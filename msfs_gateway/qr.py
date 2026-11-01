"""Генератор QR-кодов (ISO/IEC 18004) без внешних зависимостей.

Нужен для «подключите телефон»: хост отдаёт SVG с QR-кодом адреса панели,
телефон сканирует камерой и открывает панель без ввода IP.

Поддержано: байтовый режим (UTF-8), уровень коррекции L, версии 1–10
(до 271 байта данных), все восемь масок с выбором по штрафу. Этого с
запасом хватает на URL вида `http://192.168.31.189:8760/?device=phone`.

Реализация намеренно компактная: без ECI, Kanji и микро-QR.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Уровень коррекции L: (число EC-кодовых слов на блок, [(блоков, данных)]).
_EC_L: dict[int, tuple[int, list[tuple[int, int]]]] = {
    1: (7, [(1, 19)]),
    2: (10, [(1, 34)]),
    3: (15, [(1, 55)]),
    4: (20, [(1, 80)]),
    5: (26, [(1, 108)]),
    6: (18, [(2, 68)]),
    7: (20, [(2, 78)]),
    8: (24, [(2, 97)]),
    9: (30, [(2, 116)]),
    10: (18, [(2, 68), (2, 69)]),
}

#: Позиции выравнивающих узоров (центры) для версий 1–10.
_ALIGNMENT: dict[int, tuple[int, ...]] = {
    1: (),
    2: (6, 18),
    3: (6, 22),
    4: (6, 26),
    5: (6, 30),
    6: (6, 34),
    7: (6, 22, 38),
    8: (6, 24, 42),
    9: (6, 26, 46),
    10: (6, 28, 50),
}

#: Биты уровня коррекции для поля формата (L = 01).
_ECL_FORMAT_BITS = 0b01

MAX_VERSION = max(_EC_L)


class QRError(ValueError):
    """Данные не помещаются в поддерживаемые версии."""


@dataclass(frozen=True)
class QRCode:
    """Готовая матрица: `matrix[row][col]` — True для тёмного модуля."""

    version: int
    mask: int
    matrix: tuple[tuple[bool, ...], ...]

    @property
    def size(self) -> int:
        return len(self.matrix)

    def is_dark(self, row: int, col: int) -> bool:
        return self.matrix[row][col]


# ---------------------------------------------------------------------
# Поля Галуа и Reed–Solomon
# ---------------------------------------------------------------------
def _gf_mul(x: int, y: int) -> int:
    z = 0
    for i in range(7, -1, -1):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z & 0xFF


def _rs_divisor(degree: int) -> list[int]:
    result = [0] * degree
    result[-1] = 1
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 0x02)
    return result


def _rs_remainder(data: bytes, degree: int) -> bytes:
    divisor = _rs_divisor(degree)
    result = bytearray(degree)
    for byte in data:
        factor = byte ^ result[0]
        result = result[1:] + bytearray(1)
        if factor:
            for i in range(degree):
                result[i] ^= _gf_mul(divisor[i], factor)
    return bytes(result)


# ---------------------------------------------------------------------
# Кодирование данных
# ---------------------------------------------------------------------
def _data_codewords(version: int) -> int:
    _ec, groups = _EC_L[version]
    return sum(count * length for count, length in groups)


def _encode_codewords(payload: bytes, version: int) -> bytes:
    capacity_bits = _data_codewords(version) * 8
    bits: list[int] = []

    def append(value: int, length: int) -> None:
        bits.extend((value >> i) & 1 for i in range(length - 1, -1, -1))

    append(0b0100, 4)  # байтовый режим
    append(len(payload), 8 if version < 10 else 16)
    for byte in payload:
        append(byte, 8)

    if len(bits) > capacity_bits:
        raise QRError(f"{len(payload)} байт не помещаются в версию {version}")

    append(0, min(4, capacity_bits - len(bits)))
    append(0, (-len(bits)) % 8)

    result = bytearray()
    for i in range(0, len(bits), 8):
        value = 0
        for bit in bits[i : i + 8]:
            value = (value << 1) | bit
        result.append(value)

    pad = 0xEC
    while len(result) < _data_codewords(version):
        result.append(pad)
        pad ^= 0xEC ^ 0x11
    return bytes(result)


def _split_blocks(codewords: bytes, version: int) -> list[bytes]:
    blocks: list[bytes] = []
    offset = 0
    for count, length in _EC_L[version][1]:
        for _ in range(count):
            blocks.append(codewords[offset : offset + length])
            offset += length
    return blocks


def _interleave(codewords: bytes, version: int) -> bytes:
    ec_len = _EC_L[version][0]
    blocks = _split_blocks(codewords, version)
    ecc = [_rs_remainder(block, ec_len) for block in blocks]

    result = bytearray()
    for i in range(max(len(block) for block in blocks)):
        for block in blocks:
            if i < len(block):
                result.append(block[i])
    for i in range(ec_len):
        for block_ecc in ecc:
            result.append(block_ecc[i])
    return bytes(result)


# ---------------------------------------------------------------------
# Матрица
# ---------------------------------------------------------------------
class _Builder:
    def __init__(self, version: int) -> None:
        self.version = version
        self.size = version * 4 + 17
        self.modules = [[False] * self.size for _ in range(self.size)]
        self.is_function = [[False] * self.size for _ in range(self.size)]

    # --- примитивы ---
    def set_function(self, row: int, col: int, dark: bool) -> None:
        self.modules[row][col] = dark
        self.is_function[row][col] = True

    def set_module(self, row: int, col: int, dark: bool) -> None:
        self.modules[row][col] = dark

    # --- функциональные узоры ---
    def draw_function_patterns(self) -> None:
        size = self.size
        for i in range(size):
            self.set_function(6, i, i % 2 == 0)
            self.set_function(i, 6, i % 2 == 0)

        for row, col in ((0, 0), (0, size - 7), (size - 7, 0)):
            self._draw_finder(row, col)

        centers = _ALIGNMENT[self.version]
        for i, row in enumerate(centers):
            for j, col in enumerate(centers):
                if (i, j) in ((0, 0), (0, len(centers) - 1), (len(centers) - 1, 0)):
                    continue
                self._draw_alignment(row, col)

        self._draw_format_bits(0)  # резерв под формат (значения позже)
        self._draw_version()

    def _draw_finder(self, row: int, col: int) -> None:
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = row + dr, col + dc
                if 0 <= r < self.size and 0 <= c < self.size:
                    dark = (
                        0 <= dr <= 6
                        and 0 <= dc <= 6
                        and (dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4))
                    )
                    self.set_function(r, c, dark)

    def _draw_alignment(self, row: int, col: int) -> None:
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                dark = max(abs(dr), abs(dc)) != 1
                self.set_function(row + dr, col + dc, dark)

    def _draw_version(self) -> None:
        if self.version < 7:
            return
        rem = self.version
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        bits = (self.version << 12) | rem
        for i in range(18):
            bit = (bits >> i) & 1 == 1
            a = self.size - 11 + i % 3
            b = i // 3
            self.set_function(a, b, bit)
            self.set_function(b, a, bit)

    def _draw_format_bits(self, mask: int) -> None:
        data = (_ECL_FORMAT_BITS << 3) | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = ((data << 10) | rem) ^ 0x5412

        def bit(index: int) -> bool:
            return (bits >> index) & 1 == 1

        # Первая копия: вокруг верхнего левого поисковика (столбец 8 и строка 8).
        for i in range(6):
            self.set_function(i, 8, bit(i))
        self.set_function(7, 8, bit(6))
        self.set_function(8, 8, bit(7))
        self.set_function(8, 7, bit(8))
        for i in range(9, 15):
            self.set_function(8, 14 - i, bit(i))

        # Вторая копия: справа сверху и снизу слева.
        for i in range(8):
            self.set_function(8, self.size - 1 - i, bit(i))
        for i in range(8, 15):
            self.set_function(self.size - 15 + i, 8, bit(i))
        self.set_function(self.size - 8, 8, True)

    # --- данные ---
    def draw_codewords(self, codewords: bytes) -> None:
        total_bits = len(codewords) * 8
        index = 0
        right = self.size - 1
        upward = True
        while right >= 1:
            if right == 6:
                right -= 1
            for vert in range(self.size):
                row = self.size - 1 - vert if upward else vert
                for dc in (0, -1):
                    col = right + dc
                    if self.is_function[row][col]:
                        continue
                    dark = False
                    if index < total_bits:
                        dark = (codewords[index >> 3] >> (7 - (index & 7))) & 1 == 1
                    self.set_module(row, col, dark)
                    index += 1
            upward = not upward
            right -= 2

    # --- маски ---
    def apply_mask(self, mask: int) -> None:
        for row in range(self.size):
            for col in range(self.size):
                if self.is_function[row][col]:
                    continue
                if self._mask_bit(mask, row, col):
                    self.modules[row][col] = not self.modules[row][col]

    @staticmethod
    def _mask_bit(mask: int, row: int, col: int) -> bool:
        if mask == 0:
            return (row + col) % 2 == 0
        if mask == 1:
            return row % 2 == 0
        if mask == 2:
            return col % 3 == 0
        if mask == 3:
            return (row + col) % 3 == 0
        if mask == 4:
            return (row // 2 + col // 3) % 2 == 0
        if mask == 5:
            return (row * col) % 2 + (row * col) % 3 == 0
        if mask == 6:
            return ((row * col) % 2 + (row * col) % 3) % 2 == 0
        return ((row + col) % 2 + (row * col) % 3) % 2 == 0

    # --- штраф ---
    def penalty(self) -> int:
        size = self.size
        modules = self.modules
        score = 0

        for rows in (modules, [list(col) for col in zip(*modules, strict=False)]):
            for line in rows:
                run_dark = 0
                run_length = 0
                for cell in line:
                    if cell == run_dark:
                        run_length += 1
                    else:
                        if run_length >= 5:
                            score += 3 + (run_length - 5)
                        run_dark = cell
                        run_length = 1
                if run_length >= 5:
                    score += 3 + (run_length - 5)

                text = "".join("1" if cell else "0" for cell in line)
                for pattern in ("10111010000", "00001011101"):
                    start = text.find(pattern)
                    while start != -1:
                        score += 40
                        start = text.find(pattern, start + 1)

        for row in range(size - 1):
            for col in range(size - 1):
                block = (
                    modules[row][col],
                    modules[row][col + 1],
                    modules[row + 1][col],
                    modules[row + 1][col + 1],
                )
                if all(block) or not any(block):
                    score += 3

        dark = sum(sum(1 for cell in row if cell) for row in modules)
        total = size * size
        ratio = abs(dark * 100 // total - 50)
        score += ratio // 5 * 10
        return score


def _choose_version(payload: bytes) -> int:
    for version in range(1, MAX_VERSION + 1):
        header = 4 + (8 if version < 10 else 16)
        if header + len(payload) * 8 <= _data_codewords(version) * 8:
            return version
    raise QRError(
        f"Слишком длинный текст для QR: {len(payload)} байт (максимум для версии {MAX_VERSION})"
    )


def make_qr(text: str) -> QRCode:
    """Кодирует текст (UTF-8) в QR-код минимально возможной версии."""
    payload = text.encode("utf-8")
    version = _choose_version(payload)

    codewords = _interleave(_encode_codewords(payload, version), version)
    builder = _Builder(version)
    builder.draw_function_patterns()
    builder.draw_codewords(codewords)

    best: QRCode | None = None
    best_score = -1
    for mask in range(8):
        builder.apply_mask(mask)
        builder._draw_format_bits(mask)
        score = builder.penalty()
        matrix = tuple(tuple(row) for row in builder.modules)
        if best is None or score < best_score:
            best = QRCode(version=version, mask=mask, matrix=matrix)
            best_score = score
        builder.apply_mask(mask)  # снять маску (XOR инволютивен)

    assert best is not None
    return best


def to_svg(qr: QRCode, *, scale: int = 6, border: int = 4) -> str:
    """Рендерит QR в SVG: белый фон, тёмные модули одним path."""
    scale = max(1, min(40, int(scale)))
    border = max(0, min(16, int(border)))
    size = qr.size + border * 2

    parts = []
    for row in range(qr.size):
        for col in range(qr.size):
            if qr.matrix[row][col]:
                parts.append(f"M{col + border} {row + border}h1v1h-1z")

    path = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size * scale}" height="{size * scale}" '
        f'viewBox="0 0 {size} {size}" shape-rendering="crispEdges">'
        f'<rect width="{size}" height="{size}" fill="#ffffff"/>'
        f'<path d="{path}" fill="#000000"/>'
        f"</svg>"
    )
