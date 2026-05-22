"""Bilinear demosaic helpers for Bayer RAW arrays."""

from __future__ import annotations

import numpy as np


BAYER_POSITIONS = {
    "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
    "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
    "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
    "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
}


def _channel_mask(raw_shape: tuple[int, int], y_offset: int, x_offset: int) -> np.ndarray:
    mask = np.zeros(raw_shape, dtype=bool)
    mask[y_offset::2, x_offset::2] = True
    return mask


def _weighted_average(known_values: np.ndarray, known_mask: np.ndarray) -> np.ndarray:
    """Interpolate missing samples with a 3x3 bilinear kernel."""
    kernel = np.array(
        [
            [1.0, 2.0, 1.0],
            [2.0, 4.0, 2.0],
            [1.0, 2.0, 1.0],
        ],
        dtype=np.float32,
    )
    values = np.pad(known_values, 1, mode="constant")
    weights = np.pad(known_mask.astype(np.float32), 1, mode="constant")

    numerator = np.zeros_like(known_values, dtype=np.float32)
    denominator = np.zeros_like(known_values, dtype=np.float32)
    height, width = known_values.shape

    for y in range(3):
        for x in range(3):
            weight = kernel[y, x]
            numerator += values[y : y + height, x : x + width] * weight
            denominator += weights[y : y + height, x : x + width] * weight

    return numerator / np.maximum(denominator, 1.0)


def demosaic_bilinear(raw: np.ndarray, bayer_pattern: str) -> np.ndarray:
    """Convert a Bayer RAW image to linear RGB with bilinear interpolation.

    The function keeps measured Bayer samples unchanged and only interpolates
    the missing color channels. The returned array is float32 so later modules
    can apply AWB, CCM, and tone mapping without integer clipping.
    """
    pattern = bayer_pattern.upper()
    if pattern not in BAYER_POSITIONS:
        raise ValueError(f"Unsupported Bayer pattern: {bayer_pattern}")
    if raw.ndim != 2:
        raise ValueError(f"Expected a 2D Bayer RAW array, got shape {raw.shape}")

    raw_f32 = raw.astype(np.float32)
    rgb = np.zeros((*raw.shape, 3), dtype=np.float32)
    channel_indices = {"R": 0, "G": 1, "B": 2}

    masks = {}
    for name, (y_offset, x_offset) in BAYER_POSITIONS[pattern].items():
        masks[name] = _channel_mask(raw.shape, y_offset, x_offset)

    for color_name in ("R", "B"):
        mask = masks[color_name]
        known = np.where(mask, raw_f32, 0.0)
        channel = _weighted_average(known, mask)
        channel[mask] = raw_f32[mask]
        rgb[:, :, channel_indices[color_name]] = channel

    green_mask = masks["Gr"] | masks["Gb"]
    green_known = np.where(green_mask, raw_f32, 0.0)
    green = _weighted_average(green_known, green_mask)
    green[green_mask] = raw_f32[green_mask]
    rgb[:, :, channel_indices["G"]] = green

    return rgb


def normalize_rgb(rgb: np.ndarray, white_level: float | None = None) -> np.ndarray:
    """Normalize linear RGB to 0..1 for preview or simple downstream use."""
    rgb_f32 = rgb.astype(np.float32)
    if white_level is None:
        white_level = max(float(np.percentile(rgb_f32, 99.5)), 1.0)
    return np.clip(rgb_f32 / max(float(white_level), 1.0), 0.0, 1.0)
