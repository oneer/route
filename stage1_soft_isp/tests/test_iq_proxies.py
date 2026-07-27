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
    strongest_edge_roi,
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

    def test_invalid_inputs_are_rejected_instead_of_publishing_nan(self) -> None:
        with self.assertRaises(ValueError):
            roi_snr_db(np.array([], dtype=np.float32), black_level=0.0)
        with self.assertRaises(ValueError):
            roi_snr_db(np.array([[np.nan]], dtype=np.float32), black_level=0.0)
        with self.assertRaises(ValueError):
            clipping_fractions(np.ones((2, 2)), black_level=0.0, white_level=1.0, margin=-0.1)
        with self.assertRaises(ValueError):
            approximate_dynamic_range_db(white_level=1.0, black_level=1.0, noise_floor=0.1)
        with self.assertRaises(ValueError):
            approximate_dynamic_range_db(white_level=1.0, black_level=0.0, noise_floor=0.0)

    def test_roi_contract_rejects_invalid_stride_and_bounds(self) -> None:
        image = np.zeros((16, 16), dtype=np.float32)
        with self.assertRaises(ValueError):
            strongest_edge_roi(image, roi_size=8, stride=0)
        with self.assertRaises(ValueError):
            edge_mtf50_proxy(image, (-1, 0, 8, 8))
        with self.assertRaises(ValueError):
            edge_mtf50_proxy(image, (12, 12, 8, 8))


if __name__ == "__main__":
    unittest.main()
