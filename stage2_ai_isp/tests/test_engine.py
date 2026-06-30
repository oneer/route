"""中文说明：单元测试代码，用小规模输入检查数据、模型、指标和训练引擎的基本行为。

本文件属于 Stage2 AI ISP 实验代码；注释重点解释数据流、训练逻辑或导出用途，不改变任何运行行为。
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from ai_isp.engine.checkpoint import load_checkpoint, save_checkpoint
from ai_isp.engine.train import build_criterion, train_from_config
from ai_isp.models import build_model


class EngineTests(unittest.TestCase):
    """中文说明：训练引擎相关单元测试集合。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    def test_unknown_loss_fails(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        with self.assertRaises(ValueError):
            build_criterion("charbonier")

    def test_checkpoint_round_trip(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        with tempfile.TemporaryDirectory() as directory:
            model = build_model({"name": "tiny_cnn", "features": 4})
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
            path = Path(directory) / "checkpoint.pth"
            save_checkpoint(path, model, optimizer, 7, 21.5, {"test": True})
            restored = build_model({"name": "tiny_cnn", "features": 4})
            checkpoint = load_checkpoint(path, restored)
            self.assertEqual(checkpoint["step"], 7)
            for left, right in zip(model.parameters(), restored.parameters()):
                self.assertTrue(torch.equal(left, right))

    def test_minimal_training_smoke(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "experiment": {"seed": 1, "output_dir": directory},
                "data": {
                    "patch_size": 16,
                    "train_size": 4,
                    "val_size": 2,
                    "noise": {
                        "type": "gaussian",
                        "sigma_min": 0.03,
                        "sigma_max": 0.03,
                    },
                },
                "model": {
                    "name": "tiny_cnn",
                    "in_channels": 3,
                    "out_channels": 3,
                    "features": 4,
                },
                "train": {
                    "steps": 2,
                    "batch_size": 2,
                    "learning_rate": 1e-3,
                    "loss": "l1",
                    "log_every": 1,
                    "val_every": 1,
                    "num_workers": 0,
                    "device": "cpu",
                },
            }
            train_from_config(config)
            output = Path(directory)
            self.assertTrue((output / "metrics.csv").exists())
            self.assertTrue((output / "checkpoints" / "last.pth").exists())

    def test_resume_appends_metrics(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "experiment": {"seed": 2, "output_dir": directory},
                "data": {
                    "patch_size": 16,
                    "train_size": 2,
                    "val_size": 1,
                    "noise": {
                        "type": "gaussian",
                        "sigma_min": 0.03,
                        "sigma_max": 0.03,
                    },
                },
                "model": {"name": "tiny_cnn", "features": 4},
                "train": {
                    "steps": 1,
                    "batch_size": 1,
                    "learning_rate": 1e-3,
                    "loss": "l1",
                    "log_every": 1,
                    "val_every": 1,
                    "num_workers": 0,
                    "device": "cpu",
                },
            }
            train_from_config(config)
            checkpoint = Path(directory) / "checkpoints" / "last.pth"
            config["train"]["steps"] = 2
            config["train"]["resume"] = str(checkpoint)
            train_from_config(config)
            rows = (Path(directory) / "metrics.csv").read_text(
                encoding="utf-8"
            ).strip().splitlines()
            self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
