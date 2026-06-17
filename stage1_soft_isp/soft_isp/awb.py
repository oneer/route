"""自动白平衡（Auto White Balance, AWB）模块。

AWB 在 Demosaic 之后执行，估计并校正光源色偏，使中性物体恢复接近灰色。
输入和输出都是线性 RGB 图像，只是每个颜色通道乘了不同的增益。

本模块实现 Gray World（灰度世界）算法：
    - 假设场景中所有颜色的平均值应接近灰色
    - 计算截尾均值后用 G 通道为基准估计 R/B 增益
    - 排除最暗和最亮的像素以减少噪声和过曝干扰

函数列表：
    - gray_world_gains:  根据灰度世界假设估计 RGB 增益
    - apply_awb:          将增益应用到线性 RGB 图像
"""

from __future__ import annotations

import numpy as np


def gray_world_gains(
    rgb_linear: np.ndarray,
    low_percentile: float = 5.0,
    high_percentile: float = 95.0,
    max_gain: float = 8.0,
) -> np.ndarray:
    """使用灰度世界假设估计 RGB 白平衡增益。

    算法步骤：
        1. 计算亮度代理 L = mean(R, G, B)
        2. 排除 L 最低 low_percentile% 和最亮 high_percentile% 的像素
        3. 在保留的像素上计算各通道均值
        4. 以 G 通道为基准：R_gain = G_mean / R_mean, B_gain = G_mean / B_mean
        5. clip 增益到 [1/max_gain, max_gain] 范围

    参数:
        rgb_linear:      (H, W, 3) 的线性 RGB 图像
        low_percentile:  排除的最暗像素百分比，默认 5%
        high_percentile: 排除的最亮像素百分比，默认 95%
        max_gain:        最大允许增益（防止极端偏色）

    返回:
        [R_gain, G_gain, B_gain] 形状的 (3,) float32 数组，其中 G_gain = 1.0

    异常:
        ValueError: rgb_linear 不是 (H, W, 3) 形状
    """
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb_linear must have shape (H, W, 3), got {rgb.shape}")

    luminance_proxy = np.mean(rgb, axis=2)
    low = np.percentile(luminance_proxy, low_percentile)
    high = np.percentile(luminance_proxy, high_percentile)
    mask = (luminance_proxy >= low) & (luminance_proxy <= high)
    if not np.any(mask):
        mask = np.ones(luminance_proxy.shape, dtype=bool)

    means = np.maximum(np.mean(rgb[mask], axis=0), 1e-6)
    green_mean = means[1]
    gains = np.array([green_mean / means[0], 1.0, green_mean / means[2]], dtype=np.float32)
    return np.clip(gains, 1.0 / max_gain, max_gain)


def apply_awb(rgb_linear: np.ndarray, gains: np.ndarray, white_level: float | None = None) -> np.ndarray:
    """将逐通道白平衡增益应用到线性 RGB 图像。

    公式：rgb_corrected = rgb * gains（broadcast 到逐像素乘法）

    参数:
        rgb_linear:  (H, W, 3) 的线性 RGB 图像
        gains:       长度为 3 的 float32 数组 [R_gain, G_gain, B_gain]
        white_level: 若不为 None，将结果 clip 到 [0, white_level]

    返回:
        白平衡校正后的 float32 线性 RGB 图像
    """
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    gains = np.asarray(gains, dtype=np.float32).reshape(1, 1, 3)
    corrected = rgb * gains
    if white_level is not None:
        corrected = np.clip(corrected, 0.0, float(white_level))
    return corrected.astype(np.float32)
