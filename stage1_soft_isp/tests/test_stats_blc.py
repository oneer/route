from __future__ import annotations

import unittest

import numpy as np

from soft_isp.blc import apply_blc, normalized_after_blc
from soft_isp.stats import bayer_pattern_from_rawpy, split_bayer


class StatsAndBlcTests(unittest.TestCase):
    def test_split_bayer_rggb(self) -> None:
        raw = np.arange(16, dtype=np.uint16).reshape(4, 4)
        channels = split_bayer(raw, "RGGB")
        np.testing.assert_array_equal(channels["R"], [[0, 2], [8, 10]])
        np.testing.assert_array_equal(channels["Gr"], [[1, 3], [9, 11]])
        np.testing.assert_array_equal(channels["Gb"], [[4, 6], [12, 14]])
        np.testing.assert_array_equal(channels["B"], [[5, 7], [13, 15]])

    def test_pattern_inference_uses_color_desc_indices(self) -> None:
        pattern = np.array([[0, 1], [3, 2]], dtype=np.uint8)
        self.assertEqual(bayer_pattern_from_rawpy(pattern, "RGBG"), "RGGB")

    def test_blc_uses_per_position_black_level_without_underflow(self) -> None:
        raw = np.array([[100, 200], [300, 400]], dtype=np.uint16)
        pattern = np.array([[0, 1], [3, 2]], dtype=np.uint8)
        corrected = apply_blc(raw, pattern, [100, 120, 140, 130], white_level=1000)
        np.testing.assert_array_equal(corrected, [[0, 80], [170, 260]])
        self.assertEqual(corrected.dtype, np.uint16)

    def test_normalized_blc_is_finite_and_bounded(self) -> None:
        raw = np.array([[0, 1000], [500, 1200]], dtype=np.uint16)
        pattern = np.array([[0, 1], [3, 2]], dtype=np.uint8)
        result = normalized_after_blc(raw, pattern, [100, 100, 100, 100], 1000)
        self.assertTrue(np.isfinite(result).all())
        self.assertGreaterEqual(float(result.min()), 0.0)
        self.assertLessEqual(float(result.max()), 1.0)


if __name__ == "__main__":
    unittest.main()
