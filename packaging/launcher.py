"""Точка входа для сборки PyInstaller.

PYTHONPATH не нужен: пакет `msfs_gateway` лежит рядом со скриптом в корне
репозитория, а при сборке PyInstaller кладёт его внутрь .exe.
"""

from __future__ import annotations

import sys

from msfs_gateway.app import main

if __name__ == "__main__":
    sys.exit(main())
