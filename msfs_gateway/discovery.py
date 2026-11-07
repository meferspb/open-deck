"""Сетевое автообнаружение хоста (UDP broadcast).

Windows-хост периодически рассылает JSON-бикон по UDP broadcast, чтобы
нативные клиенты (Android и др.) находили шлюз без ручного ввода IP-адреса.

Замечание про браузер: веб-клиент НЕ может слушать UDP — он и так запускается
с самого хоста (по адресу из баннера), поэтому автообнаружение ему не нужно.
UDP-бикон предназначен для Android-приложения и нативных клиентов.

Формат бикона (JSON, UTF-8, один пакет):

    {
      "type": "open-deck-msfs",
      "protocol": 1,
      "name": "FLIGHTSIM-PC",
      "version": "0.1.0",
      "httpPort": 8760,
      "telemetryHz": 30.0,
      "profiles": ["cessna-172-skyhawk", "..."],
      "ts": 1762340000
    }

Реализация — только стандартная библиотека: broadcast на `255.255.255.255`
(limited broadcast, работает в пределах локального сегмента) и на
направленный broadcast каждого IPv4-интерфейса.
"""

from __future__ import annotations

import contextlib
import json
import logging
import socket
import threading
import time
from typing import Any, Final

from . import __version__

#: Отдельный UDP-порт, чтобы не конфликтовать с HTTP/WebSocket.
DEFAULT_DISCOVERY_PORT: Final = 8761
DEFAULT_DISCOVERY_INTERVAL: Final = 3.0
BEACON_TYPE: Final = "open-deck-msfs"
PROTOCOL_VERSION: Final = 1
MAX_BEACON_BYTES: Final = 1400  # меньше MTU — без фрагментации

logger = logging.getLogger("msfs_gateway.discovery")


def _local_ipv4_addresses() -> list[str]:
    """IPv4-адреса машины для направленного broadcast по каждому интерфейсу."""
    addresses: set[str] = set()
    try:
        hostname = socket.gethostname()
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_INET):
            if family == socket.AF_INET and sockaddr:
                addresses.add(str(sockaddr[0]))
    except OSError:
        pass
    return sorted(addresses)


def _broadcast_targets() -> list[str]:
    """Куда слать бикон: limited broadcast + направленные broadcast подсетей."""
    targets = {"255.255.255.255"}
    for address in _local_ipv4_addresses():
        parts = address.split(".")
        if len(parts) == 4:
            with contextlib.suppress(ValueError):
                targets.add(f"{parts[0]}.{parts[1]}.{parts[2]}.255")
    return sorted(targets)


class DiscoveryBeacon:
    """Фоновый рассыльщик биконов автообнаружения."""

    def __init__(
        self,
        *,
        port: int = DEFAULT_DISCOVERY_PORT,
        interval: float = DEFAULT_DISCOVERY_INTERVAL,
        http_port: int = 8760,
        telemetry_hz: float = 30.0,
        profiles_provider: Any = None,
        auth_required: bool = False,
    ) -> None:
        self.port = port
        self.interval = interval
        self.http_port = http_port
        self.telemetry_hz = telemetry_hz
        self._profiles_provider = profiles_provider  # callable -> list[dict]
        self._auth_required = auth_required
        self._hostname = socket.gethostname()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    def _profile_ids(self) -> list[str]:
        if self._profiles_provider is None:
            return []
        try:
            summaries = self._profiles_provider()
            return [summary["id"] for summary in summaries if isinstance(summary, dict)]
        except Exception:
            return []

    def payload(self) -> dict[str, Any]:
        """Тело бикона. Вынесено отдельно для тестов."""
        payload = {
            "type": BEACON_TYPE,
            "protocol": PROTOCOL_VERSION,
            "name": self._hostname,
            "version": __version__,
            "httpPort": self.http_port,
            "telemetryHz": self.telemetry_hz,
            "profiles": self._profile_ids(),
            "ts": int(time.time()),
        }
        if self._auth_required:
            payload["auth"] = True
        return payload

    def _broadcast_once(self) -> None:
        payload = self.payload()
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_BEACON_BYTES:
            # Список профилей — необязательная деталь: без него хост всё ещё
            # можно найти и подключить. Пропускать бикон целиком нельзя.
            payload["profiles"] = []
            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_BEACON_BYTES:
            logger.warning("Бикон автообнаружения слишком большой (%d байт)", len(data))
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for target in _broadcast_targets():
                try:
                    sock.sendto(data, (target, self.port))
                except OSError:
                    # Отдельный интерфейс может не поддерживать broadcast.
                    continue
        finally:
            sock.close()

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Запускает рассылку."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="discovery-beacon", daemon=True)
        self._thread.start()
        logger.info(
            "Автообнаружение: UDP-бикон на порту %d каждые %.1f с", self.port, self.interval
        )

    def stop(self) -> None:
        """Останавливает рассылку."""
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    def _loop(self) -> None:
        deadline = time.monotonic()
        while not self._stop.is_set():
            try:
                self._broadcast_once()
            except Exception:
                logger.debug("Сбой рассылки бикона", exc_info=True)

            deadline += self.interval
            delay = deadline - time.monotonic()
            if delay > 0:
                self._stop.wait(delay)
            else:
                deadline = time.monotonic()


def listen_once(timeout: float = 5.0, port: int = DEFAULT_DISCOVERY_PORT) -> dict[str, Any] | None:
    """Слушает один бикон и возвращает его JSON.

    Нужен нативным клиентам и автотестам. Блокирует до `timeout` секунд.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", port))
        sock.settimeout(timeout)
        data, _addr = sock.recvfrom(MAX_BEACON_BYTES)
        payload = json.loads(data.decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    except (TimeoutError, OSError, json.JSONDecodeError):
        return None
    finally:
        sock.close()


def _main(argv: list[str] | None = None) -> int:
    """Утилита отладки: `python -m msfs_gateway.discovery --listen`."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m msfs_gateway.discovery",
        description="Слушает UDP-биконы автообнаружения шлюза.",
    )
    parser.add_argument("--listen", action="store_true", help="Слушать биконы в цикле.")
    parser.add_argument("--port", type=int, default=DEFAULT_DISCOVERY_PORT)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args(argv)

    if not args.listen:
        parser.error("Укажите --listen (рассылка бикона выполняется шлюзом автоматически)")

    print(f"Слушаю биконы на UDP :{args.port} (Ctrl+C — выход)")
    while True:
        payload = listen_once(timeout=args.timeout, port=args.port)
        if payload is None:
            print(f"  … за {args.timeout:g} с бикон не получен")
            continue
        if payload.get("type") != BEACON_TYPE:
            continue
        print(
            f"  найден {payload.get('name')} v{payload.get('version')} → "
            f"http://<host>:{payload.get('httpPort')}/ "
            f"(профили: {', '.join(payload.get('profiles', [])) or '—'})"
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
