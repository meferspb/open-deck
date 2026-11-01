"""Фабрика провайдеров телеметрии."""

from __future__ import annotations

import logging

from ..profiles import ProfileStore
from ..settings import Settings
from .base import SimCommandError, SimProvider
from .mock import MockSim

logger = logging.getLogger("msfs_gateway.sim")

__all__ = ["MockSim", "SimCommandError", "SimProvider", "create_sim"]


def create_sim(settings: Settings, store: ProfileStore) -> SimProvider:
    """Создаёт провайдер согласно настройкам.

    `auto` сначала пробует настоящий SimConnect и только потом откатывается
    на mock — так шлюз запускается на машине без MSFS без правок конфигурации.
    """
    if settings.sim == "mock":
        return MockSim(store)

    if settings.sim == "simconnect":
        from .simconnect import SimConnectSim  # импорт только по требованию

        provider: SimProvider = SimConnectSim(
            settings.simconnect_dll,
            host=settings.simconnect_host,
            port=settings.simconnect_port,
        )
        return provider

    try:
        from .simconnect import SimConnectError, SimConnectSim
    except ImportError as exc:  # pragma: no cover - на Windows недостижимо
        logger.warning("Модуль SimConnect не импортируется (%s) — запускаю mock-провайдер", exc)
        return MockSim(store)

    try:
        return SimConnectSim(
            settings.simconnect_dll,
            host=settings.simconnect_host,
            port=settings.simconnect_port,
        )
    except (SimConnectError, OSError) as exc:
        logger.warning("SimConnect недоступен (%s) — запускаю mock-провайдер", exc)
        return MockSim(store)
