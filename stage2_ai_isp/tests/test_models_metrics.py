"""中文说明：单元测试代码，用小规模输入检查数据、模型、指标和训练引擎的基本行为。

本文件属于 Stage2 AI ISP 实验代码；注释重点解释数据流、训练逻辑或导出用途，不改变任何运行行为。
"""

from __future__ import annotations

import unittest

import torch

from ai_isp.metrics import batch_psnr, batch_ssim
from ai_isp.models import build_model


class ModelAndMetricTests(unittest.TestCase):
    """中文说明：模型和指标相关单元测试集合。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    def test_all_models_preserve_shape(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        tensor = torch.rand(2, 3, 65, 67)
        for name in ("tiny_cnn", "dncnn", "unet", "nafnet_lite"):
            with self.subTest(model=name):
                output = build_model({"name": name})(tensor)
                self.assertEqual(output.shape, tensor.shape)

    def test_residual_dncnn_rejects_channel_mismatch(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
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
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        tensor = torch.rand(2, 3, 32, 32)
        self.assertTrue(torch.allclose(batch_psnr(tensor, tensor), torch.full((2,), 80.0)))
        self.assertTrue(torch.allclose(batch_ssim(tensor, tensor), torch.ones(2), atol=1e-5))

    def test_ssim_rejects_shape_mismatch(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        with self.assertRaises(ValueError):
            batch_ssim(torch.rand(1, 3, 16, 16), torch.rand(1, 3, 15, 16))


if __name__ == "__main__":
    unittest.main()
