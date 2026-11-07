"""Конфигурация шлюза: значения по умолчанию и разбор аргументов командной строки."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from .auth import validate_password
from .discovery import DEFAULT_DISCOVERY_INTERVAL, DEFAULT_DISCOVERY_PORT

PACKAGE_DIR = Path(__file__).resolve().parent

#: Каталог приложения: в исходниках — корень репозитория, в установленной
#: сборке (PyInstaller) — папка рядом с .exe, куда ставится статика и профили.
APP_ROOT = (
    Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PACKAGE_DIR.parent
)
REPO_ROOT = APP_ROOT
DEFAULT_WEB_DIR = APP_ROOT / "web"
DEFAULT_PROFILE_DIR = APP_ROOT / "profiles"
DEFAULT_DONATION_PATH = APP_ROOT / "config" / "donation.json"
#: Файл с PBKDF2-хешем пароля; создаётся командой --set-password.
DEFAULT_AUTH_PATH = APP_ROOT / "config" / "auth.json"

SIM_CHOICES = ("auto", "mock", "simconnect")
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8760
#: Требование ТЗ: 30–60 Гц. 30 Гц достаточно для стрелок и экономит CPU.
DEFAULT_TELEMETRY_HZ = 30.0
DEFAULT_LOG_LEVEL = "INFO"
#: Автообнаружение хоста по UDP broadcast включено по умолчанию.
DEFAULT_DISCOVERY = True


@dataclass(frozen=True, slots=True)
class Settings:
    """Неизменяемый набор параметров запуска."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    web_dir: Path = DEFAULT_WEB_DIR
    profile_dir: Path = DEFAULT_PROFILE_DIR
    donation_path: Path = DEFAULT_DONATION_PATH
    sim: str = "auto"
    simconnect_dll: Path | None = None
    #: TCP-адрес SimConnect (MSFS 2020/2024 по умолчанию слушает 19999).
    simconnect_host: str = "127.0.0.1"
    simconnect_port: int = 19999
    telemetry_hz: float = DEFAULT_TELEMETRY_HZ
    log_level: str = DEFAULT_LOG_LEVEL
    discovery: bool = DEFAULT_DISCOVERY
    discovery_port: int = DEFAULT_DISCOVERY_PORT
    discovery_interval: float = DEFAULT_DISCOVERY_INTERVAL
    #: Обмен LVAR/RPN через Client Data Area WASM-модуля.
    wasm: bool = True
    #: Режим «собрать APK и выйти»: путь к JSON с настройками (или пустой).
    build_apk: str | None = None
    #: Аутентификация: файл с хешем пароля (config/auth.json).
    auth_path: Path = DEFAULT_AUTH_PATH
    #: Пароль из командной строки (не сохраняется на диск).
    password: str | None = None
    #: Режим «задать пароль и выйти».
    set_password: str | None = None
    #: Принудительно открытый доступ, даже если файл пароля существует.
    no_auth: bool = False
    #: Дополнительные имена, разрешённые в заголовке Host (DNS-имена хоста).
    allowed_hosts: tuple[str, ...] = ()


