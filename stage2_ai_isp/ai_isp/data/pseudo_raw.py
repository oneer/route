"""Small pseudo RAW helpers for Stage 2 AI-ISP experiments."""
# 中文说明：实现 RGB 图像与 RGGB packed 伪 RAW 张量之间的近似转换。

from __future__ import annotations

import torch


def rgb_to_rggb_pack(rgb: torch.Tensor) -> torch.Tensor:
    """Convert RGB tensors to a 4-channel RGGB-like pack.

    This is a controlled bridge experiment, not a physical sensor simulator.
    It samples R/G/B values from an already-rendered RGB image into an RGGB
    layout so Stage 2 can exercise RAW-shaped 4-channel models.
    """
    # 中文说明：把 RGB 张量近似打包成 4 通道 RGGB Bayer 表示。
    if rgb.ndim != 3:
        raise ValueError(f"Expected CHW tensor, got shape {tuple(rgb.shape)}")
    if rgb.shape[0] != 3:
        raise ValueError(f"Expected 3 RGB channels, got {rgb.shape[0]}")

    _, height, width = rgb.shape
    if height % 2 != 0 or width % 2 != 0:
        raise ValueError(f"RGGB pack needs even spatial size, got {height}x{width}")

    red = rgb[0, 0::2, 0::2]
    green_red_row = rgb[1, 0::2, 1::2]
    green_blue_row = rgb[1, 1::2, 0::2]
    blue = rgb[2, 1::2, 1::2]
    return torch.stack([red, green_red_row, green_blue_row, blue], dim=0)


def rggb_pack_to_rgb_preview(pack: torch.Tensor) -> torch.Tensor:
    """Create a simple RGB preview from a 4-channel RGGB-like pack."""
    # 中文说明：把 4 通道 packed RGGB 还原成便于观察的 RGB 预览图。
    if pack.ndim != 3:
        raise ValueError(f"Expected CHW tensor, got shape {tuple(pack.shape)}")
    if pack.shape[0] != 4:
        raise ValueError(f"Expected 4 RGGB channels, got {pack.shape[0]}")

    red, green_red_row, green_blue_row, blue = pack
    green = 0.5 * (green_red_row + green_blue_row)
    return torch.stack([red, green, blue], dim=0)
