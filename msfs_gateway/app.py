"""Сборка приложения: профили, провайдер телеметрии, шина и HTTP-сервер."""

from __future__ import annotations

import contextlib
import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

from . import APP_NAME, __version__
from .android_build import BuildManager
from .assist import AssistManager
from .auth import AuthError, AuthService, load_record, save_record, validate_password
from .discovery import DiscoveryBeacon
from .http_api import GatewayHTTPServer, create_server
from .hub import Hub
from .integrity import IntegrityError, verify
from .profiles import ProfileStore
from .settings import Settings, parse_args
from .sim import SimProvider, create_sim

LOGGER = logging.getLogger("msfs_gateway")


def local_addresses() -> list[str]:
    """IPv4-адреса машины для подсказки «откройте с телефона»."""
    addresses: set[str] = {"127.0.0.1"}
    try:
        hostname = socket.gethostname()
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_INET):
            if family == socket.AF_INET and sockaddr:
                addresses.add(str(sockaddr[0]))
    except OSError:
        pass
    try:
        # UDP-connect не отправляет пакеты, но сообщает адрес нужного интерфейса.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))
            addresses.add(str(probe.getsockname()[0]))
    except OSError:
        pass
    return sorted(addresses)


class GatewayApplication:
    """Контейнер зависимостей и жизненного цикла шлюза."""

    def __init__(self, settings: Settings, *, check_integrity: bool = True) -> None:
        self.settings = settings
        self.logger = LOGGER
        self.profiles = ProfileStore(settings.profile_dir)
        self.sim: SimProvider = create_sim(settings, self.profiles)
        self.hub = Hub(self.sim, self.profiles, hz=settings.telemetry_hz)
        self.assist = AssistManager(self.hub)
        self.httpd: GatewayHTTPServer | None = None
        self._serve_thread: threading.Thread | None = None
        self._check_integrity = check_integrity
        self.integrity_report = None
        self.wasm_bridge = None
        self.android = BuildManager()
        self.auth = _build_auth(settings)
        self._allowed_hosts_lock = threading.Lock()
        self._allowed_hosts_at = 0.0
        self._allowed_hosts: set[str] = set()
        self.discovery: DiscoveryBeacon | None = None
        if settings.discovery:
            self.discovery = DiscoveryBeacon(
                port=settings.discovery_port,
                interval=settings.discovery_interval,
                http_port=settings.port,
                telemetry_hz=settings.telemetry_hz,
                profiles_provider=self.profiles.list_summaries,
                auth_required=self.auth.required,
            )

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Запускает провайдер, шину, ассистента, автообнаружение и HTTP-сервер."""
        if self._check_integrity:
            report = verify()
            if not report.verified:
                details = "\n".join(f"  - {error}" for error in report.errors)
                raise IntegrityError(
                    "Проверка целостности интерфейса не пройдена:\n"
                    f"{details}\n"
                    "Если файлы изменены намеренно, обновите манифест:\n"
                    "  python -m msfs_gateway.integrity --write"
                )
            self.integrity_report = report
            self.logger.info("Целостность интерфейса подтверждена (%d файлов)", len(report.files))

        try:
            self.sim.start()
            self._setup_wasm()
            self.hub.start()
            self.assist.start()
            if self.discovery is not None:
                self.discovery.start()
            self.httpd = create_server(self)
        except Exception:
            # Не оставляем полузапущенные потоки, если порт занят или
            # SimConnect не открылся.
            self.shutdown()
            raise

    def _setup_wasm(self) -> None:
        """Подключает LVAR/RPN через WASM-модуль, если провайдер это умеет."""
        if not self.settings.wasm:
            return
        factory = getattr(self.sim, "wasm_bridge", None)
        if not callable(factory):
            return
        try:
            bridge = factory()
        except Exception as exc:
            self.logger.warning("WASM-мост не создан: %s", exc)
            return

        self.wasm_bridge = bridge
        self.hub.set_custom_reader(bridge.read_specs)
        self.logger.info(
            "WASM-мост подключён: LVAR/RPN через Client Data Area (MobiFlight/SimBridge)"
        )

    def serve_forever(self) -> None:
        """Блокирующий цикл HTTP-сервера (режим CLI)."""
        if self.httpd is None:
            raise RuntimeError("Сервер не создан: вызовите start()")
        self.httpd.serve_forever(poll_interval=0.2)

    def start_background(self) -> threading.Thread:
        """Для тестов: сервер в отдельном потоке, управление — через shutdown()."""
        if self.httpd is None:
            self.start()
        assert self.httpd is not None
        self._serve_thread = threading.Thread(
            target=self.httpd.serve_forever,
            kwargs={"poll_interval": 0.05},
            name="http-server",
            daemon=True,
        )
        self._serve_thread.start()
        return self._serve_thread

    def shutdown(self) -> None:
        """Останавливает подсистемы в безопасном порядке."""
        self.assist.stop()
        if self.discovery is not None:
            self.discovery.stop()
        self.hub.close_all()
        self.hub.stop()
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        self.sim.stop()

    # ------------------------------------------------------------------
    def base_urls(self) -> list[str]:
        """Адреса, по которым панель доступна в браузере."""
        host = self.settings.host
        addresses = local_addresses() if host in {"0.0.0.0", "::", ""} else [host]
        return [f"http://{address}:{self.settings.port}/" for address in addresses]

    def allowed_hostnames(self) -> set[str]:
        """Имена, которые допустимы в заголовке Host (защита от DNS rebinding).

        Разрешаем localhost, имя машины/FQDN и локальные IP. Кэш на 30 секунд:
        DHCP может сменить адрес, перезапускать шлюз для этого не нужно.
        """
        now = time.monotonic()
        with self._allowed_hosts_lock:
            if now - self._allowed_hosts_at < 30.0 and self._allowed_hosts:
                return set(self._allowed_hosts)
            hosts = {"localhost", "127.0.0.1", "::1"}
            with contextlib.suppress(OSError):
                hosts.add(socket.gethostname().lower())
            with contextlib.suppress(OSError):
                hosts.add(socket.getfqdn().lower())
            hosts.update(address.lower() for address in local_addresses())
            hosts.update(host.lower() for host in self.settings.allowed_hosts)
            configured = self.settings.host.strip().lower()
            if configured and configured not in {"0.0.0.0", "::"}:
                hosts.add(configured)
            self._allowed_hosts = {host.rstrip(".") for host in hosts if host}
            self._allowed_hosts_at = now
            return set(self._allowed_hosts)

    def banner(self) -> str:
        """Приветствие в консоли с адресами и состоянием подсистем."""
        urls = "\n".join(f"  {url}" for url in self.base_urls())
        provider = self.sim.name
        connection = "подключён" if self.sim.connected else "нет связи"
        try:
            profile_count = len(self.profiles.list_summaries())
        except Exception:
            profile_count = 0
        wasm_state = "подключён" if self.wasm_bridge else "недоступен"
        discovery_state = f"UDP {self.settings.discovery_port}" if self.discovery else "выключено"
        integrity_state = "подтверждена" if self.integrity_report else "не проверялась"
        if self.auth.required:
            auth_state = "включён (вход по паролю)"
        elif self.settings.no_auth:
            auth_state = "выключен (--no-auth)"
        else:
            auth_state = "выключен"
        warning = ""
        if not self.auth.required:
            warning = (
                "  ВНИМАНИЕ: вход выключен — панель и команды доступны всем в локальной сети.\n"
                "            Задайте пароль: OpenDeck.exe --set-password\n"
            )
        return (
            f"\n{APP_NAME} v{__version__}\n"
            f"  Провайдер телеметрии : {provider} ({connection})\n"
            f"  Профилей самолётов   : {profile_count}\n"
            f"  Телеметрия           : {self.settings.telemetry_hz:g} Гц по WebSocket /ws\n"
            f"  WASM-мост (LVAR/RPN) : {wasm_state}\n"
            f"  Автообнаружение      : {discovery_state}\n"
            f"  Вход по паролю       : {auth_state}\n"
            f"{warning}"
            f"  Целостность          : {integrity_state}\n"
            f"  Панель в браузере    :\n{urls}\n"
            f"  Остановка            : Ctrl+C\n"
        )


def _build_auth(settings: Settings) -> AuthService:
    """Собирает AuthService: --no-auth важнее файла, --password важнее файла."""
    if settings.no_auth:
        return AuthService()
    if settings.password is not None:
        from .auth import hash_password

        return AuthService(record=hash_password(settings.password))
    env_password = os.environ.get("OPEN_DECK_PASSWORD")
    if env_password:
        error = validate_password(env_password)
        if error:
            raise SystemExit(f"OPEN_DECK_PASSWORD: {error}")
        from .auth import hash_password

        return AuthService(record=hash_password(env_password))
    try:
        record = load_record(settings.auth_path)
    except AuthError as exc:
        raise SystemExit(f"Ошибка файла пароля: {exc}") from exc
    return AuthService(record=record)


def _prompt_new_password() -> str | None:
    """Спрашивает пароль в консоли (для ярлыка «Задать пароль»)."""
    import getpass

    while True:
        try:
            first = getpass.getpass("Новый пароль (не короче 6 символов): ")
        except (EOFError, KeyboardInterrupt):
            print("Отменено.", file=sys.stderr)
            return None
        error = validate_password(first)
        if error:
            print(error, file=sys.stderr)
            continue
        try:
            second = getpass.getpass("Повторите пароль: ")
        except (EOFError, KeyboardInterrupt):
            print("Отменено.", file=sys.stderr)
            return None
        if first != second:
            print("Пароли не совпадают, попробуйте ещё раз.", file=sys.stderr)
            continue
        return first


def _configure_console() -> None:
    """Чтобы кириллица не роняла вывод в консоли с cp1251."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure: Any = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            with contextlib.suppress(ValueError, OSError):
                reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI: разбирает аргументы и запускает шлюз."""
    _configure_console()
    settings = parse_args(argv)

    if settings.set_password is not None:
        password = settings.set_password
        if not password:
            password = _prompt_new_password()
            if password is None:
                return 1
        try:
            save_record(settings.auth_path, password)
        except AuthError as exc:
            print(f"Не удалось сохранить пароль: {exc}", file=sys.stderr)
            return 1
        print(f"Пароль сохранён: {settings.auth_path}")
        print("Запустите шлюз без --password: вход будет по этому паролю.")
        return 0

    if settings.build_apk is not None:
        # Режим сборки APK: сервер не поднимаем, только собираем и выходим.
        from .android_build import build_from_file

        config = Path(settings.build_apk) if settings.build_apk else None
        return build_from_file(config)

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)-7s %(name)-24s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        app = GatewayApplication(settings)
        app.start()
    except IntegrityError as exc:
        print("\nЗАПУСК ЗАБЛОКИРОВАН: нарушена целостность интерфейса.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Не удалось запустить шлюз: {exc}", file=sys.stderr)
        return 1

    print(app.banner(), flush=True)

    try:
        app.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка шлюза...", flush=True)
    finally:
        app.shutdown()
    return 0
