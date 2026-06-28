"""Feasible RAW/IQ diagnostics for Stage 1.

These helpers intentionally avoid claiming lab-grade image quality results.
They use existing RAW frames and local ROIs to produce interview-useful
diagnostics: clipping, approximate SNR, approximate dynamic range, and an
edge-based MTF50 proxy.
"""

from __future__ import annotations

import math

import numpy as np


def clipping_fractions(raw: np.ndarray, black_level: float, white_level: float, margin: float = 16.0) -> dict[str, float]:
    """Return near-black and near-white fractions for a RAW image."""
    data = np.asarray(raw, dtype=np.float32)
    total = float(data.size)
    if total == 0:
        raise ValueError("raw must not be empty")
    return {
        "near_black_fraction": float(np.count_nonzero(data <= black_level + margin) / total),
        "near_white_fraction": float(np.count_nonzero(data >= white_level - margin) / total),
    }


def roi_snr_db(roi: np.ndarray, black_level: float) -> dict[str, float]:
    """Estimate ROI SNR from mean signal above black and local standard deviation.

    This is useful for relative diagnosis across ROIs or parameter variants.
    It is not a sensor-lab SNR result because a natural-image ROI mixes texture
    with noise unless it comes from a true flat-field frame.
    """
    data = np.asarray(roi, dtype=np.float32)
    signal = max(float(np.mean(data) - black_level), 0.0)
    noise = max(float(np.std(data)), 1e-6)
    return {
        "signal_mean": signal,
        "noise_std": noise,
        "snr_db": float(20.0 * math.log10(max(signal, 1e-6) / noise)),
    }


def approximate_dynamic_range_db(white_level: float, black_level: float, noise_floor: float) -> float:
    """Estimate dynamic range from usable signal and a chosen noise floor."""
    usable_signal = max(float(white_level) - float(black_level), 1e-6)
    floor = max(float(noise_floor), 1e-6)
    return float(20.0 * math.log10(usable_signal / floor))


def edge_mtf50_proxy(gray: np.ndarray, roi: tuple[int, int, int, int]) -> dict[str, float]:
    """Return a lightweight edge sharpness proxy for a local gray ROI.

    The proxy finds the dominant horizontal/vertical gradient direction and
    reports the spatial frequency where the normalized derivative spectrum
    drops below 50%. It is meant to rank comparable crops, not replace a
    slanted-edge chart measurement.
    """
    x, y, w, h = roi
    crop = np.asarray(gray[y : y + h, x : x + w], dtype=np.float32)
    if crop.size == 0:
        raise ValueError("roi is outside image bounds")

    gx = np.diff(crop, axis=1)
    gy = np.diff(crop, axis=0)
    score_x = float(np.mean(np.abs(gx))) if gx.size else 0.0
    score_y = float(np.mean(np.abs(gy))) if gy.size else 0.0
    if score_x >= score_y and gx.size:
        esf = np.mean(crop, axis=0)
        direction = "vertical_edge"
    elif gy.size:
        esf = np.mean(crop, axis=1)
        direction = "horizontal_edge"
    else:
        return {"mtf50_proxy_cyc_per_px": 0.0, "edge_contrast": 0.0, "edge_direction": "none"}

    lsf = np.abs(np.diff(esf))
    edge_contrast = float(np.max(esf) - np.min(esf))
    if lsf.size < 4 or edge_contrast <= 1e-6 or float(np.max(lsf)) <= 1e-6:
        return {
            "mtf50_proxy_cyc_per_px": 0.0,
            "edge_contrast": edge_contrast,
            "edge_direction": direction,
        }

    windowed = lsf * np.hanning(lsf.size)
    spectrum = np.abs(np.fft.rfft(windowed))
    if spectrum.size <= 1 or float(spectrum[0]) <= 1e-9:
        mtf50 = 0.0
    else:
        mtf = spectrum / spectrum[0]
        freqs = np.fft.rfftfreq(windowed.size, d=1.0)
        below = np.where(mtf <= 0.5)[0]
        mtf50 = float(freqs[below[0]]) if below.size else float(freqs[-1])

    return {
        "mtf50_proxy_cyc_per_px": mtf50,
        "edge_contrast": edge_contrast,
        "edge_direction": direction,
    }
