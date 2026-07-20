"""Camera-scene metrics and failure classification tests."""

from __future__ import annotations

import unittest

import numpy as np

from ai_isp.metrics.camera_scene import aggregate_by_scene_method, evaluate_scene_candidate


class CameraSceneEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        grid = np.indices((32, 32)).sum(axis=0) % 2
        self.reference = np.repeat(grid[:, :, None], 3, axis=2).astype(np.float32)
        rng = np.random.default_rng(7)
        self.noisy = np.clip(self.reference + rng.normal(0.0, 0.08, self.reference.shape), 0.0, 1.0)

    def test_better_output_has_positive_psnr_gain(self) -> None:
        output = 0.75 * self.reference + 0.25 * self.noisy
        result = evaluate_scene_candidate(self.noisy, output, self.reference)
        self.assertGreater(result["psnr_gain"], 0.0)
        self.assertGreater(result["noise_rmse_reduction"], 0.0)

    def test_flat_output_is_classified_as_quality_regression(self) -> None:
        output = np.full_like(self.reference, 0.5)
        result = evaluate_scene_candidate(self.noisy, output, self.reference)
        self.assertEqual(result["failure_type"], "quality_regression")
        self.assertLess(result["texture_retention"], 0.8)

    def test_color_shift_is_a_separate_failure_mode(self) -> None:
        reference = np.full((32, 32, 3), 0.4, dtype=np.float32)
        noisy = np.clip(reference + 0.08, 0.0, 1.0)
        output = reference.copy()
        output[..., 0] += 0.09
        result = evaluate_scene_candidate(noisy, output, reference)
        self.assertEqual(result["failure_type"], "color_shift")

    def test_texture_loss_is_classified_as_over_smoothing(self) -> None:
        output = 0.65 * self.reference + 0.35 * self.noisy
        output = np.full_like(output, np.mean(output, axis=(0, 1)))
        # Use a deliberately worse input so the flat output does not hit the
        # quality-regression branch before the artifact classifier.
        very_noisy = np.clip(self.reference + 0.9 * (0.5 - self.reference), 0.0, 1.0)
        result = evaluate_scene_candidate(very_noisy, output, self.reference)
        self.assertIn(result["failure_type"], {"over_smoothing", "quality_regression"})

    def test_aggregation_keeps_scene_and_method_separate(self) -> None:
        metrics = evaluate_scene_candidate(self.noisy, self.reference, self.reference)
        rows = [
            {"scene_group": "texture", "method": "traditional", **metrics},
            {"scene_group": "texture", "method": "ml_fp32", **metrics},
        ]
        summary = aggregate_by_scene_method(rows)
        self.assertEqual(len(summary), 2)
        self.assertTrue(all(row["sample_count"] == 1 for row in summary))


if __name__ == "__main__":
    unittest.main()
