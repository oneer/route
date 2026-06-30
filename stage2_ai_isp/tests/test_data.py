"""中文说明：单元测试代码，用小规模输入检查数据、模型、指标和训练引擎的基本行为。

本文件属于 Stage2 AI ISP 实验代码；注释重点解释数据流、训练逻辑或导出用途，不改变任何运行行为。
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from ai_isp.data.paired_image_dataset import PairedImageDenoiseDataset
from ai_isp.data.pseudo_raw import rgb_to_rggb_pack, rggb_pack_to_rgb_preview
from ai_isp.data.toy_rgb_dataset import ToyRGBDenoiseDataset


class DatasetTests(unittest.TestCase):
    """中文说明：数据相关单元测试集合。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    def test_toy_dataset_is_deterministic(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        dataset = ToyRGBDenoiseDataset(2, 32, 0.03, 0.12, seed=7)
        first = dataset[0]
        second = dataset[0]
        self.assertTrue(torch.equal(first["clean"], second["clean"]))
        self.assertTrue(torch.equal(first["noisy"], second["noisy"]))

    def test_paired_dataset_uses_identical_crop(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            noisy_dir = root / "noisy"
            clean_dir = root / "clean"
            noisy_dir.mkdir()
            clean_dir.mkdir()
            array = np.arange(48 * 48 * 3, dtype=np.uint8).reshape(48, 48, 3)
            Image.fromarray(array).save(noisy_dir / "pair.png")
            Image.fromarray(array).save(clean_dir / "pair.png")
            sample = PairedImageDenoiseDataset(
                noisy_dir, clean_dir, patch_size=24, seed=3
            )[0]
            self.assertTrue(torch.equal(sample["noisy"], sample["clean"]))

    def test_full_image_dataset(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("noisy", "clean"):
                path = root / folder
                path.mkdir()
                Image.new("RGB", (37, 29), (10, 20, 30)).save(path / "pair.png")
            sample = PairedImageDenoiseDataset(
                root / "noisy", root / "clean", patch_size=None
            )[0]
            self.assertEqual(tuple(sample["clean"].shape), (3, 29, 37))

    def test_rggb_channel_positions(self) -> None:
        """中文说明：测试一个具体行为是否符合预期，避免后续修改破坏阶段功能。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        rgb = torch.zeros(3, 4, 4)
        rgb[0] = 1.0
        rgb[1] = 0.5
        rgb[2] = 0.25
        pack = rgb_to_rggb_pack(rgb)
        self.assertEqual(tuple(pack.shape), (4, 2, 2))
        self.assertTrue(torch.all(pack[0] == 1.0))
        self.assertTrue(torch.all(pack[1:3] == 0.5))
        self.assertTrue(torch.all(pack[3] == 0.25))
        preview = rggb_pack_to_rgb_preview(pack)
        self.assertTrue(torch.allclose(preview, rgb[:, :2, :2]))


if __name__ == "__main__":
    unittest.main()
