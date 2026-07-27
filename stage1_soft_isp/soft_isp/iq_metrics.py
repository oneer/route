"""可行 RAW/IQ 诊断指标：裁剪比例、ROI SNR、近似动态范围和边缘 MTF50 代理指标。

中文注释说明：本文件的注释侧重解释数据流、算法意图和实验用途；除注释/docstring 外不改变运行逻辑。
"""

from __future__ import annotations

import math

import numpy as np


def _finite_array(value: np.ndarray, name: str) -> np.ndarray:
    data = np.asarray(value, dtype=np.float32)
    if data.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(data)):
        raise ValueError(f"{name} must contain only finite values")
    return data


def _validate_levels(black_level: float, white_level: float) -> tuple[float, float]:
    black = float(black_level)
    white = float(white_level)
    if not math.isfinite(black) or not math.isfinite(white):
        raise ValueError("black_level and white_level must be finite")
    if white <= black:
        raise ValueError("white_level must be greater than black_level")
    return black, white


def exposure_statistics(
    raw: np.ndarray,
    black_level: float,
    white_level: float,
    margin: float = 16.0,
) -> dict[str, float]:
    """Return code-value and normalized exposure statistics."""
    data = _finite_array(raw, "raw")
    black, white = _validate_levels(black_level, white_level)
    usable_range = white - black
    normalized = np.clip((data - black) / usable_range, 0.0, 1.0)
    clipping = clipping_fractions(data, black, white, margin)
    return {
        "mean_code_value": float(np.mean(data)),
        "p01_code_value": float(np.percentile(data, 1.0)),
        "p50_code_value": float(np.percentile(data, 50.0)),
        "p99_code_value": float(np.percentile(data, 99.0)),
        "mean_normalized": float(np.mean(normalized)),
        "p01_normalized": float(np.percentile(normalized, 1.0)),
        "p50_normalized": float(np.percentile(normalized, 50.0)),
        "p99_normalized": float(np.percentile(normalized, 99.0)),
        **clipping,
    }


def strongest_edge_roi(
    gray: np.ndarray,
    roi_size: int,
    stride: int | None = None,
) -> tuple[int, int, int, int]:
    """Select the fixed-size tile with the largest mean gradient magnitude."""
    data = _finite_array(gray, "gray")
    if data.ndim != 2:
        raise ValueError("gray must be a 2D image")
    if roi_size < 4 or roi_size > min(data.shape):
        raise ValueError("roi_size must fit the image and be at least 4")
    step = roi_size if stride is None else stride
    if step <= 0:
        raise ValueError("stride must be positive")
    gx = np.zeros_like(data)
    gy = np.zeros_like(data)
    gx[:, 1:] = np.abs(data[:, 1:] - data[:, :-1])
    gy[1:, :] = np.abs(data[1:, :] - data[:-1, :])
    gradient = gx + gy
    best: tuple[float, int, int] | None = None
    height, width = data.shape
    xs = list(range(0, width - roi_size + 1, step))
    ys = list(range(0, height - roi_size + 1, step))
    if xs[-1] != width - roi_size:
        xs.append(width - roi_size)
    if ys[-1] != height - roi_size:
        ys.append(height - roi_size)
    for y in ys:
        for x in xs:
            score = float(np.mean(gradient[y : y + roi_size, x : x + roi_size]))
            if best is None or score > best[0]:
                best = (score, x, y)
    assert best is not None
    return (best[1], best[2], roi_size, roi_size)


# 中文注释：估计 RAW 中接近黑电平和白电平的像素比例。
def clipping_fractions(raw: np.ndarray, black_level: float, white_level: float, margin: float = 16.0) -> dict[str, float]:
    """Return near-black and near-white fractions for a RAW image."""
    data = _finite_array(raw, "raw")
    black, white = _validate_levels(black_level, white_level)
    margin = float(margin)
    if not math.isfinite(margin) or margin < 0.0:
        raise ValueError("margin must be a finite non-negative value")
    if 2.0 * margin > white - black:
        raise ValueError("margin is too large for the usable code-value range")
    total = float(data.size)
    return {
        "near_black_fraction": float(np.count_nonzero(data <= black + margin) / total),
        "near_white_fraction": float(np.count_nonzero(data >= white - margin) / total),
    }


# 中文注释：在指定 ROI 内估计信噪比，单位为 dB。
def roi_snr_db(roi: np.ndarray, black_level: float) -> dict[str, float]:
    """Estimate ROI SNR from mean signal above black and local standard deviation.

    This is useful for relative diagnosis across ROIs or parameter variants.
    It is not a sensor-lab SNR result because a natural-image ROI mixes texture
    with noise unless it comes from a true flat-field frame.
    """
    data = _finite_array(roi, "roi")
    black = float(black_level)
    if not math.isfinite(black):
        raise ValueError("black_level must be finite")
    signal = max(float(np.mean(data) - black), 0.0)
    noise = max(float(np.std(data)), 1e-6)
    return {
        "signal_mean": signal,
        "noise_std": noise,
        "snr_db": float(20.0 * math.log10(max(signal, 1e-6) / noise)),
    }


# 中文注释：用黑白电平和噪声估计近似动态范围。
def approximate_dynamic_range_db(white_level: float, black_level: float, noise_floor: float) -> float:
    """Estimate dynamic range from usable signal and a chosen noise floor."""
    black, white = _validate_levels(black_level, white_level)
    floor = float(noise_floor)
    if not math.isfinite(floor) or floor <= 0.0:
        raise ValueError("noise_floor must be a finite positive value")
    usable_signal = white - black
    return float(20.0 * math.log10(usable_signal / floor))


# 中文注释：用边缘梯度频谱估计 MTF50 代理值，只用于相对比较。
def edge_mtf50_proxy(gray: np.ndarray, roi: tuple[int, int, int, int]) -> dict[str, float]:
    """Return a lightweight edge sharpness proxy for a local gray ROI.

    The proxy finds the dominant horizontal/vertical gradient direction and
    reports the spatial frequency where the normalized derivative spectrum
    drops below 50%. It is meant to rank comparable crops, not replace a
    slanted-edge chart measurement.
    """
    data = _finite_array(gray, "gray")
    if data.ndim != 2:
        raise ValueError("gray must be a 2D image")
    if len(roi) != 4 or not all(isinstance(value, (int, np.integer)) for value in roi):
        raise ValueError("roi must contain four integer values")
    x, y, w, h = (int(value) for value in roi)
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > data.shape[1] or y + h > data.shape[0]:
        raise ValueError("roi must be fully inside the image")
    crop = data[y : y + h, x : x + w]

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
