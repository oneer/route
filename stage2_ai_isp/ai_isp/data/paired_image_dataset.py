"""Paired RGB image dataset for noisy/clean denoise experiments."""
# 中文说明：读取 noisy/clean 成对 RGB 图片，并在训练时随机裁剪成 patch。

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _list_images(root: Path) -> dict[str, Path]:
    """中文说明：实现 `_list_images` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：root。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    return {
        path.name: path
        for path in sorted(root.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    }


def _load_rgb_tensor(path: Path) -> torch.Tensor:
    """中文说明：实现 `_load_rgb_tensor` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    image = Image.open(path).convert("RGB")
    array = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(array).permute(2, 0, 1)


class PairedImageDenoiseDataset(Dataset):
    """Load paired noisy/clean RGB images from two directories.

    The two folders must contain files with matching names. If `size` is larger
    than the number of image pairs, pairs are reused with deterministic crops.
    """
    # 中文说明：配对图像去噪数据集：从 noisy_dir 和 clean_dir 读取同名样本。

    def __init__(
        self,
        noisy_dir: str | Path,
        clean_dir: str | Path,
        patch_size: int | None,
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
        self.patch_size = int(patch_size) if patch_size is not None else None
        self.seed = int(seed)
        self.augment = bool(augment)

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
        noisy = _load_rgb_tensor(noisy_path)
        clean = _load_rgb_tensor(clean_path)

        if noisy.shape != clean.shape:
            raise ValueError(f"Shape mismatch: {noisy_path} vs {clean_path}")

        if self.patch_size is not None:
            noisy, clean = self._crop_pair(noisy, clean, int(index))
        if self.augment:
            noisy, clean = self._augment_pair(noisy, clean, int(index))
        return {
            "noisy": noisy,
            "clean": clean,
            "sigma": torch.tensor(0.0, dtype=torch.float32),
        }

    def _crop_pair(
        self, noisy: torch.Tensor, clean: torch.Tensor, index: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """中文说明：实现 `_crop_pair` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：noisy、clean、index。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        _, h, w = clean.shape
        assert self.patch_size is not None
        if h < self.patch_size or w < self.patch_size:
            raise ValueError(
                f"Image is smaller than patch_size={self.patch_size}: {h}x{w}"
            )

        generator = torch.Generator().manual_seed(self.seed + index)
        y = int(torch.randint(0, h - self.patch_size + 1, (1,), generator=generator))
        x = int(torch.randint(0, w - self.patch_size + 1, (1,), generator=generator))
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
