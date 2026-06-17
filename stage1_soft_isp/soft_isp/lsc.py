"""镜头阴影校正（Lens Shading Correction, LSC）模块。

LSC 用来补偿镜头和传感器角度响应导致的中心亮、边缘暗，以及位置相关色偏。
真实产品通常依赖积分球或均匀白场标定得到每个通道的 gain map。

本模块实现一个学习用的径向 LSC baseline：
    - 中心 gain 为 1.0
    - 越靠近边缘，gain 越接近指定的 edge gain
    - R/Gr/Gb/B 可以设置不同边缘增益，用来观察对 AWB/CCM 的影响
"""

from __future__ import annotations

import numpy as np


def bayer_channel_positions(pattern: str) -> dict[str, tuple[int, int]]:
    """返回 R/Gr/Gb/B 在 2x2 Bayer block 中的位置。"""
    pattern = pattern.upper()
    positions = {
        "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
        "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
        "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
    }
    if pattern not in positions:
        raise ValueError(f"Unsupported Bayer pattern: {pattern}")
    return positions[pattern]


def radial_profile(shape: tuple[int, int], center: tuple[float, float] | None = None, power: float = 2.0) -> np.ndarray:
    """生成 0..1 的径向距离图，中心为 0，最远角点为 1。"""
    height, width = shape
    if center is None:
        cy = (height - 1) / 2.0
        cx = (width - 1) / 2.0
    else:
        cy, cx = center

    y, x = np.mgrid[0:height, 0:width]
    radius = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
    max_radius = max(float(np.max(radius)), 1e-6)
    normalized = np.clip(radius / max_radius, 0.0, 1.0)
    return np.power(normalized, power).astype(np.float32)


def make_lsc_gain_map(
    raw_shape: tuple[int, int],
    bayer_pattern: str,
    edge_gains: dict[str, float] | None = None,
    center: tuple[float, float] | None = None,
    power: float = 2.0,
) -> np.ndarray:
    """构建学习用逐像素 LSC gain map。

    edge_gains 的键为 R/Gr/Gb/B，值表示该通道在最远边缘处的增益。
    未提供时使用一个保守的默认值，避免过度放大边缘噪声。
    """
    if edge_gains is None:
        edge_gains = {"R": 1.18, "Gr": 1.12, "Gb": 1.12, "B": 1.22}

    radial = radial_profile(raw_shape, center=center, power=power)
    gain_map = np.ones(raw_shape, dtype=np.float32)
    for channel, (y_offset, x_offset) in bayer_channel_positions(bayer_pattern).items():
        edge_gain = float(edge_gains.get(channel, 1.0))
        channel_gain = 1.0 + (edge_gain - 1.0) * radial[y_offset::2, x_offset::2]
        gain_map[y_offset::2, x_offset::2] = channel_gain
    return gain_map


def apply_lsc(
    raw_bayer: np.ndarray,
    bayer_pattern: str,
    edge_gains: dict[str, float] | None = None,
    white_level: float | None = None,
    center: tuple[float, float] | None = None,
    power: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """对 Bayer RAW 应用径向 LSC。

    返回 `(corrected, gain_map)`。`corrected` 为 float32，方便后续 demosaic/AWB 继续在线性域处理。
    """
    raw = np.asarray(raw_bayer, dtype=np.float32)
    if raw.ndim != 2:
        raise ValueError(f"raw_bayer must be 2D, got shape {raw.shape}")

    gain_map = make_lsc_gain_map(raw.shape, bayer_pattern, edge_gains=edge_gains, center=center, power=power)
    corrected = raw * gain_map
    if white_level is not None:
        corrected = np.clip(corrected, 0.0, float(white_level))
    return corrected.astype(np.float32), gain_map
