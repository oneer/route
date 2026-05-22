"""Dead pixel correction helpers for Bayer RAW arrays."""

from __future__ import annotations

import numpy as np

from soft_isp.stats import split_bayer


def _median3x3(channel: np.ndarray) -> np.ndarray:
    padded = np.pad(channel, 1, mode="edge")
    neighbors = [
        padded[0:-2, 0:-2],
        padded[0:-2, 1:-1],
        padded[0:-2, 2:],
        padded[1:-1, 0:-2],
        padded[1:-1, 1:-1],
        padded[1:-1, 2:],
        padded[2:, 0:-2],
        padded[2:, 1:-1],
        padded[2:, 2:],
    ]
    return np.median(np.stack(neighbors, axis=0), axis=0)


def detect_channel_defects(
    channel: np.ndarray,
    min_delta: int = 256,
    mad_k: float = 12.0,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Detect impulse-like outliers in one same-color Bayer channel."""
    channel_i32 = channel.astype(np.int32)
    local_median = _median3x3(channel_i32).astype(np.int32)
    residual = np.abs(channel_i32 - local_median)

    residual_median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - residual_median)))
    robust_threshold = residual_median + mad_k * max(mad, 1.0)
    threshold = max(float(min_delta), robust_threshold)

    mask = residual > threshold
    return mask, local_median, threshold


def detect_defects(
    raw_blc: np.ndarray,
    bayer_pattern: str,
    min_delta: int = 256,
    mad_k: float = 12.0,
) -> dict:
    """Detect defect candidates per Bayer channel."""
    channels = split_bayer(raw_blc, bayer_pattern)
    masks = {}
    medians = {}
    thresholds = {}

    for name, channel in channels.items():
        mask, local_median, threshold = detect_channel_defects(channel, min_delta=min_delta, mad_k=mad_k)
        masks[name] = mask
        medians[name] = local_median
        thresholds[name] = threshold

    return {
        "masks": masks,
        "local_medians": medians,
        "thresholds": thresholds,
    }


def repair_defects(raw_blc: np.ndarray, bayer_pattern: str, detection: dict) -> np.ndarray:
    """Replace detected defect candidates with their same-color local median."""
    repaired = raw_blc.copy()
    positions = {
        "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
        "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
        "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
    }[bayer_pattern.upper()]

    for name, (y_offset, x_offset) in positions.items():
        channel_view = repaired[y_offset::2, x_offset::2]
        mask = detection["masks"][name]
        median = detection["local_medians"][name]
        channel_view[mask] = np.clip(median[mask], 0, np.iinfo(repaired.dtype).max).astype(repaired.dtype)

    return repaired


def merge_channel_masks(raw_shape: tuple[int, int], bayer_pattern: str, masks: dict[str, np.ndarray]) -> np.ndarray:
    """Merge per-channel masks back to full-resolution Bayer coordinates."""
    full_mask = np.zeros(raw_shape, dtype=bool)
    positions = {
        "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
        "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
        "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
    }[bayer_pattern.upper()]

    for name, (y_offset, x_offset) in positions.items():
        full_mask[y_offset::2, x_offset::2] = masks[name]
    return full_mask
