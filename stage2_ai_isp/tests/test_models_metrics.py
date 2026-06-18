from __future__ import annotations

import unittest

import torch

from ai_isp.metrics import batch_psnr, batch_ssim
from ai_isp.models import build_model


class ModelAndMetricTests(unittest.TestCase):
    def test_all_models_preserve_shape(self) -> None:
        tensor = torch.rand(2, 3, 65, 67)
        for name in ("tiny_cnn", "dncnn", "unet", "nafnet_lite"):
            with self.subTest(model=name):
                output = build_model({"name": name})(tensor)
                self.assertEqual(output.shape, tensor.shape)

    def test_residual_dncnn_rejects_channel_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            build_model(
                {
                    "name": "dncnn",
                    "in_channels": 3,
                    "out_channels": 4,
                    "residual": True,
                }
            )

    def test_identity_metrics(self) -> None:
        tensor = torch.rand(2, 3, 32, 32)
        self.assertTrue(torch.allclose(batch_psnr(tensor, tensor), torch.full((2,), 80.0)))
        self.assertTrue(torch.allclose(batch_ssim(tensor, tensor), torch.ones(2), atol=1e-5))

    def test_ssim_rejects_shape_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            batch_ssim(torch.rand(1, 3, 16, 16), torch.rand(1, 3, 15, 16))


if __name__ == "__main__":
    unittest.main()
