from __future__ import annotations

import unittest

import numpy as np

from soft_isp.awb import apply_awb, gray_world_gains
from soft_isp.ccm import apply_ccm
from soft_isp.metrics import compute_metrics
from soft_isp.tone import apply_gamma, normalize_by_percentile, to_uint8


class ColorAndToneTests(unittest.TestCase):
    def test_gray_world_equalizes_channel_means(self) -> None:
        rgb = np.zeros((10, 10, 3), dtype=np.float32)
        rgb[..., 0] = 1.0
        rgb[..., 1] = 2.0
        rgb[..., 2] = 4.0
        corrected = apply_awb(rgb, gray_world_gains(rgb, 0.0, 100.0))
        means = corrected.mean(axis=(0, 1))
        np.testing.assert_allclose(means, [2.0, 2.0, 2.0], atol=1e-5)

    def test_identity_ccm_preserves_values(self) -> None:
        rgb = np.random.default_rng(0).random((4, 5, 3), dtype=np.float32)
        np.testing.assert_allclose(apply_ccm(rgb, np.eye(3)), rgb)

    def test_ccm_rejects_wrong_shape(self) -> None:
        with self.assertRaises(ValueError):
            apply_ccm(np.zeros((2, 2, 3), dtype=np.float32), np.eye(4))

    def test_gamma_rejects_non_positive_value(self) -> None:
        with self.assertRaises(ValueError):
            apply_gamma(np.zeros((2, 2, 3), dtype=np.float32), 0.0)

    def test_display_conversion_is_bounded_uint8(self) -> None:
        rgb = np.array([[[-1.0, 0.5, 5.0]]], dtype=np.float32)
        output = to_uint8(apply_gamma(normalize_by_percentile(rgb, 99.5), 2.2))
        self.assertEqual(output.dtype, np.uint8)
        self.assertGreaterEqual(int(output.min()), 0)
        self.assertLessEqual(int(output.max()), 255)

    def test_metrics_are_perfect_for_identical_images(self) -> None:
        image = np.full((16, 16, 3), 128, dtype=np.uint8)
        metrics = compute_metrics(image, image)
        self.assertTrue(np.isinf(metrics["psnr"]))
        self.assertAlmostEqual(metrics["ssim"], 1.0)
        self.assertAlmostEqual(metrics["mean_abs_diff"], 0.0)


if __name__ == "__main__":
    unittest.main()
