"""进阶 AWB baseline：白点法、Shades-of-Gray 和中性区域误差，用于定位灰度世界失败场景。

中文注释说明：本文件的注释侧重解释数据流、算法意图和实验用途；除注释/docstring 外不改变运行逻辑。
"""

from __future__ import annotations

import numpy as np

from soft_isp.awb import apply_awb, gray_world_gains


# 中文注释：从高亮且低饱和区域估计白点增益，适合有白色物体的场景。
def white_patch_gains(rgb_linear: np.ndarray, percentile: float = 99.0, max_gain: float = 8.0) -> np.ndarray:
    """Estimate gains from bright, low-saturation pixels."""
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb_linear must have shape (H, W, 3), got {rgb.shape}")

    luminance = np.mean(rgb, axis=2)
    threshold = np.percentile(luminance, percentile)
    saturation = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    sat_threshold = np.percentile(saturation, 60.0)
    mask = (luminance >= threshold) & (saturation <= sat_threshold)
    if np.count_nonzero(mask) < 16:
        mask = luminance >= threshold

    means = np.maximum(np.mean(rgb[mask], axis=0), 1e-6)
    green = means[1]
    gains = np.array([green / means[0], 1.0, green / means[2]], dtype=np.float32)
    return np.clip(gains, 1.0 / max_gain, max_gain)


# 中文注释：使用 Minkowski 均值估计白平衡，比普通灰度世界更强调高亮像素。
def shades_of_gray_gains(
    rgb_linear: np.ndarray,
    minkowski_p: float = 6.0,
    low_percentile: float = 5.0,
    high_percentile: float = 95.0,
    max_gain: float = 8.0,
) -> np.ndarray:
    """Estimate gains using a Minkowski mean over mid-brightness pixels."""
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb_linear must have shape (H, W, 3), got {rgb.shape}")

    luminance = np.mean(rgb, axis=2)
    low = np.percentile(luminance, low_percentile)
    high = np.percentile(luminance, high_percentile)
    mask = (luminance >= low) & (luminance <= high)
    if not np.any(mask):
        mask = np.ones(luminance.shape, dtype=bool)

    values = np.maximum(rgb[mask], 0.0)
    means = np.maximum(np.mean(values**minkowski_p, axis=0) ** (1.0 / minkowski_p), 1e-6)
    green = means[1]
    gains = np.array([green / means[0], 1.0, green / means[2]], dtype=np.float32)
    return np.clip(gains, 1.0 / max_gain, max_gain)


# 中文注释：评估疑似中性像素的通道偏差，用作 AWB 效果的诊断指标。
def neutrality_error(rgb_linear: np.ndarray, sample_fraction: float = 0.25) -> dict[str, float]:
    """Measure how far likely neutral pixels are from equal RGB channels."""
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    luminance = np.mean(rgb, axis=2)
    low = np.percentile(luminance, 10.0)
    high = np.percentile(luminance, 90.0)
    saturation = (np.max(rgb, axis=2) - np.min(rgb, axis=2)) / np.maximum(luminance, 1e-6)
    candidates = (luminance >= low) & (luminance <= high)
    if not np.any(candidates):
        candidates = np.ones(luminance.shape, dtype=bool)

    candidate_sat = saturation[candidates]
    threshold = np.percentile(candidate_sat, max(1.0, min(sample_fraction * 100.0, 100.0)))
    mask = candidates & (saturation <= threshold)
    selected = rgb[mask]
    if selected.size == 0:
        selected = rgb.reshape(-1, 3)

    ratios = selected / np.maximum(np.mean(selected, axis=1, keepdims=True), 1e-6)
    return {
        "neutral_rg_error": float(abs(np.mean(ratios[:, 0]) - np.mean(ratios[:, 1]))),
        "neutral_bg_error": float(abs(np.mean(ratios[:, 2]) - np.mean(ratios[:, 1]))),
        "neutral_pixel_fraction": float(np.count_nonzero(mask) / mask.size),
    }


# 中文注释：在同一张图上比较多种 AWB 方法的增益和中性误差。
def compare_awb_methods(rgb_linear: np.ndarray, white_level: float | None = None) -> dict[str, dict[str, float | list[float]]]:
    """Apply several AWB baselines and return gains plus neutral errors."""
    methods = {
        "none": np.ones(3, dtype=np.float32),
        "gray_world": gray_world_gains(rgb_linear),
        "white_patch": white_patch_gains(rgb_linear),
        "shades_of_gray": shades_of_gray_gains(rgb_linear),
    }
    result: dict[str, dict[str, float | list[float]]] = {}
    for name, gains in methods.items():
        corrected = apply_awb(rgb_linear, gains, white_level=white_level)
        errors = neutrality_error(corrected)
        result[name] = {
            "gains": [float(value) for value in gains],
            **errors,
        }
    return result
