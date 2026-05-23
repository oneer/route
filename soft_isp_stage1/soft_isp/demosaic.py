"""Simple bilinear demosaic helpers for Bayer RAW arrays."""

from __future__ import annotations

import cv2
import numpy as np


def bayer_positions(pattern: str) -> dict[str, tuple[int, int]]:
    pattern = pattern.upper()
    positions = {
        "RGGB": {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "G1": (0, 1), "G2": (1, 0), "R": (1, 1)},
        "GRBG": {"G1": (0, 0), "R": (0, 1), "B": (1, 0), "G2": (1, 1)},
        "GBRG": {"G1": (0, 0), "B": (0, 1), "R": (1, 0), "G2": (1, 1)},
    }
    if pattern not in positions:
        raise ValueError(f"Unsupported Bayer pattern: {pattern}")
    return positions[pattern]


def _known_mask(shape: tuple[int, int], offsets: list[tuple[int, int]]) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.float32)
    for y_offset, x_offset in offsets:
        mask[y_offset::2, x_offset::2] = 1.0
    return mask


def _interpolate_channel(raw: np.ndarray, mask: np.ndarray) -> np.ndarray:
    raw_f32 = raw.astype(np.float32)
    kernel = np.array(
        [
            [1.0, 2.0, 1.0],
            [2.0, 4.0, 2.0],
            [1.0, 2.0, 1.0],
        ],
        dtype=np.float32,
    )
    weighted_sum = cv2.filter2D(raw_f32 * mask, -1, kernel, borderType=cv2.BORDER_REFLECT_101)
    weight = cv2.filter2D(mask, -1, kernel, borderType=cv2.BORDER_REFLECT_101)
    interpolated = weighted_sum / np.maximum(weight, 1e-6)
    interpolated[mask > 0] = raw_f32[mask > 0]
    return interpolated


def bilinear_demosaic(raw_bayer: np.ndarray, bayer_pattern: str) -> np.ndarray:
    """Convert a single-channel Bayer RAW image to a linear RGB float32 image."""
    positions = bayer_positions(bayer_pattern)
    raw = np.asarray(raw_bayer)
    if raw.ndim != 2:
        raise ValueError(f"raw_bayer must be 2D, got shape {raw.shape}")

    r_mask = _known_mask(raw.shape, [positions["R"]])
    g_mask = _known_mask(raw.shape, [positions["G1"], positions["G2"]])
    b_mask = _known_mask(raw.shape, [positions["B"]])

    rgb = np.stack(
        [
            _interpolate_channel(raw, r_mask),
            _interpolate_channel(raw, g_mask),
            _interpolate_channel(raw, b_mask),
        ],
        axis=-1,
    )
    return rgb.astype(np.float32)


def rgb_preview(
    rgb_linear: np.ndarray,
    black: float = 0.0,
    white: float | None = None,
    gamma: float = 2.2,
) -> np.ndarray:
    """Map linear RGB data to an 8-bit display preview."""
    rgb = rgb_linear.astype(np.float32) - float(black)
    if white is None:
        white = float(np.percentile(rgb, 99.5))
    white = max(float(white), 1.0)
    preview = np.clip(rgb / white, 0.0, 1.0)
    if gamma > 0:
        preview = np.power(preview, 1.0 / gamma)
    return (preview * 255.0 + 0.5).astype(np.uint8)
