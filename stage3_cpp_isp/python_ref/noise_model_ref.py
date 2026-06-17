from __future__ import annotations

import numpy as np


def add_gaussian_noise(image: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    noisy = image.astype(np.float32) + rng.normal(0.0, sigma, size=image.shape).astype(np.float32)
    return np.clip(noisy, 0.0, 1.0)


def add_poisson_gaussian_noise(
    image: np.ndarray,
    shot_scale: float,
    read_sigma: float,
    rng: np.random.Generator,
) -> np.ndarray:
    image = np.clip(image.astype(np.float32), 0.0, 1.0)
    photons = np.maximum(image * shot_scale, 0.0)
    shot = rng.poisson(photons).astype(np.float32) / shot_scale
    read = rng.normal(0.0, read_sigma, size=image.shape).astype(np.float32)
    return np.clip(shot + read, 0.0, 1.0)


def box_filter(image: np.ndarray, radius: int) -> np.ndarray:
    image = image.astype(np.float32)
    padded = np.pad(image, radius, mode="edge")
    out = np.zeros_like(image, dtype=np.float32)
    area = float((2 * radius + 1) ** 2)
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            out += padded[dy : dy + image.shape[0], dx : dx + image.shape[1]]
    return out / area


def gaussian_kernel_1d(radius: int, sigma: float) -> np.ndarray:
    x = np.arange(-radius, radius + 1, dtype=np.float32)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    return (kernel / np.sum(kernel)).astype(np.float32)


def gaussian_filter(image: np.ndarray, radius: int, sigma: float) -> np.ndarray:
    image = image.astype(np.float32)
    kernel = gaussian_kernel_1d(radius, sigma)
    padded_x = np.pad(image, ((0, 0), (radius, radius)), mode="edge")
    temp = np.zeros_like(image, dtype=np.float32)
    for i, weight in enumerate(kernel):
        temp += weight * padded_x[:, i : i + image.shape[1]]

    padded_y = np.pad(temp, ((radius, radius), (0, 0)), mode="edge")
    out = np.zeros_like(image, dtype=np.float32)
    for i, weight in enumerate(kernel):
        out += weight * padded_y[i : i + image.shape[0], :]
    return out.astype(np.float32)


def psnr(reference: np.ndarray, output: np.ndarray, peak: float = 1.0) -> float:
    mse = np.mean((reference.astype(np.float32) - output.astype(np.float32)) ** 2)
    if mse == 0:
        return float("inf")
    return float(20.0 * np.log10(peak / np.sqrt(mse)))


def edge_gradient_mean(image: np.ndarray) -> float:
    image = image.astype(np.float32)
    gx = np.diff(image, axis=1)
    gy = np.diff(image, axis=0)
    return float(0.5 * (np.mean(np.abs(gx)) + np.mean(np.abs(gy))))
