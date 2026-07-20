"""Camera-scene restoration metrics and deterministic failure classification."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


NUMERIC_FIELDS = (
    "input_psnr", "output_psnr", "psnr_gain", "output_ssim",
    "noise_rmse_reduction", "texture_retention", "edge_loss", "color_bias",
)


def _as_rgb(image: np.ndarray, name: str) -> np.ndarray:
    data = np.asarray(image, dtype=np.float32)
    if data.ndim != 3 or data.shape[2] != 3:
        raise ValueError(f"{name} must have shape HxWx3")
    if not np.all(np.isfinite(data)):
        raise ValueError(f"{name} contains NaN or Inf")
    return np.clip(data, 0.0, 1.0)


def _gradient_map(image: np.ndarray) -> np.ndarray:
    luminance = 0.2126 * image[..., 0] + 0.7152 * image[..., 1] + 0.0722 * image[..., 2]
    gx = np.zeros_like(luminance)
    gy = np.zeros_like(luminance)
    gx[:, 1:] = luminance[:, 1:] - luminance[:, :-1]
    gy[1:, :] = luminance[1:, :] - luminance[:-1, :]
    return np.hypot(gx, gy)


def _texture_metrics(output: np.ndarray, reference: np.ndarray) -> tuple[float, float]:
    """Measure gradients only where the reference contains real structure.

    Whole-image gradient energy is dominated by noise in flat regions and can
    incorrectly report several hundred percent "texture retention". The top
    reference-gradient quartile is a deterministic structure mask.
    """
    reference_gradient = _gradient_map(reference)
    output_gradient = _gradient_map(output)
    threshold = max(float(np.percentile(reference_gradient, 75.0)), 1.0e-5)
    mask = reference_gradient >= threshold
    if not np.any(mask):
        return 1.0, 0.0
    reference_energy = max(float(np.mean(reference_gradient[mask])), 1.0e-8)
    output_energy = float(np.mean(output_gradient[mask]))
    retention = output_energy / reference_energy
    return retention, max(1.0 - retention, 0.0)


def evaluate_scene_candidate(
    noisy: np.ndarray,
    output: np.ndarray,
    reference: np.ndarray,
) -> dict[str, float | str]:
    """Compare one restoration output against its input and paired reference."""
    noisy_rgb = _as_rgb(noisy, "noisy")
    output_rgb = _as_rgb(output, "output")
    reference_rgb = _as_rgb(reference, "reference")
    if noisy_rgb.shape != output_rgb.shape or output_rgb.shape != reference_rgb.shape:
        raise ValueError("noisy, output, and reference must have identical shapes")
    input_psnr = float(peak_signal_noise_ratio(reference_rgb, noisy_rgb, data_range=1.0))
    output_psnr = float(peak_signal_noise_ratio(reference_rgb, output_rgb, data_range=1.0))
    output_ssim = float(structural_similarity(reference_rgb, output_rgb, channel_axis=2, data_range=1.0))
    input_rmse = float(np.sqrt(np.mean((noisy_rgb - reference_rgb) ** 2)))
    output_rmse = float(np.sqrt(np.mean((output_rgb - reference_rgb) ** 2)))
    texture_retention, edge_loss = _texture_metrics(output_rgb, reference_rgb)
    color_bias = float(np.mean(np.abs(np.mean(output_rgb - reference_rgb, axis=(0, 1)))))
    if output_psnr < input_psnr - 0.05:
        failure_type = "quality_regression"
    elif color_bias > 0.02:
        failure_type = "color_shift"
    elif texture_retention < 0.80:
        failure_type = "over_smoothing"
    elif edge_loss > 0.15:
        failure_type = "edge_loss"
    elif texture_retention > 1.25:
        failure_type = "excess_high_frequency"
    else:
        failure_type = "acceptable"
    return {
        "input_psnr": input_psnr,
        "output_psnr": output_psnr,
        "psnr_gain": output_psnr - input_psnr,
        "output_ssim": output_ssim,
        "noise_rmse_reduction": input_rmse - output_rmse,
        "texture_retention": texture_retention,
        "edge_loss": edge_loss,
        "color_bias": color_bias,
        "failure_type": failure_type,
    }


def aggregate_by_scene_method(rows: list[dict[str, str | float]]) -> list[dict[str, str | float | int]]:
    """Aggregate per-sample metrics by frozen scene group and method."""
    groups: dict[tuple[str, str], list[dict[str, str | float]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["scene_group"]), str(row["method"]))].append(row)
    result: list[dict[str, str | float | int]] = []
    for (scene_group, method), items in sorted(groups.items()):
        failures = sum(item["failure_type"] != "acceptable" for item in items)
        result.append(
            {
                "scene_group": scene_group,
                "method": method,
                "sample_count": len(items),
                **{
                    f"mean_{field}": float(np.mean([float(item[field]) for item in items]))
                    for field in NUMERIC_FIELDS
                },
                "failure_count": failures,
                "failure_rate": failures / len(items),
            }
        )
    return result
