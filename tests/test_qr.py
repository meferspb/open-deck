"""Тесты собственного генератора QR (без внешних библиотек).

Корректность матрицы подтверждена декодированием в OpenCV (см.
scripts/verify_qr.py); здесь — структурные проверки и эталонный отпечаток,
чтобы регрессии ловились без установки OpenCV.
"""

import hashlib
import unittest

from msfs_gateway import qr


class StructureTest(unittest.TestCase):
    def test_size_matches_version(self):
        code = qr.make_qr("hello")
        self.assertEqual(code.version, 1)
        self.assertEqual(code.size, 21)

    def test_finder_patterns(self):
        code = qr.make_qr("hello")
        for row, col in ((0, 0), (0, 14), (14, 0)):
            # Внешняя рамка поисковика — тёмная, внутренняя — светлая.
            self.assertTrue(code.matrix[row][col])
            self.assertTrue(code.matrix[row + 6][col + 6])
            self.assertFalse(code.matrix[row + 1][col + 1])
            self.assertTrue(code.matrix[row + 3][col + 3])

    def test_timing_pattern_alternates(self):
        code = qr.make_qr("hello")
        for i in range(8, code.size - 8):
            self.assertEqual(code.matrix[6][i], i % 2 == 0)
            self.assertEqual(code.matrix[i][6], i % 2 == 0)

    def test_dark_module(self):
        code = qr.make_qr("hello")
        self.assertTrue(code.matrix[code.size - 8][8])

    def test_matrix_is_square_and_boolean(self):
        code = qr.make_qr("http://10.0.0.2:8760/")
        self.assertTrue(all(len(row) == code.size for row in code.matrix))
        self.assertTrue(all(isinstance(cell, bool) for row in code.matrix for cell in row))


class VersionSelectionTest(unittest.TestCase):
    def test_short_text_uses_small_version(self):
        self.assertEqual(qr.make_qr("hello").version, 1)

    def test_long_text_grows(self):
        self.assertGreater(qr.make_qr("x" * 100).version, 3)

    def test_max_version(self):
        self.assertEqual(qr.make_qr("x" * 260).version, 10)

    def test_too_long_raises(self):
        with self.assertRaises(qr.QRError):
            qr.make_qr("x" * 500)

    def test_unicode_counts_utf8_bytes(self):
        ascii_version = qr.make_qr("a" * 20).version
        cyrillic_version = qr.make_qr("я" * 20).version
        self.assertGreater(cyrillic_version, ascii_version)


class DeterminismTest(unittest.TestCase):
    def test_same_text_same_matrix(self):
        first = qr.make_qr("http://192.168.1.10:8760/")
        second = qr.make_qr("http://192.168.1.10:8760/")
        self.assertEqual(first.matrix, second.matrix)

    def test_different_text_different_matrix(self):
        first = qr.make_qr("http://192.168.1.10:8760/")
        second = qr.make_qr("http://192.168.1.11:8760/")
        self.assertNotEqual(first.matrix, second.matrix)

    def test_known_matrix_digest(self):
        """Эталон: изменился алгоритм кодирования — тест это покажет."""
        code = qr.make_qr("http://192.168.31.189:8760/?device=phone")
        payload = "\n".join("".join("1" if cell else "0" for cell in row) for row in code.matrix)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        self.assertEqual(code.version, 3)
        self.assertEqual(digest, "024f9e5fb8ff34c87b7a05d3287ad6c612130d97090652f84a7a6bac24e9fa95")


class SvgTest(unittest.TestCase):
    def test_svg_has_quiet_zone_and_scaling(self):
        code = qr.make_qr("hello")
        svg = qr.to_svg(code, scale=4, border=2)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn('width="100"', svg)  # (21 + 2*2) * 4
        self.assertIn('fill="#ffffff"', svg)
        self.assertIn("<path", svg)

    def test_scale_and_border_are_clamped(self):
        code = qr.make_qr("hello")
        self.assertIn('width="21"', qr.to_svg(code, scale=0, border=0))
        huge = qr.to_svg(code, scale=1000, border=0)
        self.assertIn(f'width="{21 * 40}"', huge)


if __name__ == "__main__":
    unittest.main()
