"""Проверка QR-генератора настоящим декодером (OpenCV).

Запуск (нужен только на машине разработчика):
    python -m pip install opencv-python-headless
    python scripts/verify_qr.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

# Запуск из корня репозитория: пакет лежит рядом, а не в scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from msfs_gateway import qr

TEXTS = [
    "hello",
    "http://192.168.31.189:8760/?device=phone",
    "http://10.0.0.5:8760/?device=tablet-sm&frame=0",
    "x" * 100,
    "x" * 260,
    "Привет, мир!",
]


def render(text: str, scale: int = 8, border: int = 4) -> np.ndarray:
    code = qr.make_qr(text)
    size = code.size + border * 2
    image = np.full((size, size), 255, dtype=np.uint8)
    for row in range(code.size):
        for col in range(code.size):
            if code.matrix[row][col]:
                image[row + border][col + border] = 0
    image = np.kron(image, np.ones((scale, scale), dtype=np.uint8))
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


def main() -> int:
    detector = cv2.QRCodeDetector()
    failed = 0
    for text in TEXTS:
        decoded, _points, _ = detector.detectAndDecode(render(text))
        ok = decoded == text
        print(f"{'OK  ' if ok else 'FAIL'} len={len(text.encode('utf-8')):>3} {text[:40]!r}")
        if not ok:
            failed += 1
            print(f"     получено: {decoded[:60]!r}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
