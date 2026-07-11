"""LSC 增益图和显示方向变换的合成回归测试。"""

from __future__ import annotations

import unittest

import numpy as np

from soft_isp.lsc import apply_lsc, make_lsc_gain_map, radial_profile
from soft_isp.orientation import apply_rawpy_orientation, transform_box_for_orientation


class LscAndOrientationTests(unittest.TestCase):
    def test_radial_profile_is_zero_at_center_and_one_at_corners(self) -> None:
        profile = radial_profile((5, 5), power=2.0)
        self.assertEqual(profile.dtype, np.float32)
        self.assertAlmostEqual(float(profile[2, 2]), 0.0)
        np.testing.assert_allclose(profile[[0, 0, 4, 4], [0, 4, 0, 4]], 1.0)

    def test_unit_edge_gains_produce_identity_map_for_all_bayer_positions(self) -> None:
        gains = {channel: 1.0 for channel in ("R", "Gr", "Gb", "B")}
        gain_map = make_lsc_gain_map((6, 8), "RGGB", edge_gains=gains)
        np.testing.assert_array_equal(gain_map, np.ones((6, 8), dtype=np.float32))

    def test_lsc_applies_gain_and_clips_to_white_level(self) -> None:
        raw = np.full((5, 5), 800.0, dtype=np.float32)
        gains = {channel: 2.0 for channel in ("R", "Gr", "Gb", "B")}
        corrected, gain_map = apply_lsc(raw, "RGGB", edge_gains=gains, white_level=1000.0)
        self.assertEqual(corrected.dtype, np.float32)
        self.assertAlmostEqual(float(corrected[2, 2]), 800.0)
        self.assertAlmostEqual(float(gain_map[0, 0]), 2.0)
        self.assertAlmostEqual(float(corrected[0, 0]), 1000.0)

    def test_lsc_rejects_non_bayer_input_and_unknown_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be 2D"):
            apply_lsc(np.zeros((2, 2, 3), dtype=np.float32), "RGGB")
        with self.assertRaisesRegex(ValueError, "Unsupported Bayer pattern"):
            make_lsc_gain_map((4, 4), "RGBX")

    def test_orientation_matches_expected_flip_and_rotations(self) -> None:
        image = np.arange(6).reshape(2, 3)
        np.testing.assert_array_equal(apply_rawpy_orientation(image, 1), np.fliplr(image))
        np.testing.assert_array_equal(apply_rawpy_orientation(image, 2), np.flipud(image))
        np.testing.assert_array_equal(apply_rawpy_orientation(image, 3), np.rot90(image, 2))
        np.testing.assert_array_equal(apply_rawpy_orientation(image, 5), np.rot90(image, 1))
        np.testing.assert_array_equal(apply_rawpy_orientation(image, 6), np.rot90(image, -1))

    def test_roi_box_follows_horizontal_flip(self) -> None:
        transformed = transform_box_for_orientation(1, 1, 2, 1, (4, 6), flip=1)
        self.assertEqual(transformed, (3.0, 1.0, 2.0, 1.0))


if __name__ == "__main__":
    unittest.main()
