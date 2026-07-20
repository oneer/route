"""ColorChecker-style CCM fitting and color-error evaluation."""

from __future__ import annotations

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

from soft_isp.ccm import apply_ccm


def _validate_patches(measured_rgb: np.ndarray, reference_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    measured = np.asarray(measured_rgb, dtype=np.float64)
    reference = np.asarray(reference_rgb, dtype=np.float64)
    if measured.ndim != 2 or measured.shape[1] != 3:
        raise ValueError("measured_rgb must have shape Nx3")
    if reference.shape != measured.shape:
        raise ValueError("reference_rgb must match measured_rgb shape")
    if measured.shape[0] < 3:
        raise ValueError("at least three patches are required")
    if not np.all(np.isfinite(measured)) or not np.all(np.isfinite(reference)):
        raise ValueError("patch values must be finite")
    return measured, reference


def fit_ccm_least_squares(
    measured_rgb: np.ndarray,
    reference_rgb: np.ndarray,
    regularization: float = 1.0e-6,
) -> np.ndarray:
    """Fit a 3x3 matrix for corrected = measured times ccm transpose."""
    measured, reference = _validate_patches(measured_rgb, reference_rgb)
    if regularization < 0.0:
        raise ValueError("regularization must be non-negative")
    gram = measured.T @ measured + regularization * np.eye(3)
    mapping = np.linalg.solve(gram, measured.T @ reference)
    return mapping.T.astype(np.float32)


def evaluate_colorchecker(
    measured_rgb: np.ndarray,
    reference_rgb: np.ndarray,
    ccm: np.ndarray,
) -> dict[str, float | int | list[float]]:
    """Apply a CCM and report mean/P95/worst-patch CIEDE2000."""
    measured, reference = _validate_patches(measured_rgb, reference_rgb)
    corrected = apply_ccm(measured[None, :, :], ccm, white_level=1.0)[0]
    delta_e = deltaE_ciede2000(
        rgb2lab(np.clip(reference, 0.0, 1.0)[None, :, :])[0],
        rgb2lab(np.clip(corrected, 0.0, 1.0)[None, :, :])[0],
    )
    worst = int(np.argmax(delta_e))
    return {
        "mean_delta_e_2000": float(np.mean(delta_e)),
        "p95_delta_e_2000": float(np.percentile(delta_e, 95.0)),
        "worst_patch_index": worst,
        "worst_patch_delta_e_2000": float(delta_e[worst]),
        "per_patch_delta_e_2000": [float(value) for value in delta_e],
    }
