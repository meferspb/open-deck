"""HTTP-слой шлюза: статика клиента, REST API и точка входа WebSocket.

Один порт обслуживает всё: браузер получает `web/`, Android-клиент —
JSON API, а телеметрия идёт через Upgrade на `/ws`. Это упрощает
настройку брандмауэра в локальной сети: достаточно одного правила.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import sys
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Final

from . import __version__, integrity
from .android_build import (
    AndroidBuildError,
    AndroidBuildSettings,
    load_settings,
    prebuilt_apk,
    save_settings,
    toolchain_status,
)
from .auth import PAIRING_TTL, SESSION_COOKIE
from .hub import ClientInfo, Hub
from .profiles import ProfileError, ProfileNotFound, ProfileStore
from .settings import REPO_ROOT
from .sim.base import SimCommandError, SimProvider
from .websocket import WebSocketConnection, WebSocketError, handshake_headers

MAX_BODY_BYTES: Final = 2 * 1024 * 1024
#: Клиент и профили — живые данные: кэширование только мешает при разработке.
STATIC_CACHE_CONTROL: Final = "no-cache"

#: API, доступное без входа: проверка статуса, сам вход/выход и данные,
#: которые нужны для блока поддержки автора и проверки целостности.
PUBLIC_API_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/api/auth/status",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/health",
        "/api/integrity",
        "/api/donation",
    }
)
#: Статика, доступная без входа: страница входа и её оформление.
PUBLIC_STATIC_PATHS: Final[frozenset[str]] = frozenset(
    {"/login.html", "/js/login.js", "/license", "/favicon.ico"}
)
PUBLIC_STATIC_PREFIXES: Final[tuple[str, ...]] = ("/css/", "/img/")

CONTENT_TYPES: Final[dict[str, str]] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".map": "application/json; charset=utf-8",
}

logger = logging.getLogger("msfs_gateway.http")


class ApiError(Exception):
    """Ошибка запроса с HTTP-кодом."""

    def __init__(self, status: int, message: str, code: str = "bad_request") -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# --- кэш проверок целостности и реквизитов (5 секунд) ------------------
_integrity_cache: tuple[float, dict[str, Any]] | None = None
_donation_cache: tuple[float, float, dict[str, Any]] | None = None


def _integrity_payload() -> dict[str, Any]:
    global _integrity_cache
    now = time.monotonic()
    if _integrity_cache is not None and now - _integrity_cache[0] < 5.0:
        return _integrity_cache[1]
    payload = integrity.verify().as_dict()
    _integrity_cache = (now, payload)
    return payload


def _donation_payload(path: Path) -> dict[str, Any]:
    global _donation_cache
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        raise ApiError(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            f"Конфигурация поддержки недоступна: {path.name}",
            "donation_missing",
        ) from exc

    now = time.monotonic()
    if (
        _donation_cache is not None
        and _donation_cache[0] == mtime
        and now - _donation_cache[1] < 5.0
    ):
        return _donation_cache[2]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApiError(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "config/donation.json: некорректный JSON",
            "donation_invalid",
        ) from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("links"), list):
        raise ApiError(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "config/donation.json: ожидался объект с массивом links",
            "donation_invalid",
        )

    _donation_cache = (mtime, now, payload)
    return payload


class GatewayHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler], app: Any
    ) -> None:
        self.app = app
        super().__init__(address, handler)

    def handle_error(self, request: Any, client_address: tuple[str, int]) -> None:
        """Не засоряем лог трейсбеками обрывов соединения клиентом.

        Клиент может закрыть сокет в любой момент (мобильный браузер,
        перезагрузка страницы) — это штатная ситуация, а не ошибка сервера.
        """
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionError, TimeoutError)):
            logger.debug("Клиент %s отключился: %s", client_address[0], exc)
            return
        super().handle_error(request, client_address)


def make_handler(app: Any) -> type[BaseHTTPRequestHandler]:
    """Создаёт класс обработчика, связанный с конкретным приложением."""

    class GatewayRequestHandler(BaseHTTPRequestHandler):
        server_version = f"RUDPanelGateway/{__version__}"
        protocol_version = "HTTP/1.1"
        timeout = 120  # keep-alive не должен висеть вечно

        # --- утилиты ---------------------------------------------------
        @property
        def gateway(self) -> Any:
            return app

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("%s %s", self.address_string(), format % args)

        def log_error(self, format: str, *args: Any) -> None:
            logger.warning("%s %s", self.address_string(), format % args)

        def _send_json(
            self, status: int, payload: Any, *, extra: dict[str, str] | None = None
        ) -> None:
            body = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for name, value in (extra or {}).items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_error(
            self,
            status: int,
            message: str,
            code: str = "error",
            *,
            extra: dict[str, str] | None = None,
        ) -> None:
            self._send_json(status, {"error": message, "code": code}, extra=extra)

        def _read_body_bytes(self) -> bytes:
            """Читает тело один раз, чтобы не ломать keep-alive.

            Обработчики, которым тело не нужно (например, запуск сборки),
            всё равно должны его вычитать — иначе следующие байты будут
            приняты за новую строку запроса.
            """
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ApiError(
                    HTTPStatus.LENGTH_REQUIRED, "Не указан Content-Length", "length_required"
                )
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Некорректный Content-Length") from exc
            if length < 0:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Некорректный Content-Length")
            if length > MAX_BODY_BYTES:
                raise ApiError(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Тело запроса слишком велико", "too_large"
                )
            return self.rfile.read(length) if length else b""

        def _read_json_body(self) -> Any:
            if not hasattr(self, "_raw_body"):
                self._raw_body = self._read_body_bytes()
            raw: bytes = self._raw_body
            if not raw:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Пустое тело запроса", "empty_body")
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Некорректный JSON") from exc

        # --- аутентификация -------------------------------------------
        def _cookie_token(self) -> str | None:
            raw = self.headers.get("Cookie")
            if not raw:
                return None
            jar = SimpleCookie()
            try:
                jar.load(raw)
            except CookieError:
                return None
            morsel = jar.get(SESSION_COOKIE)
            return morsel.value if morsel else None

        def _bearer_token(self) -> str | None:
            header = self.headers.get("Authorization", "")
            if header.lower().startswith("bearer "):
                return header[7:].strip() or None
            return None

        def _session_token(self) -> str | None:
            return self._bearer_token() or self._cookie_token()

        def _authorized(self) -> bool:
            return self.gateway.auth.valid(self._session_token())

        def _unauthorized(self) -> None:
            # Тело POST/PUT могло остаться непрочитанным — закрываем соединение.
            self.close_connection = True
            self._send_error(
                HTTPStatus.UNAUTHORIZED,
                "Требуется вход по паролю",
                "unauthorized",
                extra={"WWW-Authenticate": 'Bearer realm="rud-panel"'},
            )

        def _redirect(self, location: str, *, cookie: str | None = None) -> None:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            if cookie is not None:
                self.send_header("Set-Cookie", cookie)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _redirect_to_login(self, next_path: str = "") -> None:
            target = "/login.html"
            if next_path and next_path not in {"/", "/login.html"}:
                target += "?next=" + urllib.parse.quote(next_path, safe="")
            self._redirect(target)

        def _session_cookie(self, token: str, *, max_age: int) -> str:
            return f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}"

        def _handle_auth_status(self) -> None:
            auth = self.gateway.auth
            token = self._session_token()
            self._send_json(
                HTTPStatus.OK,
                {
                    "required": auth.required,
                    "authenticated": (not auth.required) or auth.valid(token),
                },
            )

        def _handle_auth_login(self) -> None:
            payload = self._read_json_body()
            if not isinstance(payload, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, "Ожидался JSON-объект")
            password = payload.get("password")
            if not isinstance(password, str) or not password:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Не указан пароль", "missing_password")

            auth = self.gateway.auth
            if not auth.required:
                self._send_json(HTTPStatus.OK, {"ok": True, "required": False})
                return

            address = self.client_address[0]
            retry_after = auth.limiter.retry_after(address)
            if retry_after > 0:
                seconds = max(1, int(retry_after) + 1)
                self._send_json(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    {
                        "ok": False,
                        "error": "Слишком много неверных попыток, подождите",
                        "code": "rate_limited",
                        "retryAfter": seconds,
                    },
                    extra={"Retry-After": str(seconds)},
                )
                return

            token = auth.login(password)
            if token is None:
                retry_after = auth.limiter.register_failure(address)
                logger.warning("Неудачный вход по паролю с %s", address)
                extra = (
                    {"Retry-After": str(max(1, int(retry_after) + 1))} if retry_after > 0 else None
                )
                self._send_error(
                    HTTPStatus.UNAUTHORIZED,
                    "Неверный пароль",
                    "bad_password",
                    extra=extra,
                )
                return

            auth.limiter.reset(address)
            logger.info("Вход по паролю с %s", address)
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "required": True,
                    "token": token,
                    "expiresIn": int(auth.session_ttl),
                },
                extra={"Set-Cookie": self._session_cookie(token, max_age=int(auth.session_ttl))},
            )

        def _handle_auth_logout(self) -> None:
            auth = self.gateway.auth
            auth.sessions.revoke(self._session_token())
            self._send_json(
                HTTPStatus.OK,
                {"ok": True},
                extra={"Set-Cookie": self._session_cookie("", max_age=0)},
            )

        def _primary_url(self) -> str | None:
            return self._connect_payload().get("primaryUrl")

        def _handle_pair(self) -> None:
            auth = self.gateway.auth
            base = self._primary_url() or f"http://127.0.0.1:{self.gateway.settings.port}/"
            if not auth.required:
                self._send_json(HTTPStatus.OK, {"url": base, "expiresIn": 0, "required": False})
                return
            token = auth.issue_pairing()
            self._send_json(
                HTTPStatus.OK,
                {
                    "url": f"{base}?pair={token}",
                    "token": token,
                    "expiresIn": int(PAIRING_TTL),
                    "required": True,
                },
            )

        def _handle_pair_entry(self, token: str) -> None:
            if not self.gateway.auth.required:
                self._redirect("/")
                return
            session = self.gateway.auth.sessions.consume_pairing(token)
            if session is None:
                self._redirect("/login.html?error=pair")
                return
            self._redirect(
                "/",
                cookie=self._session_cookie(session, max_age=int(self.gateway.auth.session_ttl)),
            )

        # --- HTTP-методы ----------------------------------------------
        def do_OPTIONS(self) -> None:
            # CORS намеренно не включён: API — same-origin, а открытый
            # Access-Control-Allow-Origin позволял бы сторонним страницам
            # перебирать пароль через браузер пользователя.
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            try:
                if path == "/ws":
                    token = self._session_token()
                    if token is None:
                        token = (urllib.parse.parse_qs(parsed.query).get("token") or [None])[0]
                    if not self.gateway.auth.valid(token):
                        self._unauthorized()
                        return
                    self._handle_websocket()
                    return
                if path == "/" and "pair" in urllib.parse.parse_qs(parsed.query):
                    values = urllib.parse.parse_qs(parsed.query).get("pair") or [""]
                    self._handle_pair_entry(values[0])
                    return
                if path == "/license":
                    self._serve_license()
                    return
                if path.startswith("/api/"):
                    if path not in PUBLIC_API_PATHS and not self._authorized():
                        self._unauthorized()
                        return
                    self._handle_api_get(path)
                    return
                if not self._authorized() and not self._is_public_static(path):
                    self._redirect_to_login(path)
                    return
                self._serve_static(path)
            except ApiError as exc:
                self._send_error(exc.status, exc.message, exc.code)
            except (BrokenPipeError, ConnectionResetError):
                logger.debug("Клиент разорвал соединение: %s", self.client_address[0])

        def do_HEAD(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path.startswith("/api/"):
                self._send_error(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "HEAD не поддерживается для API",
                    "method_not_allowed",
                )
                return
            if not self._authorized() and not self._is_public_static(path):
                self._redirect_to_login(path)
                return
            self._serve_static(path, head_only=True)

        def do_PUT(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path not in PUBLIC_API_PATHS and not self._authorized():
                self._unauthorized()
                return
            try:
                # Тело вычитываем всегда: иначе лишние байты «превратятся»
                # в следующую строку запроса на keep-alive соединении.
                self._raw_body = self._read_body_bytes()
                self._handle_api_put(path)
            except ApiError as exc:
                self._send_error(exc.status, exc.message, exc.code)

        def do_POST(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path not in PUBLIC_API_PATHS and not self._authorized():
                self._unauthorized()
                return
            try:
                self._raw_body = self._read_body_bytes()
                self._handle_api_post(path)
            except ApiError as exc:
                self._send_error(exc.status, exc.message, exc.code)

        # --- статика ---------------------------------------------------
        def _is_public_static(self, path: str) -> bool:
            return path in PUBLIC_STATIC_PATHS or path.startswith(PUBLIC_STATIC_PREFIXES)

        def _serve_static(self, path: str, *, head_only: bool = False) -> None:
            web_root = self.gateway.settings.web_dir.resolve()
            try:
                relative = urllib.parse.unquote(path).lstrip("/") or "index.html"
                candidate = (web_root / relative).resolve()
            except (OSError, ValueError):
                # Некорректный путь (например, NUL-байт) — просто 404.
                self._send_error(HTTPStatus.NOT_FOUND, "Файл не найден", "not_found")
                return

            if not candidate.is_relative_to(web_root):
                self._send_error(HTTPStatus.NOT_FOUND, "Файл не найден", "not_found")
                return
            if candidate.is_dir():
                candidate = candidate / "index.html"
            if not candidate.is_file():
                self._send_error(HTTPStatus.NOT_FOUND, "Файл не найден", "not_found")
                return

            try:
                body = candidate.read_bytes()
            except OSError:
                self._send_error(
                    HTTPStatus.INTERNAL_SERVER_ERROR, "Не удалось прочитать файл", "read_failed"
                )
                return

            content_type = CONTENT_TYPES.get(candidate.suffix.lower())
            if content_type is None:
                content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", STATIC_CACHE_CONTROL)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                # Всё своё, из сети — ничего. Inline-стили нужны для координат виджетов.
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; font-src 'self'; connect-src 'self' ws: wss:; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
            )
            self.end_headers()
            if not head_only:
                self.wfile.write(body)

        # --- REST ------------------------------------------------------
        def _serve_license(self) -> None:
            path = REPO_ROOT / "LICENSE"
            if not path.is_file():
                self._send_error(HTTPStatus.NOT_FOUND, "Файл лицензии не найден", "not_found")
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _handle_api_get(self, path: str) -> None:
            parts = [part for part in path.split("/") if part]
            hub: Hub = self.gateway.hub
            store: ProfileStore = self.gateway.profiles

            if parts == ["api", "health"]:
                self._send_json(
                    HTTPStatus.OK,
                    {**hub.health(), "authRequired": self.gateway.auth.required},
                )
                return
            if parts == ["api", "auth", "status"]:
                self._handle_auth_status()
                return
            if parts == ["api", "connect"]:
                self._send_json(HTTPStatus.OK, self._connect_payload())
                return
            if parts == ["api", "android", "settings"]:
                self._send_json(HTTPStatus.OK, self._android_settings_payload())
                return
            if parts == ["api", "android", "build"]:
                self._send_json(HTTPStatus.OK, self.gateway.android.status())
                return
            if parts == ["api", "android", "apk"]:
                self._serve_android_apk()
                return
            if parts == ["api", "qr.svg"]:
                self._serve_qr()
                return
            if parts == ["api", "integrity"]:
                self._send_json(HTTPStatus.OK, _integrity_payload())
                return
            if parts == ["api", "donation"]:
                self._send_json(
                    HTTPStatus.OK, _donation_payload(self.gateway.settings.donation_path)
                )
                return
            if parts == ["api", "profiles"]:
                self._send_json(HTTPStatus.OK, {"profiles": store.list_summaries()})
                return
            if len(parts) == 3 and parts[:2] == ["api", "profiles"]:
                try:
                    profile = store.get(parts[2])
                except ProfileNotFound as exc:
                    raise ApiError(HTTPStatus.NOT_FOUND, str(exc), "not_found") from exc
                except ProfileError as exc:
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY, str(exc), "invalid_profile"
                    ) from exc
                self._send_json(HTTPStatus.OK, profile)
                return
            if parts == ["api", "telemetry"]:
                self._send_json(HTTPStatus.OK, hub.latest_message())
                return
            if parts == ["api", "telemetry", "variables"]:
                from .telemetry import variables_catalog

                self._send_json(HTTPStatus.OK, {"variables": variables_catalog()})
                return
            if parts == ["api", "sim"]:
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "provider": self.gateway.sim.name,
                        "connected": bool(self.gateway.sim.connected),
                        "aircraftTitle": self.gateway.sim.aircraft_title,
                        "profileId": self.gateway.sim.profile_id,
                    },
                )
                return
            raise ApiError(HTTPStatus.NOT_FOUND, f"Неизвестный ресурс: {path}", "not_found")

        # --- быстрое подключение телефона ------------------------------
        def _connect_payload(self) -> dict[str, Any]:
            """Адреса, по которым панель открывается с телефона/планшета."""
            entries: list[dict[str, Any]] = []
            for url in self.gateway.base_urls():
                parsed = urllib.parse.urlsplit(url)
                host = parsed.hostname or ""
                private = host.startswith(("192.168.", "10.")) or host.startswith(
                    tuple(f"172.{n}." for n in range(16, 32))
                )
                entries.append(
                    {
                        "url": url,
                        "host": host,
                        "private": private,
                        "loopback": host in {"127.0.0.1", "localhost", "::1"},
                        "linkLocal": host.startswith("169.254."),
                    }
                )

            def rank(entry: dict[str, Any]) -> tuple[int, str]:
                host = entry["host"]
                # Домашние сети чаще 192.168.x, затем 10.x, затем 172.16-31.
                for index, prefix in enumerate(("192.168.", "10.", "172.")):
                    if host.startswith(prefix):
                        return (index, host)
                if entry["linkLocal"]:
                    return (4, host)
                if entry["loopback"]:
                    return (5, host)
                return (3, host)

            entries.sort(key=rank)
            primary = entries[0] if entries else None
            phone_url = f"{primary['url']}?device=phone" if primary else None
            return {
                "host": os.environ.get("COMPUTERNAME", "host"),
                "urls": entries,
                "primaryUrl": primary["url"] if primary else None,
                "phoneUrl": phone_url,
                "devicePresets": ["phone", "tablet-sm", "tablet-lg"],
                "qr": {"scale": 6, "border": 4, "maxTextLength": 512},
            }

        def _serve_qr(self) -> None:
            from .qr import QRError, make_qr, to_svg

            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            text = (query.get("text") or [""])[0].strip()
            if not text:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Не указан параметр text", "missing_text")
            if len(text) > 512:
                raise ApiError(
                    HTTPStatus.BAD_REQUEST, "Слишком длинный text (максимум 512)", "text_too_long"
                )
            try:
                scale = int((query.get("scale") or ["6"])[0])
                border = int((query.get("border") or ["4"])[0])
            except ValueError as exc:
                raise ApiError(
                    HTTPStatus.BAD_REQUEST, "scale и border должны быть числами"
                ) from exc

            try:
                svg = to_svg(make_qr(text), scale=scale, border=border)
            except QRError as exc:
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc), "qr_too_long") from exc

            body = svg.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _android_settings_payload(self) -> dict[str, Any]:
            try:
                settings = load_settings()
            except AndroidBuildError as exc:
                raise ApiError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    f"Настройки Android не читаются: {exc}",
                    "invalid_settings",
                ) from exc
            apk = self.gateway.android.status().get("apk")
            prebuilt = prebuilt_apk()
            return {
                "settings": settings.to_dict(),
                "toolchain": toolchain_status(settings),
                "apk": apk,
                "prebuiltApk": str(prebuilt) if prebuilt else None,
            }

        def _serve_android_apk(self) -> None:
            status = self.gateway.android.status()
            path = Path(status.get("apk") or "") if status.get("apk") else None
            if path is None or not path.is_file():
                path = prebuilt_apk()
            if path is None or not path.is_file():
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    "APK ещё не собран и готовой сборки нет — запустите сборку",
                    "apk_missing",
                )
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.android.package-archive")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
            self.end_headers()
            self.wfile.write(data)

        def _handle_api_put(self, path: str) -> None:
            parts = [part for part in path.split("/") if part]

            if parts == ["api", "android", "settings"]:
                payload = self._read_json_body()
                if not isinstance(payload, dict):
                    raise ApiError(HTTPStatus.BAD_REQUEST, "Ожидался JSON-объект")
                settings = AndroidBuildSettings.from_dict(payload)
                try:
                    save_settings(settings)
                except AndroidBuildError as exc:
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY, str(exc), "invalid_settings"
                    ) from exc
                self._send_json(HTTPStatus.OK, self._android_settings_payload())
                return

            if len(parts) != 3 or parts[:2] != ["api", "profiles"]:
                raise ApiError(HTTPStatus.NOT_FOUND, f"Неизвестный ресурс: {path}", "not_found")

            profile_id = parts[2]
            payload = self._read_json_body()
            if not isinstance(payload, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, "Профиль должен быть JSON-объектом")
            if payload.get("id") != profile_id:
                raise ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "id в теле запроса должен совпадать с id в URL",
                    "id_mismatch",
                )

            try:
                saved = self.gateway.profiles.save(payload)
            except ProfileNotFound as exc:
                raise ApiError(HTTPStatus.NOT_FOUND, str(exc), "not_found") from exc
            except ProfileError as exc:
                raise ApiError(
                    HTTPStatus.UNPROCESSABLE_ENTITY, str(exc), "invalid_profile"
                ) from exc

            self.gateway.hub.announce_profiles()
            self._send_json(
                HTTPStatus.OK,
                {"ok": True, "profile": {"id": saved["id"], "name": saved["name"]}},
            )

        def _handle_api_post(self, path: str) -> None:
            parts = [part for part in path.split("/") if part]
            hub: Hub = self.gateway.hub
            sim: SimProvider = self.gateway.sim

            if parts == ["api", "auth", "login"]:
                self._handle_auth_login()
                return
            if parts == ["api", "auth", "logout"]:
                self._handle_auth_logout()
                return
            if parts == ["api", "pair"]:
                self._handle_pair()
                return

            if parts == ["api", "android", "build"]:
                try:
                    load_settings()
                except AndroidBuildError as exc:
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        f"Проверьте настройки сборки: {exc}",
                        "invalid_settings",
                    ) from exc
                try:
                    job_id = self.gateway.android.start()
                except AndroidBuildError as exc:
                    raise ApiError(HTTPStatus.CONFLICT, str(exc), "build_running") from exc
                self._send_json(
                    HTTPStatus.ACCEPTED,
                    {"jobId": job_id, **self.gateway.android.status()},
                )
                return

            if parts == ["api", "sim", "aircraft"]:
                payload = self._read_json_body()
                if not isinstance(payload, dict):
                    raise ApiError(HTTPStatus.BAD_REQUEST, "Ожидался JSON-объект")
                profile_id = payload.get("profileId")
                if not isinstance(profile_id, str):
                    raise ApiError(HTTPStatus.BAD_REQUEST, "Не указан profileId")
                try:
                    self.gateway.profiles.get(profile_id)
                except ProfileNotFound as exc:
                    raise ApiError(HTTPStatus.NOT_FOUND, str(exc), "not_found") from exc

                pinned = False
                try:
                    sim.select_aircraft(profile_id)
                except SimCommandError:
                    # Провайдер не умеет менять ВС (например, SimConnect):
                    # это не ошибка — фиксируем ручной выбор до смены самолёта.
                    pinned = True
                except ProfileNotFound as exc:
                    raise ApiError(HTTPStatus.NOT_FOUND, str(exc), "not_found") from exc

                hub.set_profile_override(profile_id)
                hub.announce_aircraft()
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "profileId": sim.profile_id or profile_id,
                        "aircraftTitle": sim.aircraft_title,
                        "pinned": pinned,
                    },
                )
                return

            if parts == ["api", "sim", "command"]:
                payload = self._read_json_body()
                if not isinstance(payload, dict):
                    raise ApiError(HTTPStatus.BAD_REQUEST, "Ожидался JSON-объект")
                ack = hub.handle_command(
                    payload.get("key"), payload.get("value"), payload.get("id")
                )
                if ack.get("ok"):
                    self._send_json(HTTPStatus.OK, ack)
                else:
                    status = (
                        HTTPStatus.CONFLICT
                        if ack.get("code") == "sim_rejected"
                        else HTTPStatus.BAD_REQUEST
                    )
                    self._send_json(status, ack)
                return

            raise ApiError(HTTPStatus.NOT_FOUND, f"Неизвестный ресурс: {path}", "not_found")

        # --- WebSocket ------------------------------------------------
        def _handle_websocket(self) -> None:
            upgrade = self.headers.get("Upgrade", "").lower()
            key = self.headers.get("Sec-WebSocket-Key")
            version = self.headers.get("Sec-WebSocket-Version")

            if upgrade != "websocket" or not key or version != "13":
                self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "Ожидался WebSocket handshake (Upgrade: websocket, версия 13)",
                    "bad_handshake",
                )
                return

            # Браузер присылает куку, нативные клиенты — Bearer или ?token=.
            token = self._session_token()
            if token is None:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                token = (query.get("token") or [None])[0]
            if not self.gateway.auth.valid(token):
                self._unauthorized()
                return

            # Ответ 101 пишем напрямую: BaseHTTPRequestHandler добавил бы
            # к нему свои заголовки и Content-Length.
            self.wfile.write(handshake_headers(key))
            self.wfile.flush()

            connection = WebSocketConnection(
                self.connection,
                self.rfile,
                self.wfile,
                peer=self.client_address[0],
                logger=logger,
            )
            client: ClientInfo | None = None
            try:
                client = self.gateway.hub.attach(connection, self.headers.get("User-Agent", ""))
                self._websocket_loop(connection, client)
            except WebSocketError as exc:
                logger.debug("WebSocket закрыт (%s): %s", self.client_address[0], exc)
                # 1002 — protocol error: клиент нарушил RFC 6455.
                connection.close(1002, "protocol error")
            except OSError:
                logger.debug("Сокет клиента %s недоступен", self.client_address[0])
            finally:
                self.gateway.hub.detach(connection)
                connection.close()
                self.close_connection = True

        def _websocket_loop(self, connection: WebSocketConnection, client: ClientInfo) -> None:
            while True:
                text = connection.recv_text()
                if text is None:
                    return
                try:
                    message = json.loads(text)
                except json.JSONDecodeError:
                    connection.send_text(
                        _json_bytes(
                            {"type": "error", "code": "bad_json", "error": "Ожидался JSON"}
                        ).decode("utf-8")
                    )
                    continue
                if not isinstance(message, dict):
                    continue

                kind = message.get("type")
                if kind == "ping":
                    connection.send_text(
                        _json_bytes(
                            {"type": "pong", "t": message.get("t"), "ts": int(time.time() * 1000)}
                        ).decode("utf-8")
                    )
                elif kind == "command":
                    ack = self.gateway.hub.handle_command(
                        message.get("key"),
                        message.get("value"),
                        message.get("id"),
                        client=client,
                    )
                    connection.send_text(_json_bytes(ack).decode("utf-8"))
                else:
                    connection.send_text(
                        _json_bytes(
                            {
                                "type": "error",
                                "code": "unknown_type",
                                "error": f"Неизвестный тип сообщения: {kind!r}",
                            }
                        ).decode("utf-8")
                    )

    return GatewayRequestHandler


def create_server(app: Any) -> GatewayHTTPServer:
    settings = app.settings
    handler = make_handler(app)
    server = GatewayHTTPServer((settings.host, settings.port), handler, app)
    logger.info("HTTP/WebSocket сервер слушает %s:%d", settings.host, settings.port)
    return server


def serve_thread(server: GatewayHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, name="http-server", daemon=True)
    thread.start()
    return thread
