"""Synthetic exposure, ROI selection, and CCM calibration tests."""

from __future__ import annotations

import unittest

import numpy as np

from soft_isp.calibration import evaluate_colorchecker, fit_ccm_least_squares
from soft_isp.denoise import bilateral_denoise_rgb
from soft_isp.iq_metrics import exposure_statistics, strongest_edge_roi


class CalibrationTests(unittest.TestCase):
    def test_exposure_statistics_use_metadata_range(self) -> None:
        raw = np.array([[100.0, 550.0, 1000.0]], dtype=np.float32)
        result = exposure_statistics(raw, black_level=100.0, white_level=1000.0, margin=0.0)
        self.assertAlmostEqual(result["p50_normalized"], 0.5)
        self.assertAlmostEqual(result["near_black_fraction"], 1.0 / 3.0)
        self.assertAlmostEqual(result["near_white_fraction"], 1.0 / 3.0)

    def test_strongest_edge_roi_finds_edge_tile(self) -> None:
        image = np.zeros((32, 64), dtype=np.float32)
        image[:, 48:] = 1.0
        self.assertEqual(strongest_edge_roi(image, roi_size=16, stride=16), (48, 0, 16, 16))

    def test_fitted_ccm_recovers_known_linear_mapping(self) -> None:
        measured = np.array(
            [[0.1, 0.2, 0.3], [0.8, 0.1, 0.2], [0.2, 0.9, 0.1], [0.6, 0.4, 0.7]],
            dtype=np.float32,
        )
        expected = np.array([[1.05, -0.03, 0.01], [0.02, 0.98, 0.01], [-0.01, 0.04, 0.96]], dtype=np.float32)
        reference = measured @ expected.T
        fitted = fit_ccm_least_squares(measured, reference, regularization=0.0)
        np.testing.assert_allclose(fitted, expected, atol=1.0e-5)
        metrics = evaluate_colorchecker(measured, reference, fitted)
        self.assertLess(metrics["mean_delta_e_2000"], 1.0e-3)

    def test_bilateral_denoise_reduces_controlled_noise(self) -> None:
        clean = np.full((32, 32, 3), 0.5, dtype=np.float32)
        noisy = clean.copy()
        noisy[::2, ::2] += 0.08
        noisy[1::2, 1::2] -= 0.08
        filtered = bilateral_denoise_rgb(noisy, sigma_range=0.12)
        self.assertLess(float(np.mean((filtered - clean) ** 2)), float(np.mean((noisy - clean) ** 2)))

    def test_bilateral_denoise_validates_parameters(self) -> None:
        with self.assertRaises(ValueError):
            bilateral_denoise_rgb(np.zeros((8, 8, 3), dtype=np.float32), sigma_range=0.0)


if __name__ == "__main__":
    unittest.main()
