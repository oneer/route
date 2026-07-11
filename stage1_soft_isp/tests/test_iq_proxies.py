"""自然图诊断 proxy 的方向性 sanity checks。"""

from __future__ import annotations

import math
import unittest

import numpy as np

from soft_isp.iq_metrics import (
    approximate_dynamic_range_db,
    clipping_fractions,
    edge_mtf50_proxy,
    roi_snr_db,
)


class IqProxyTests(unittest.TestCase):
    def test_clipping_fractions_use_black_and_white_margins(self) -> None:
        raw = np.array([[0.0, 10.0, 990.0, 1000.0]], dtype=np.float32)
        result = clipping_fractions(raw, black_level=0.0, white_level=1000.0, margin=10.0)
        self.assertEqual(result["near_black_fraction"], 0.5)
        self.assertEqual(result["near_white_fraction"], 0.5)

    def test_snr_proxy_decreases_when_variation_increases(self) -> None:
        flat = np.full((8, 8), 1000.0, dtype=np.float32)
        textured = flat.copy()
        textured[::2] -= 100.0
        textured[1::2] += 100.0
        clean_snr = roi_snr_db(flat, black_level=100.0)["snr_db"]
        varied_snr = roi_snr_db(textured, black_level=100.0)["snr_db"]
        self.assertGreater(clean_snr, varied_snr)

    def test_dynamic_range_proxy_matches_documented_formula(self) -> None:
        result = approximate_dynamic_range_db(white_level=1000.0, black_level=100.0, noise_floor=10.0)
        self.assertAlmostEqual(result, 20.0 * math.log10(90.0))

    def test_sharp_step_ranks_above_blurred_step(self) -> None:
        edge = np.zeros(64, dtype=np.float32)
        edge[32:] = 1.0
        sharp = np.tile(edge, (64, 1))
        kernel = np.ones(9, dtype=np.float32) / 9.0
        blurred_edge = np.convolve(edge, kernel, mode="same")
        blurred = np.tile(blurred_edge, (64, 1))
        roi = (0, 0, 64, 64)
        sharp_proxy = edge_mtf50_proxy(sharp, roi)["mtf50_proxy_cyc_per_px"]
        blurred_proxy = edge_mtf50_proxy(blurred, roi)["mtf50_proxy_cyc_per_px"]
        self.assertGreater(sharp_proxy, blurred_proxy)


if __name__ == "__main__":
    unittest.main()
