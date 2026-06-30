"""Week 3 实验脚本：比较 bilateral、range LUT bilateral 和 NLM 参考算法。"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from denoise_ref import bilateral_filter, bilateral_filter_range_lut, nlm_reference
from noise_model_ref import add_poisson_gaussian_noise, edge_gradient_mean, gaussian_filter, psnr


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week3"


def make_edge_texture_scene(size: int = 128) -> np.ndarray:
    y, x = np.indices((size, size), dtype=np.float32)
    scene = np.where(x < size * 0.52, 0.18, 0.72).astype(np.float32)
    texture = 0.035 * np.sin(x * 0.45) * np.sin(y * 0.33)
    scene += texture.astype(np.float32)
    scene[size // 5 : size // 2, size // 5 : size // 2] = 0.42
    return np.clip(scene, 0.0, 1.0)


def save_grid(images: list[tuple[str, np.ndarray]], path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    for ax, (title, image) in zip(axes.ravel(), images):
        ax.imshow(np.clip(image, 0.0, 1.0), cmap="gray", vmin=0, vmax=1)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260616)

    clean = make_edge_texture_scene(128)
    noisy = add_poisson_gaussian_noise(clean, shot_scale=260.0, read_sigma=0.01, rng=rng)
    gauss = gaussian_filter(noisy, radius=2, sigma=1.1)
    bilateral_weak = bilateral_filter(noisy, radius=2, sigma_spatial=1.5, sigma_range=0.06)
    bilateral_strong = bilateral_filter(noisy, radius=3, sigma_spatial=2.2, sigma_range=0.12)
    bilateral_lut = bilateral_filter_range_lut(noisy, radius=2, sigma_spatial=1.5, sigma_range=0.06, bins=512)

    small = noisy[:48, :48]
    t0 = time.perf_counter()
    nlm_small = nlm_reference(small, patch_radius=1, search_radius=3, h=0.08)
    nlm_ms = (time.perf_counter() - t0) * 1000.0

    save_grid(
        [
            ("clean", clean),
            ("noisy", noisy),
            ("Gaussian", gauss),
            ("bilateral weak", bilateral_weak),
            ("bilateral strong", bilateral_strong),
            ("abs residual x6", np.abs(bilateral_weak - clean) * 6.0),
        ],
        FIGURE_DIR / "week3_bilateral_grid.png",
    )

    save_grid(
        [
            ("NLM input crop", small),
            ("NLM output crop", nlm_small),
            ("NLM residual x6", np.abs(nlm_small - clean[:48, :48]) * 6.0),
        ],
        FIGURE_DIR / "week3_nlm_small_crop.png",
    )

    rows = []
    for name, image in [
        ("noisy", noisy),
        ("gaussian_r2_sigma1.1", gauss),
        ("bilateral_r2_ss1.5_sr0.06", bilateral_weak),
        ("bilateral_r3_ss2.2_sr0.12", bilateral_strong),
        ("bilateral_lut512", bilateral_lut),
    ]:
        rows.append(
            {
                "method": name,
                "psnr": psnr(clean, image),
                "residual_std": float(np.std(image - clean)),
                "edge_gradient_mean": edge_gradient_mean(image),
                "max_abs_vs_direct": float(np.max(np.abs(image - bilateral_weak)))
                if name == "bilateral_lut512"
                else "",
            }
        )

    rows.append(
        {
            "method": "nlm_48x48_patch1_search3",
            "psnr": psnr(clean[:48, :48], nlm_small),
            "residual_std": float(np.std(nlm_small - clean[:48, :48])),
            "edge_gradient_mean": edge_gradient_mean(nlm_small),
            "max_abs_vs_direct": f"runtime_ms={nlm_ms:.2f}",
        }
    )

    csv_path = FIGURE_DIR / "week3_bilateral_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote Week3 figures and metrics to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
