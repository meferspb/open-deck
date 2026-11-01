"""Общий интерфейс источника телеметрии.

Шлюз и веб-клиент ничего не знают о SimConnect: они работают с этим
интерфейсом. Благодаря этому прототип запускается без MSFS (mock), а
реальный полёт подключается заменой провайдера.
"""

from __future__ import annotations

import abc
from typing import Any


class SimCommandError(RuntimeError):
    """Команда не может быть выполнена текущим провайдером."""


class SimProvider(abc.ABC):
    """Источник значений телеметрии и приёмник команд."""

    #: Имя провайдера для логов и метаданных телеметрии.
    name: str = "base"

    @property
    @abc.abstractmethod
    def connected(self) -> bool:
        """Есть ли живая связь с симулятором."""

    @property
    def aircraft_title(self) -> str | None:
        """Название борта в симуляторе (если известно)."""
        return None

    @property
    def atc_model(self) -> str | None:
        """Модель ATC (например, C172) — второй признак автоопределения."""
        return None

    def select_aircraft(self, profile_id: str) -> None:
        """Переключить борт (только если провайдер это умеет)."""
        raise SimCommandError("Провайдер телеметрии не умеет менять борт")

    @property
    def profile_id(self) -> str | None:
        """Профиль, выбранный самим провайдером (актуально для mock)."""
        return None

    @abc.abstractmethod
    def start(self) -> None:
        """Запускает фоновые потоки провайдера."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Останавливает фоновые потоки и освобождает ресурсы."""

    @abc.abstractmethod
    def read(self) -> dict[str, Any]:
        """Снимок значений телеметрии (ключи из `telemetry.VARIABLES`)."""

    @abc.abstractmethod
    def apply_command(self, key: str, value: Any) -> None:
        """Применяет команду клиента. Бросает `SimCommandError` при отказе."""
