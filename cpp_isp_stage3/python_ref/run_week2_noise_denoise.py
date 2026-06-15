from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from noise_model_ref import (
    add_gaussian_noise,
    add_poisson_gaussian_noise,
    box_filter,
    edge_gradient_mean,
    gaussian_filter,
    psnr,
)


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week2"
REPORT_DIR = ROOT / "reports"


def make_clean_scene(size: int = 192) -> np.ndarray:
    y, x = np.indices((size, size), dtype=np.float32)
    gradient = x / (size - 1)
    scene = 0.08 + 0.72 * gradient
    scene[size // 5 : size // 2, size // 6 : size // 2] *= 0.25
    scene[size // 4 : 3 * size // 4, 3 * size // 5 : 4 * size // 5] = 0.95
    edge = ((x - size * 0.55) ** 2 + (y - size * 0.52) ** 2) < (size * 0.12) ** 2
    scene[edge] = 0.55
    return np.clip(scene, 0.0, 1.0).astype(np.float32)


def save_grid(images: list[tuple[str, np.ndarray]], path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    for ax, (title, image) in zip(axes.ravel(), images):
        ax.imshow(np.clip(image, 0.0, 1.0), cmap="gray", vmin=0, vmax=1)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    for ax in axes.ravel()[len(images):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def save_noise_curve(path: Path) -> None:
    rng = np.random.default_rng(42)
    levels = np.linspace(0.02, 0.95, 16, dtype=np.float32)
    stds = []
    for level in levels:
        patch = np.full((256, 256), level, dtype=np.float32)
        noisy = add_poisson_gaussian_noise(patch, shot_scale=280.0, read_sigma=0.006, rng=rng)
        stds.append(float(np.std(noisy - patch)))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(levels, stds, marker="o")
    ax.set_xlabel("linear signal level")
    ax.set_ylabel("noise std")
    ax.set_title("Poisson-Gaussian noise: variance grows with signal")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260615)

    clean = make_clean_scene()
    noisy_gaussian = add_gaussian_noise(clean, sigma=0.035, rng=rng)
    noisy_pg = add_poisson_gaussian_noise(clean, shot_scale=300.0, read_sigma=0.008, rng=rng)
    box = box_filter(noisy_pg, radius=1)
    gauss = gaussian_filter(noisy_pg, radius=2, sigma=1.1)
    residual = np.abs(noisy_pg - clean) * 6.0

    save_grid(
        [
            ("clean linear input", clean),
            ("Gaussian noise", noisy_gaussian),
            ("Poisson-Gaussian noise", noisy_pg),
            ("box r=1", box),
            ("Gaussian r=2 sigma=1.1", gauss),
            ("residual x6", residual),
        ],
        FIGURE_DIR / "week2_noise_denoise_grid.png",
    )
    save_noise_curve(FIGURE_DIR / "week2_noise_std_curve.png")

    rows = []
    for name, image in [
        ("noisy_pg", noisy_pg),
        ("box_r1", box),
        ("gaussian_r2_sigma1.1", gauss),
    ]:
        rows.append(
            {
                "method": name,
                "psnr": psnr(clean, image),
                "residual_std": float(np.std(image - clean)),
                "edge_gradient_mean": edge_gradient_mean(image),
            }
        )

    csv_path = FIGURE_DIR / "week2_basic_denoise_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote figures and metrics to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
