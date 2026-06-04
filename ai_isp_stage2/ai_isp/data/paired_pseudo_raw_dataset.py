"""Paired pseudo RAW dataset built from aligned RGB noisy/clean folders."""

from __future__ import annotations

from pathlib import Path

import torch

from ai_isp.data.paired_image_dataset import _list_images, _load_rgb_tensor
from ai_isp.data.pseudo_raw import rgb_to_rggb_pack


class PairedPseudoRawDataset(torch.utils.data.Dataset):
    """Load paired RGB images and expose them as 4-channel RGGB packs."""

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
        return self.size

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        noisy_path, clean_path = self.pairs[int(index) % len(self.pairs)]
        noisy_rgb = _load_rgb_tensor(noisy_path)
        clean_rgb = _load_rgb_tensor(clean_path)
        if noisy_rgb.shape != clean_rgb.shape:
            raise ValueError(f"Shape mismatch: {noisy_path} vs {clean_path}")

        noisy_rgb, clean_rgb = self._crop_pair(noisy_rgb, clean_rgb, int(index))
        return {
            "noisy": rgb_to_rggb_pack(noisy_rgb),
            "clean": rgb_to_rggb_pack(clean_rgb),
            "sigma": torch.tensor(0.0, dtype=torch.float32),
        }

    def _crop_pair(
        self, noisy: torch.Tensor, clean: torch.Tensor, index: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
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
