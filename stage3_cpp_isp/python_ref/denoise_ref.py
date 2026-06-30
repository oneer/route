"""Python 降噪参考实现：用于验证 C++ box/gaussian/bilateral/LUT/NLM 行为是否一致。"""

from __future__ import annotations

import numpy as np

from noise_model_ref import gaussian_kernel_1d


def bilateral_filter(
    image: np.ndarray,
    radius: int,
    sigma_spatial: float,
    sigma_range: float,
) -> np.ndarray:
    image = image.astype(np.float32)
    padded = np.pad(image, radius, mode="edge")
    out = np.zeros_like(image, dtype=np.float32)

    spatial = np.zeros((2 * radius + 1, 2 * radius + 1), dtype=np.float32)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            spatial[dy + radius, dx + radius] = np.exp(
                -0.5 * (dx * dx + dy * dy) / (sigma_spatial * sigma_spatial)
            )

    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            patch = padded[y : y + 2 * radius + 1, x : x + 2 * radius + 1]
            diff = patch - image[y, x]
            range_weight = np.exp(-0.5 * (diff * diff) / (sigma_range * sigma_range))
            weight = spatial * range_weight
            out[y, x] = np.sum(weight * patch) / np.sum(weight)
    return out


def bilateral_filter_range_lut(
    image: np.ndarray,
    radius: int,
    sigma_spatial: float,
    sigma_range: float,
    bins: int = 512,
) -> np.ndarray:
    image = image.astype(np.float32)
    lut_x = np.linspace(0.0, 1.0, bins, dtype=np.float32)
    lut = np.exp(-0.5 * (lut_x * lut_x) / (sigma_range * sigma_range)).astype(np.float32)

    padded = np.pad(image, radius, mode="edge")
    out = np.zeros_like(image, dtype=np.float32)
    spatial = np.zeros((2 * radius + 1, 2 * radius + 1), dtype=np.float32)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            spatial[dy + radius, dx + radius] = np.exp(
                -0.5 * (dx * dx + dy * dy) / (sigma_spatial * sigma_spatial)
            )

    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            patch = padded[y : y + 2 * radius + 1, x : x + 2 * radius + 1]
            pos = np.clip(np.abs(patch - image[y, x]), 0.0, 1.0) * (bins - 1)
            idx0 = np.floor(pos).astype(np.int32)
            idx1 = np.clip(idx0 + 1, 0, bins - 1)
            t = pos - idx0
            range_weight = lut[idx0] * (1.0 - t) + lut[idx1] * t
            weight = spatial * range_weight
            out[y, x] = np.sum(weight * patch) / np.sum(weight)
    return out


def nlm_reference(
    image: np.ndarray,
    patch_radius: int,
    search_radius: int,
    h: float,
) -> np.ndarray:
    image = image.astype(np.float32)
    pad = patch_radius + search_radius
    padded = np.pad(image, pad, mode="edge")
    out = np.zeros_like(image, dtype=np.float32)

    patch_size = 2 * patch_radius + 1
    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            cy = y + pad
            cx = x + pad
            center_patch = padded[
                cy - patch_radius : cy + patch_radius + 1,
                cx - patch_radius : cx + patch_radius + 1,
            ]
            weighted_sum = 0.0
            weight_sum = 0.0
            for dy in range(-search_radius, search_radius + 1):
                for dx in range(-search_radius, search_radius + 1):
                    ny = cy + dy
                    nx = cx + dx
                    patch = padded[
                        ny - patch_radius : ny + patch_radius + 1,
                        nx - patch_radius : nx + patch_radius + 1,
                    ]
                    dist2 = np.mean((patch - center_patch) ** 2)
                    weight = np.exp(-dist2 / (h * h))
                    weighted_sum += weight * padded[ny, nx]
                    weight_sum += weight
            out[y, x] = weighted_sum / weight_sum
    return out
