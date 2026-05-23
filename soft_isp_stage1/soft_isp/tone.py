"""Gamma and tone-mapping helpers for display previews."""

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
