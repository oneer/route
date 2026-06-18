from __future__ import annotations

import unittest

import numpy as np

from soft_isp.demosaic import bilinear_demosaic
from soft_isp.dpc import detect_defects, merge_channel_masks, repair_defects


class DpcAndDemosaicTests(unittest.TestCase):
    def test_injected_hot_pixel_is_detected_and_repaired(self) -> None:
        raw = np.full((12, 12), 1000, dtype=np.uint16)
        raw[4, 4] = 6000
        detection = detect_defects(raw, "RGGB", min_delta=500, mad_k=6.0)
        full_mask = merge_channel_masks(raw.shape, "RGGB", detection["masks"])
        repaired = repair_defects(raw, "RGGB", detection)
        self.assertTrue(bool(full_mask[4, 4]))
        self.assertEqual(int(repaired[4, 4]), 1000)

    def test_constant_bayer_remains_constant_after_demosaic(self) -> None:
        raw = np.full((8, 8), 512, dtype=np.uint16)
        rgb = bilinear_demosaic(raw, "RGGB")
        self.assertEqual(rgb.shape, (8, 8, 3))
        np.testing.assert_allclose(rgb, 512.0, atol=1e-5)

    def test_sampled_values_are_preserved(self) -> None:
        raw = np.arange(64, dtype=np.uint16).reshape(8, 8)
        rgb = bilinear_demosaic(raw, "RGGB")
        np.testing.assert_array_equal(rgb[0::2, 0::2, 0], raw[0::2, 0::2])
        np.testing.assert_array_equal(rgb[1::2, 1::2, 2], raw[1::2, 1::2])


if __name__ == "__main__":
    unittest.main()
