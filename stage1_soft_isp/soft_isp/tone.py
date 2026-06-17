"""Gamma 校正与色调映射（Tone Mapping）模块。

这些函数位于 ISP 管线的末端，负责将线性 RGB 转换为适合显示器观看的图像。
主要解决两个问题：
    1. 动态范围压缩：RAW/线性 RGB 的动态范围通常远超 8-bit 显示范围
    2. 显示编码：人眼对亮度的感知是非线性的，显示设备也期望 gamma 编码的输入

函数列表：
    - normalize_by_percentile: 用高分位点做归一化到 0~1
    - reinhard_tone_map:       全局 Reinhard 色调映射曲线
    - apply_gamma:             应用显示 gamma（默认 1/2.2 幂函数）
    - to_uint8:                将 0~1 浮点图像转换为 uint8（0~255）
"""

from __future__ import annotations

import numpy as np


def normalize_by_percentile(rgb_linear: np.ndarray, percentile: float = 99.5) -> np.ndarray:
    """Scale linear RGB to 0..1 using a high percentile as display white."""
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    white = max(float(np.percentile(rgb, percentile)), 1e-6)
    return np.clip(rgb / white, 0.0, 1.0).astype(np.float32)


def reinhard_tone_map(rgb_linear: np.ndarray, percentile: float = 99.5) -> np.ndarray:
    """Apply a simple global Reinhard tone curve after percentile exposure scaling."""
    exposed = normalize_by_percentile(rgb_linear, percentile)
    return (exposed / (1.0 + exposed)).astype(np.float32)


def apply_gamma(rgb_01: np.ndarray, gamma: float = 2.2) -> np.ndarray:
    """Apply display gamma to a 0..1 RGB image."""
    rgb = np.clip(np.asarray(rgb_01, dtype=np.float32), 0.0, 1.0)
    if gamma <= 0:
        raise ValueError(f"gamma must be positive, got {gamma}")
    return np.power(rgb, 1.0 / gamma).astype(np.float32)


def to_uint8(rgb_01: np.ndarray) -> np.ndarray:
    """Convert a 0..1 RGB image to uint8."""
    rgb = np.clip(np.asarray(rgb_01, dtype=np.float32), 0.0, 1.0)
    return (rgb * 255.0 + 0.5).astype(np.uint8)
