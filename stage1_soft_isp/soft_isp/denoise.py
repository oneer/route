"""Small traditional RGB denoise baselines used by Stage 1 tuning.

The implementation operates on normalized RGB and intentionally exposes only
the two bilateral-filter parameters that are varied by the tuning sweep.
"""

from __future__ import annotations

import cv2
import numpy as np


def bilateral_denoise_rgb(
    rgb_01: np.ndarray,
    sigma_range: float,
    sigma_space: float = 3.0,
    diameter: int = 5,
) -> np.ndarray:
    """Apply an OpenCV bilateral filter to an HxWx3 normalized RGB image."""
    image = np.asarray(rgb_01, dtype=np.float32)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("rgb_01 must have shape HxWx3")
    if sigma_range <= 0.0 or sigma_space <= 0.0:
        raise ValueError("sigma_range and sigma_space must be positive")
    if diameter <= 0 or diameter % 2 == 0:
        raise ValueError("diameter must be a positive odd number")
    filtered = cv2.bilateralFilter(
        np.clip(image, 0.0, 1.0),
        diameter,
        sigmaColor=float(sigma_range),
        sigmaSpace=float(sigma_space),
        borderType=cv2.BORDER_REFLECT101,
    )
    return np.clip(filtered, 0.0, 1.0).astype(np.float32)
