from __future__ import annotations

import numpy as np


def luminance(rgb: np.ndarray) -> np.ndarray:
    return (
        0.2126 * rgb[..., 0]
        + 0.7152 * rgb[..., 1]
        + 0.0722 * rgb[..., 2]
    ).astype(np.float32)


def percentile_exposure(image: np.ndarray, percentile: float = 99.0, target: float = 1.0) -> float:
    image = np.asarray(image, dtype=np.float32)
    values = luminance(image) if image.ndim == 3 and image.shape[2] >= 3 else image
    white = max(float(np.percentile(values, percentile)), 1e-6)
    return target / white


def reinhard_curve(x: np.ndarray) -> np.ndarray:
    x = np.maximum(np.asarray(x, dtype=np.float32), 0.0)
    return (x / (1.0 + x)).astype(np.float32)


def filmic_curve(x: np.ndarray) -> np.ndarray:
    x = np.maximum(np.asarray(x, dtype=np.float32), 0.0)
    a, b, c, d, e, f = 0.15, 0.50, 0.10, 0.20, 0.02, 0.30

    def raw(v: np.ndarray | float) -> np.ndarray | float:
        return ((v * (a * v + c * b) + d * e) / (v * (a * v + b) + d * f)) - e / f

    white_scale = 1.0 / raw(11.2)
    return np.clip(raw(x) * white_scale, 0.0, 1.0).astype(np.float32)


def scurve(x: np.ndarray, midpoint: float = 0.5, contrast: float = 8.0) -> np.ndarray:
    x = np.clip(np.asarray(x, dtype=np.float32), 0.0, 1.0)
    y = 1.0 / (1.0 + np.exp(-contrast * (x - midpoint)))
    y0 = 1.0 / (1.0 + np.exp(contrast * midpoint))
    y1 = 1.0 / (1.0 + np.exp(-contrast * (1.0 - midpoint)))
    return np.clip((y - y0) / max(y1 - y0, 1e-6), 0.0, 1.0).astype(np.float32)


def apply_curve(x: np.ndarray, curve: str) -> np.ndarray:
    if curve == "reinhard":
        return reinhard_curve(x)
    if curve == "filmic":
        return filmic_curve(x)
    if curve == "scurve":
        return scurve(x)
    raise ValueError(f"unknown tone curve: {curve}")


def tone_map_rgb(image: np.ndarray, curve: str, exposure: float) -> np.ndarray:
    return apply_curve(np.asarray(image, dtype=np.float32) * exposure, curve)


def tone_map_luminance(image: np.ndarray, curve: str, exposure: float) -> np.ndarray:
    rgb = np.asarray(image, dtype=np.float32)
    y = luminance(rgb)
    mapped_y = apply_curve(y * exposure, curve)
    scale = mapped_y / np.maximum(y, 1e-6)
    return np.clip(rgb * scale[..., None], 0.0, 1.0).astype(np.float32)


def apply_gamma(image: np.ndarray, gamma: float = 2.2) -> np.ndarray:
    if gamma <= 0:
        raise ValueError("gamma must be positive")
    return np.power(np.clip(image, 0.0, 1.0), 1.0 / gamma).astype(np.float32)
