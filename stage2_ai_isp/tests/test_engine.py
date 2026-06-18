from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from ai_isp.engine.checkpoint import load_checkpoint, save_checkpoint
from ai_isp.engine.train import build_criterion, train_from_config
from ai_isp.models import build_model


class EngineTests(unittest.TestCase):
    def test_unknown_loss_fails(self) -> None:
        with self.assertRaises(ValueError):
            build_criterion("charbonier")

    def test_checkpoint_round_trip(self) -> None:
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
