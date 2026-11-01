"""Сборка приложения: профили, провайдер телеметрии, шина и HTTP-сервер."""

from __future__ import annotations

import contextlib
import logging
import socket
import sys
import threading
from pathlib import Path
from typing import Any

from . import APP_NAME, __version__
from .android_build import BuildManager
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
        self.httpd: GatewayHTTPServer | None = None
        self._serve_thread: threading.Thread | None = None
        self._check_integrity = check_integrity
        self.integrity_report = None
        self.wasm_bridge = None
        self.android = BuildManager()
        self.discovery: DiscoveryBeacon | None = None
        if settings.discovery:
            self.discovery = DiscoveryBeacon(
                port=settings.discovery_port,
                interval=settings.discovery_interval,
                http_port=settings.port,
                telemetry_hz=settings.telemetry_hz,
                profiles_provider=self.profiles.list_summaries,
            )

    # ------------------------------------------------------------------
    def start(self) -> None:
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

        self.sim.start()
        self._setup_wasm()
        self.hub.start()
        if self.discovery is not None:
            self.discovery.start()
        self.httpd = create_server(self)

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
        host = self.settings.host
        addresses = local_addresses() if host in {"0.0.0.0", "::", ""} else [host]
        return [f"http://{address}:{self.settings.port}/" for address in addresses]

    def banner(self) -> str:
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
        return (
            f"\n{APP_NAME} v{__version__}\n"
            f"  Провайдер телеметрии : {provider} ({connection})\n"
            f"  Профилей самолётов   : {profile_count}\n"
            f"  Телеметрия           : {self.settings.telemetry_hz:g} Гц по WebSocket /ws\n"
            f"  WASM-мост (LVAR/RPN) : {wasm_state}\n"
            f"  Автообнаружение      : {discovery_state}\n"
            f"  Целостность          : {integrity_state}\n"
            f"  Панель в браузере    :\n{urls}\n"
            f"  Остановка            : Ctrl+C\n"
        )


def _configure_console() -> None:
    """Чтобы кириллица не роняла вывод в консоли с cp1251."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure: Any = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            with contextlib.suppress(ValueError, OSError):
                reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    settings = parse_args(argv)

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
