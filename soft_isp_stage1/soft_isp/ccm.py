"""Color correction matrix helpers for linear RGB images."""

from __future__ import annotations

import numpy as np


def apply_ccm(rgb_linear: np.ndarray, matrix: np.ndarray, white_level: float | None = None) -> np.ndarray:
    """Apply a 3x3 CCM to an HxWx3 linear RGB image."""
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    ccm = np.asarray(matrix, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb_linear must have shape (H, W, 3), got {rgb.shape}")
    if ccm.shape != (3, 3):
        raise ValueError(f"matrix must have shape (3, 3), got {ccm.shape}")

    corrected = rgb @ ccm.T
    if white_level is not None:
        corrected = np.clip(corrected, 0.0, float(white_level))
    return corrected.astype(np.float32)


def ccm_from_rawpy_color_matrix(color_matrix: np.ndarray) -> np.ndarray:
    """Use rawpy's color_matrix as a learning-oriented 3x3 CCM."""
    matrix = np.asarray(color_matrix, dtype=np.float32)
    if matrix.shape[0] < 3 or matrix.shape[1] < 3:
        return np.eye(3, dtype=np.float32)
    ccm = matrix[:3, :3].astype(np.float32)
    if not np.all(np.isfinite(ccm)) or np.max(np.abs(ccm)) == 0:
        return np.eye(3, dtype=np.float32)
    return ccm
