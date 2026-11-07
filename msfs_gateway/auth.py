"""Парольная аутентификация шлюза.

Пароль хранится только в виде PBKDF2-хеша (``config/auth.json``), сессии —
в памяти процесса. Никаких внешних зависимостей: всё на стандартной
библиотеке.

Модель простая: если пароль настроен, любой запрос к API (кроме
``/api/auth/*``, ``/api/health``, ``/api/integrity`` и ``/api/donation``)
и WebSocket требует действующую сессию. Сессия выдаётся после входа по
паролю или по одноразовому QR-коду.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Минимальная длина пароля (требование ТЗ).
MIN_PASSWORD_LENGTH = 6
#: httponly-кука с токеном сессии.
SESSION_COOKIE = "rud_session"
DEFAULT_ITERATIONS = 210_000
DEFAULT_SESSION_TTL = 12 * 3600.0
#: Сколько живёт QR-код для быстрого входа с телефона.
PAIRING_TTL = 600.0
#: Лимит неудачных попыток входа с одного адреса.
MAX_LOGIN_FAILURES = 5
LOGIN_WINDOW = 60.0
LOGIN_LOCKOUT = 60.0


class AuthError(Exception):
    """Ошибка конфигурации аутентификации."""


def validate_password(password: str) -> str | None:
    """Возвращает текст ошибки или None, если пароль годится."""
    if not isinstance(password, str):
        return "Пароль должен быть строкой"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
    if len(password) > 256:
        return "Пароль слишком длинный (максимум 256 символов)"
    if password != password.strip():
        return "Пароль не должен начинаться или заканчиваться пробелом"
    if any(ord(char) < 32 for char in password):
        return "Пароль не должен содержать управляющих символов"
    return None


def hash_password(password: str, *, iterations: int = DEFAULT_ITERATIONS) -> dict[str, Any]:
    """Создаёт запись для ``config/auth.json`` (соль случайная)."""
    error = validate_password(password)
    if error:
        raise AuthError(error)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {
        "algorithm": "pbkdf2-sha256",
        "iterations": iterations,
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(digest).decode("ascii"),
    }


def verify_password(password: str, record: dict[str, Any]) -> bool:
    """Сверяет пароль с записью; любые проблемы в записи — «не подходит»."""
    try:
        if record.get("algorithm") != "pbkdf2-sha256":
            return False
        iterations = int(record["iterations"])
        salt = base64.b64decode(record["salt"], validate=True)
        expected = base64.b64decode(record["hash"], validate=True)
    except (KeyError, TypeError, ValueError):
        return False
    if iterations < 1 or iterations > 10_000_000:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def load_record(path: Path) -> dict[str, Any] | None:
    """Читает файл с хешем. None — файла нет; битый файл — ошибка."""
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        record = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthError(f"Не удалось прочитать {path}: {exc}") from exc
    if not isinstance(record, dict) or "hash" not in record:
        raise AuthError(f"Файл {path} не похож на запись пароля")
    return record


def save_record(path: Path, password: str) -> dict[str, Any]:
    """Атомарно записывает хеш пароля в файл."""
    record = hash_password(password)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise AuthError(f"Не удалось сохранить пароль в {path}: {exc}") from exc
    with contextlib.suppress(OSError):
        path.chmod(0o600)
    return record


@dataclass
class _Session:
    token: str
    expires_at: float
    pairing: bool = False


class SessionStore:
    """Потокобезопасное хранилище сессий с продлением по активности."""

    def __init__(self, *, ttl: float = DEFAULT_SESSION_TTL) -> None:
        self.ttl = ttl
        self._lock = threading.Lock()
        self._sessions: dict[str, _Session] = {}
        self._last_prune = 0.0

    def create(self, *, ttl: float | None = None, pairing: bool = False) -> str:
        """Создаёт сессию и возвращает токен."""
        token = secrets.token_urlsafe(32)
        duration = self.ttl if ttl is None else ttl
        with self._lock:
            self._maybe_prune_locked()
            self._sessions[token] = _Session(
                token=token, expires_at=time.monotonic() + duration, pairing=pairing
            )
        return token

    def validate(self, token: str | None, *, touch: bool = True) -> bool:
        """Проверяет токен и при необходимости продлевает сессию.

        Одноразовые QR-токены (`pairing=True`) здесь недействительны: их
        единственный разрешённый путь — `consume_pairing` через `/?pair=`.
        """
        if not token:
            return False
        now = time.monotonic()
        with self._lock:
            self._maybe_prune_locked(now)
            session = self._sessions.get(token)
            if session is None or session.expires_at <= now:
                self._sessions.pop(token, None)
                return False
            if session.pairing:
                # Не гасим QR-токен: его должен погасить ровно один
                # `consume_pairing` через `/?pair=`.
                return False
            if touch:
                session.expires_at = now + self.ttl
            return True

    def consume_pairing(self, token: str | None) -> str | None:
        """Гасит одноразовый QR-токен и возвращает обычную сессию."""
        if not token:
            return None
        now = time.monotonic()
        with self._lock:
            self._maybe_prune_locked(now)
            session = self._sessions.get(token)
            if session is None or not session.pairing:
                return None
            if session.expires_at <= now:
                self._sessions.pop(token, None)
                return None
            self._sessions.pop(token, None)
            new_token = secrets.token_urlsafe(32)
            self._sessions[new_token] = _Session(token=new_token, expires_at=now + self.ttl)
            return new_token

    def revoke(self, token: str | None) -> None:
        """Отзывает одну сессию."""
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def revoke_all(self) -> None:
        """Отзывает все сессии."""
        with self._lock:
            self._sessions.clear()

    def count(self) -> int:
        """Число активных сессий (диагностика)."""
        with self._lock:
            return len(self._sessions)

    def _maybe_prune_locked(self, now: float | None = None) -> None:
        """Периодически убирает просроченные сессии, чтобы словарь не рос."""
        moment = time.monotonic() if now is None else now
        if moment - self._last_prune < 60.0:
            return
        self._last_prune = moment
        self._prune_locked()

    def _prune_locked(self) -> None:
        now = time.monotonic()
        expired = [token for token, session in self._sessions.items() if session.expires_at <= now]
        for token in expired:
            self._sessions.pop(token, None)


class LoginLimiter:
    """Ограничивает перебор пароля: N неудач с одного адреса за окно."""

    def __init__(
        self,
        *,
        max_failures: int = MAX_LOGIN_FAILURES,
        window: float = LOGIN_WINDOW,
        lockout: float = LOGIN_LOCKOUT,
    ) -> None:
        self.max_failures = max_failures
        self.window = window
        self.lockout = lockout
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}
        self._blocked_until: dict[str, float] = {}
        self._last_prune = 0.0

    def retry_after(self, address: str) -> float:
        """Сколько секунд ждать (0 — попытки разрешены)."""
        now = time.monotonic()
        with self._lock:
            self._maybe_prune_locked(now)
            blocked = self._blocked_until.get(address, 0.0)
            return max(0.0, blocked - now)

    def register_failure(self, address: str) -> float:
        """Учитывает неудачу и возвращает retry_after для ответа клиенту."""
        now = time.monotonic()
        with self._lock:
            self._maybe_prune_locked(now)
            attempts = [
                moment for moment in self._failures.get(address, []) if now - moment <= self.window
            ]
            attempts.append(now)
            if len(attempts) >= self.max_failures:
                self._blocked_until[address] = now + self.lockout
                attempts = []
            self._failures[address] = attempts
            return max(0.0, self._blocked_until.get(address, 0.0) - now)

    def reset(self, address: str) -> None:
        """Сбрасывает счётчик неудач для адреса."""
        with self._lock:
            self._failures.pop(address, None)
            self._blocked_until.pop(address, None)

    def _maybe_prune_locked(self, now: float) -> None:
        """Периодически убирает старые записи, чтобы словари не росли."""
        if now - self._last_prune < 60.0:
            return
        self._last_prune = now
        for address, until in list(self._blocked_until.items()):
            if until <= now:
                self._blocked_until.pop(address, None)
        for address, attempts in list(self._failures.items()):
            recent = [moment for moment in attempts if now - moment <= self.window]
            if recent:
                self._failures[address] = recent
            else:
                self._failures.pop(address, None)


@dataclass
class AuthService:
    """Проверка пароля + выдача сессий. ``required`` — включён ли вход."""

    record: dict[str, Any] | None = None
    session_ttl: float = DEFAULT_SESSION_TTL
    sessions: SessionStore = field(init=False)
    limiter: LoginLimiter = field(init=False)

    def __post_init__(self) -> None:
        self.sessions = SessionStore(ttl=self.session_ttl)
        self.limiter = LoginLimiter()

    @property
    def required(self) -> bool:
        """Нужен ли вход (настроен ли пароль)."""
        return self.record is not None

    def check(self, password: str) -> bool:
        """Сверяет пароль с хешем."""
        if self.record is None:
            return True
        return verify_password(password, self.record)

    def login(self, password: str) -> str | None:
        """Успешный вход → токен сессии; иначе None."""
        if not self.required or not self.check(password):
            return None
        return self.sessions.create()

    def valid(self, token: str | None) -> bool:
        """Действителен ли токен (с учётом режима без пароля)."""
        if not self.required:
            return True
        return self.sessions.validate(token)

    def issue_pairing(self) -> str:
        """Создаёт одноразовый QR-токен на 10 минут."""
        return self.sessions.create(ttl=PAIRING_TTL, pairing=True)
