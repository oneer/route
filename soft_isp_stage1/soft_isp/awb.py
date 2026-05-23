"""Auto white balance helpers for linear RGB images."""

from __future__ import annotations

import numpy as np


def gray_world_gains(
    rgb_linear: np.ndarray,
    low_percentile: float = 5.0,
    high_percentile: float = 95.0,
    max_gain: float = 8.0,
) -> np.ndarray:
    """Estimate RGB gains with the gray-world assumption."""
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
    """Apply per-channel white-balance gains to a linear RGB image."""
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    gains = np.asarray(gains, dtype=np.float32).reshape(1, 1, 3)
    corrected = rgb * gains
    if white_level is not None:
        corrected = np.clip(corrected, 0.0, float(white_level))
    return corrected.astype(np.float32)
