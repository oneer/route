"""Black level correction helpers."""

from __future__ import annotations

import numpy as np


def make_black_level_map(raw_shape: tuple[int, int], raw_pattern: np.ndarray, black_levels: list[int]) -> np.ndarray:
    """Build a per-pixel black-level map from rawpy metadata."""
    pattern = np.asarray(raw_pattern)
    if pattern.shape != (2, 2):
        raise ValueError(f"Unsupported raw_pattern shape: {pattern.shape}")

    black_levels_array = np.asarray(black_levels, dtype=np.int32)
    if black_levels_array.size <= int(pattern.max()):
        raise ValueError("black_levels does not cover all entries in raw_pattern")

    black_tile = black_levels_array[pattern]
    tile_rows = (raw_shape[0] + 1) // 2
    tile_cols = (raw_shape[1] + 1) // 2
    return np.tile(black_tile, (tile_rows, tile_cols))[: raw_shape[0], : raw_shape[1]]


def apply_blc(
    raw_visible: np.ndarray,
    raw_pattern: np.ndarray,
    black_levels: list[int],
    white_level: int,
) -> np.ndarray:
    """Subtract black level per Bayer position and clip to the valid signal range."""
    black_map = make_black_level_map(raw_visible.shape, raw_pattern, black_levels)
    corrected = raw_visible.astype(np.int32) - black_map
    corrected_white_map = np.maximum(int(white_level) - black_map, 0)
    corrected = np.minimum(np.maximum(corrected, 0), corrected_white_map)
    return corrected.astype(np.uint16)


def normalized_after_blc(
    raw_visible: np.ndarray,
    raw_pattern: np.ndarray,
    black_levels: list[int],
    white_level: int,
) -> np.ndarray:
    """Return BLC result normalized to 0..1 float32."""
    corrected = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    black_map = make_black_level_map(raw_visible.shape, raw_pattern, black_levels)
    corrected_white_map = np.maximum(float(white_level) - black_map.astype(np.float32), 1.0)
    return corrected.astype(np.float32) / corrected_white_map
