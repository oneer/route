"""Paired RGB image dataset for noisy/clean denoise experiments."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _list_images(root: Path) -> dict[str, Path]:
    return {
        path.name: path
        for path in sorted(root.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    }


def _load_rgb_tensor(path: Path) -> torch.Tensor:
    image = Image.open(path).convert("RGB")
    array = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(array).permute(2, 0, 1)


class PairedImageDenoiseDataset(Dataset):
    """Load paired noisy/clean RGB images from two directories.

    The two folders must contain files with matching names. If `size` is larger
    than the number of image pairs, pairs are reused with deterministic crops.
    """

    def __init__(
        self,
        noisy_dir: str | Path,
        clean_dir: str | Path,
        patch_size: int,
        size: int | None = None,
        seed: int = 42,
    ) -> None:
        self.noisy_dir = Path(noisy_dir)
        self.clean_dir = Path(clean_dir)
        self.patch_size = int(patch_size)
        self.seed = int(seed)

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
        return self.size

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        noisy_path, clean_path = self.pairs[int(index) % len(self.pairs)]
        noisy = _load_rgb_tensor(noisy_path)
        clean = _load_rgb_tensor(clean_path)

        if noisy.shape != clean.shape:
            raise ValueError(f"Shape mismatch: {noisy_path} vs {clean_path}")

        noisy, clean = self._crop_pair(noisy, clean, int(index))
        return {
            "noisy": noisy,
            "clean": clean,
            "sigma": torch.tensor(0.0, dtype=torch.float32),
        }

    def _crop_pair(
        self, noisy: torch.Tensor, clean: torch.Tensor, index: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        _, h, w = clean.shape
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
