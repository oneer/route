"""Paired pseudo RAW dataset built from aligned RGB noisy/clean folders."""
# 中文说明：在配对 RGB 数据上构造伪 RAW 输入，用来模拟 RAW-to-RGB 桥接任务。

from __future__ import annotations

from pathlib import Path

import torch

from ai_isp.data.paired_image_dataset import _list_images, _load_rgb_tensor
from ai_isp.data.pseudo_raw import rgb_to_rggb_pack


class PairedPseudoRawDataset(torch.utils.data.Dataset):
    """Load paired RGB images and expose them as 4-channel RGGB packs."""
    # 中文说明：伪 RAW 配对数据集：把 clean/noisy RGB 变换成 packed Bayer 风格输入。

    def __init__(
        self,
        noisy_dir: str | Path,
        clean_dir: str | Path,
        patch_size: int,
        size: int | None = None,
        seed: int = 42,
        augment: bool = False,
    ) -> None:
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：noisy_dir、clean_dir、patch_size、size、seed、augment。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        self.noisy_dir = Path(noisy_dir)
        self.clean_dir = Path(clean_dir)
        self.patch_size = int(patch_size)
        self.seed = int(seed)
        self.augment = bool(augment)
        if self.patch_size % 2 != 0:
            raise ValueError("paired_pseudo_raw patch_size must be even.")

        noisy_files = _list_images(self.noisy_dir)
        clean_files = _list_images(self.clean_dir)
        names = sorted(set(noisy_files) & set(clean_files))
        if not names:
            raise ValueError(
                f"No paired images found in {self.noisy_dir} and {self.clean_dir}."
            )

        self.pairs = [(noisy_files[name], clean_files[name]) for name in names]
        self.size = int(size) if size is not None else len(self.pairs)

    def __len__(self) -> int:
        """中文说明：返回数据集中可采样样本数量，供 DataLoader 计算 epoch 长度。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        return self.size

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        """中文说明：按索引读取一个样本，并返回训练/验证所需的张量字典。
        
        输入：index。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        noisy_path, clean_path = self.pairs[int(index) % len(self.pairs)]
        noisy_rgb = _load_rgb_tensor(noisy_path)
        clean_rgb = _load_rgb_tensor(clean_path)
        if noisy_rgb.shape != clean_rgb.shape:
            raise ValueError(f"Shape mismatch: {noisy_path} vs {clean_path}")

        noisy_rgb, clean_rgb = self._crop_pair(noisy_rgb, clean_rgb, int(index))
        if self.augment:
            noisy_rgb, clean_rgb = self._augment_pair(
                noisy_rgb, clean_rgb, int(index)
            )
        return {
            "noisy": rgb_to_rggb_pack(noisy_rgb),
            "clean": rgb_to_rggb_pack(clean_rgb),
            "sigma": torch.tensor(0.0, dtype=torch.float32),
        }

    def _crop_pair(
        self, noisy: torch.Tensor, clean: torch.Tensor, index: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """中文说明：实现 `_crop_pair` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：noisy、clean、index。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        _, height, width = clean.shape
        if height < self.patch_size or width < self.patch_size:
            raise ValueError(
                f"Image is smaller than patch_size={self.patch_size}: {height}x{width}"
            )

        generator = torch.Generator().manual_seed(self.seed + index)
        max_y = (height - self.patch_size) // 2
        max_x = (width - self.patch_size) // 2
        y = 2 * int(torch.randint(0, max_y + 1, (1,), generator=generator))
        x = 2 * int(torch.randint(0, max_x + 1, (1,), generator=generator))
        return (
            noisy[:, y : y + self.patch_size, x : x + self.patch_size],
            clean[:, y : y + self.patch_size, x : x + self.patch_size],
        )

    def _augment_pair(
        self, noisy: torch.Tensor, clean: torch.Tensor, index: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """中文说明：实现 `_augment_pair` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：noisy、clean、index。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        generator = torch.Generator().manual_seed(self.seed + index + 20000)
        if bool(torch.randint(0, 2, (1,), generator=generator)):
            noisy, clean = noisy.flip(-1), clean.flip(-1)
        if bool(torch.randint(0, 2, (1,), generator=generator)):
            noisy, clean = noisy.flip(-2), clean.flip(-2)
        if bool(torch.randint(0, 2, (1,), generator=generator)):
            noisy, clean = noisy.transpose(-1, -2), clean.transpose(-1, -2)
        return noisy, clean
