"""RUD Panel Gateway — локальный шлюз приборных панелей MSFS.

Пакет намеренно не имеет внешних зависимостей: он рассчитан на запуск
в изолированной сети (air-gapped), где `pip install` невозможен.
"""

from __future__ import annotations

__version__ = "0.1.0"

APP_NAME = "RUD Panel Gateway"