def build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов CLI."""
    parser = argparse.ArgumentParser(
        prog="msfs_gateway",
        description="Локальный HTTP/WebSocket шлюз между MSFS и клиентскими панелями.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Адрес прослушивания (по умолчанию все интерфейсы).",
    )
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="NAME",
        help="Дополнительное имя в заголовке Host (если панель открывают по DNS-имени).",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="TCP-порт HTTP и WebSocket.")
    parser.add_argument(
        "--sim",
        choices=SIM_CHOICES,
        default="auto",
        help="Телеметрия: auto (SimConnect, иначе mock), mock (демо), simconnect.",
    )
    parser.add_argument(
        "--simconnect-dll",
        type=Path,
        default=None,
        help="Путь к SimConnect.dll, если он не находится автоматически.",
    )
    parser.add_argument(
        "--simconnect-host",
        default="127.0.0.1",
        help="Адрес SimConnect (для удалённого симулятора; по умолчанию localhost).",
    )
    parser.add_argument(
        "--simconnect-port",
        type=int,
        default=19999,
        help="TCP-порт SimConnect (MSFS 2020/2024 по умолчанию 19999).",
    )
    parser.add_argument(
        "--web-dir",
        type=Path,
        default=DEFAULT_WEB_DIR,
        help="Каталог со статикой клиента (web/).",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=DEFAULT_PROFILE_DIR,
        help="Каталог с JSON-профилями самолётов.",
    )
    parser.add_argument(
        "--donation-config",
        type=Path,
        default=DEFAULT_DONATION_PATH,
        help="Конфигурация реквизитов поддержки автора (config/donation.json).",
    )
    parser.add_argument(
        "--telemetry-hz",
        type=float,
        default=DEFAULT_TELEMETRY_HZ,
        help="Частота широковещательной рассылки телеметрии, Гц (1..60).",
    )
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Уровень логирования.",
    )
    parser.add_argument(
        "--no-discovery",
        action="store_true",
        help="Отключить автообнаружение хоста по UDP broadcast.",
    )
    parser.add_argument(
        "--discovery-port",
        type=int,
        default=DEFAULT_DISCOVERY_PORT,
        help="UDP-порт бикона автообнаружения.",
    )
    parser.add_argument(
        "--discovery-interval",
        type=float,
        default=DEFAULT_DISCOVERY_INTERVAL,
        help="Период рассылки бикона автообнаружения, секунды.",
    )
    parser.add_argument(
        "--no-wasm",
        action="store_true",
        help="Отключить WASM-мост (LVAR/RPN через Client Data Area).",
    )
    parser.add_argument(
        "--password",
        default=None,
        metavar="PWD",
        help="Включить вход по паролю (не короче 6 символов). Не сохраняется на диск.",
    )
    parser.add_argument(
        "--set-password",
        nargs="?",
        const="",
        default=None,
        metavar="PWD",
        help="Сохранить пароль (PBKDF2-хеш) в config/auth.json и выйти; "
        "без значения — спросить пароль в консоли.",
    )
    parser.add_argument(
        "--auth-file",
        type=Path,
        default=DEFAULT_AUTH_PATH,
        help="Файл с хешем пароля (по умолчанию config/auth.json).",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Игнорировать пароль и пускать без входа (только для доверенной сети).",
    )
    parser.add_argument(
        "--build-apk",
        nargs="?",
        const="",
        default=None,
        metavar="CONFIG",
        help="Собрать Android APK из android/ и выйти (путь к android-build.json опционален).",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> Settings:
    """Разбирает и проверяет аргументы CLI."""
    args = build_parser().parse_args(argv)

    if not 1 <= args.port <= 65535:
        raise SystemExit(f"Некорректный порт: {args.port}")
    if not 1.0 <= args.telemetry_hz <= 60.0:
        raise SystemExit(f"Некорректная частота телеметрии: {args.telemetry_hz}")
    if not 1 <= args.simconnect_port <= 65535:
        raise SystemExit(f"Некорректный порт SimConnect: {args.simconnect_port}")
    if not 1 <= args.discovery_port <= 65535:
        raise SystemExit(f"Некорректный порт автообнаружения: {args.discovery_port}")
    if not 0.5 <= args.discovery_interval <= 60.0:
        raise SystemExit(f"Некорректный период автообнаружения: {args.discovery_interval}")
    if not args.web_dir.is_dir():
        raise SystemExit(f"Каталог статики не найден: {args.web_dir}")
    if args.password is not None:
        error = validate_password(args.password)
        if error:
            raise SystemExit(f"--password: {error}")
    if args.set_password:
        error = validate_password(args.set_password)
        if error:
            raise SystemExit(f"--set-password: {error}")
    if args.password is not None and args.set_password is not None:
        raise SystemExit("--password и --set-password несовместимы")

    args.profile_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        host=args.host,
        port=args.port,
        web_dir=args.web_dir.resolve(),
        profile_dir=args.profile_dir.resolve(),
        donation_path=args.donation_config.resolve(),
        sim=args.sim,
        simconnect_dll=args.simconnect_dll,
        simconnect_host=args.simconnect_host,
        simconnect_port=args.simconnect_port,
        telemetry_hz=args.telemetry_hz,
        log_level=args.log_level,
        discovery=not args.no_discovery,
        discovery_port=args.discovery_port,
        discovery_interval=args.discovery_interval,
        wasm=not args.no_wasm,
        build_apk=args.build_apk,
        auth_path=args.auth_file.resolve(),
        password=args.password,
        set_password=args.set_password,
        no_auth=args.no_auth,
        allowed_hosts=tuple(host.strip().lower() for host in args.allow_host if host.strip()),
    )
