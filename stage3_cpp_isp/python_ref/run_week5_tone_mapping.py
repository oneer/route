from __future__ import annotations

import csv
import subprocess
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from make_test_vectors import write_cpf32
from tone_mapping_ref import (
    apply_gamma,
    filmic_curve,
    luminance,
    percentile_exposure,
    reinhard_curve,
    scurve,
    tone_map_luminance,
    tone_map_rgb,
)


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week5"
ALIGN_DIR = ROOT / "data" / "week5_alignment"
BUILD_DIR = ROOT / "build"


def save_png(path: Path, image: np.ndarray) -> None:
    image = np.clip(image, 0.0, 1.0)
    Image.fromarray((image * 255.0 + 0.5).astype(np.uint8)).save(path)


def make_hdr_like_scene(width: int = 320, height: int = 192) -> np.ndarray:
    y, x = np.indices((height, width), dtype=np.float32)
    gx = x / max(width - 1, 1)
    gy = y / max(height - 1, 1)
    base = np.zeros((height, width, 3), dtype=np.float32)
    base[..., 0] = 0.08 + 2.8 * gx
    base[..., 1] = 0.06 + 2.2 * gy
    base[..., 2] = 0.10 + 1.4 * (1.0 - gx)

    sun = np.exp(-(((x - width * 0.76) ** 2 + (y - height * 0.22) ** 2) / (2.0 * (width * 0.055) ** 2)))
    window = ((x > width * 0.62) & (x < width * 0.90) & (y > height * 0.08) & (y < height * 0.36)).astype(np.float32)
    shadow = ((x > width * 0.08) & (x < width * 0.38) & (y > height * 0.55) & (y < height * 0.88)).astype(np.float32)
    texture = 0.08 * np.sin(x * 0.18) * np.cos(y * 0.23)

    base += sun[..., None] * np.array([8.0, 6.2, 3.6], dtype=np.float32)
    base += window[..., None] * np.array([3.0, 2.6, 1.8], dtype=np.float32)
    base -= shadow[..., None] * np.array([0.05, 0.04, 0.03], dtype=np.float32)
    base += texture[..., None]
    return np.clip(base, 0.0, None).astype(np.float32)


def plot_curves() -> None:
    x = np.linspace(0.0, 8.0, 512, dtype=np.float32)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, reinhard_curve(x), label="Reinhard")
    ax.plot(x, filmic_curve(x), label="Filmic")
    ax.plot(x, scurve(np.clip(x, 0.0, 1.0)), label="S-curve on normalized input")
    ax.set_xlabel("linear input after exposure")
    ax.set_ylabel("tone mapped output")
    ax.set_title("Global tone curves")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week5_tone_curves.png", dpi=170)
    plt.close(fig)


def plot_comparison(scene: np.ndarray, exposure: float) -> list[dict[str, float | str]]:
    outputs = [
        ("linear clipped", np.clip(scene * exposure, 0.0, 1.0)),
        ("reinhard rgb", tone_map_rgb(scene, "reinhard", exposure)),
        ("reinhard luma", tone_map_luminance(scene, "reinhard", exposure)),
        ("filmic luma", tone_map_luminance(scene, "filmic", exposure)),
        ("s-curve luma", tone_map_luminance(scene, "scurve", exposure)),
    ]

    fig, axes = plt.subplots(2, len(outputs), figsize=(15, 6))
    for col, (title, image) in enumerate(outputs):
        display = apply_gamma(image, 2.2)
        axes[0, col].imshow(display)
        axes[0, col].set_title(title, fontsize=9)
        axes[0, col].axis("off")
        err = np.abs(luminance(image) - luminance(scene * exposure))
        axes[1, col].imshow(np.clip(err * 2.5, 0.0, 1.0), cmap="magma")
        axes[1, col].set_title("luma compression map", fontsize=9)
        axes[1, col].axis("off")
        save_png(FIGURE_DIR / f"week5_{title.replace(' ', '_')}.png", display)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week5_tone_mapping_comparison.png", dpi=170)
    plt.close(fig)

    rows: list[dict[str, float | str]] = []
    h, w = scene.shape[:2]
    rois = {
        "shadow": np.s_[int(h * 0.58) : int(h * 0.86), int(w * 0.10) : int(w * 0.36)],
        "midtone": np.s_[int(h * 0.40) : int(h * 0.62), int(w * 0.40) : int(w * 0.58)],
        "highlight": np.s_[int(h * 0.10) : int(h * 0.34), int(w * 0.66) : int(w * 0.88)],
    }
    for name, image in outputs:
        y = luminance(image)
        row: dict[str, float | str] = {
            "method": name,
            "mean_luma": float(np.mean(y)),
            "p95_luma": float(np.percentile(y, 95)),
            "clip_fraction": float(np.mean(image >= 0.999)),
        }
        for roi_name, roi in rois.items():
            row[f"{roi_name}_mean"] = float(np.mean(y[roi]))
            row[f"{roi_name}_std"] = float(np.std(y[roi]))
        rows.append(row)

    metrics_path = FIGURE_DIR / "week5_roi_metrics.csv"
    with metrics_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for name, image in outputs:
        ax.hist(luminance(image).ravel(), bins=80, range=(0.0, 1.0), histtype="step", label=name)
    ax.set_xlabel("output luminance")
    ax.set_ylabel("pixel count")
    ax.set_title("Tone mapped luminance histograms")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week5_luminance_histograms.png", dpi=170)
    plt.close(fig)
    return rows


def read_compare_output(text: str) -> dict[str, str]:
    row: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            row[key.strip()] = value.strip()
    return row


def run_alignment(scene: np.ndarray, exposure: float) -> None:
    ALIGN_DIR.mkdir(parents=True, exist_ok=True)
    input_path = ALIGN_DIR / "week5_tone_input.cpf32"
    write_cpf32(input_path, scene)

    rows: list[dict[str, str]] = []
    cases = [
        ("reinhard", "rgb", tone_map_rgb(scene, "reinhard", exposure)),
        ("reinhard", "luma", tone_map_luminance(scene, "reinhard", exposure)),
        ("filmic", "luma", tone_map_luminance(scene, "filmic", exposure)),
        ("scurve", "luma", tone_map_luminance(scene, "scurve", exposure)),
    ]
    for curve, mode, reference in cases:
        ref_path = ALIGN_DIR / f"week5_python_{curve}_{mode}.cpf32"
        out_path = ALIGN_DIR / f"week5_cpp_{curve}_{mode}.cpf32"
        write_cpf32(ref_path, reference)
        subprocess.run(
            [
                str(BUILD_DIR / "run_tone_mapping.exe"),
                str(input_path),
                str(out_path),
                curve,
                mode,
                f"{exposure:.9f}",
            ],
            check=True,
        )
        completed = subprocess.run(
            [str(BUILD_DIR / "compare_with_reference.exe"), str(ref_path), str(out_path), "2e-5"],
            check=True,
            text=True,
            capture_output=True,
        )
        row = {"curve": curve, "mode": mode}
        row.update(read_compare_output(completed.stdout))
        rows.append(row)

    with (FIGURE_DIR / "week5_python_cpp_alignment.csv").open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["curve", "mode", "max_abs_error", "mean_abs_error", "rmse", "psnr", "failed_values"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_python_benchmark(scene: np.ndarray, exposure: float) -> None:
    rows = []
    for curve, fn in [
        ("reinhard_rgb", lambda: tone_map_rgb(scene, "reinhard", exposure)),
        ("reinhard_luma", lambda: tone_map_luminance(scene, "reinhard", exposure)),
        ("filmic_luma", lambda: tone_map_luminance(scene, "filmic", exposure)),
        ("scurve_luma", lambda: tone_map_luminance(scene, "scurve", exposure)),
    ]:
        best = 1e9
        for _ in range(5):
            t0 = time.perf_counter()
            fn()
            best = min(best, (time.perf_counter() - t0) * 1000.0)
        rows.append({"python_method": curve, "width": scene.shape[1], "height": scene.shape[0], "ms": best})

    with (FIGURE_DIR / "week5_python_benchmark.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    ALIGN_DIR.mkdir(parents=True, exist_ok=True)
    scene = make_hdr_like_scene()
    exposure = percentile_exposure(scene, 99.0, 1.0)
    write_cpf32(ALIGN_DIR / "week5_tone_input.cpf32", scene)
    save_png(FIGURE_DIR / "week5_input_linear_preview_gamma.png", apply_gamma(np.clip(scene * exposure, 0, 1), 2.2))
    plot_curves()
    plot_comparison(scene, exposure)
    run_alignment(scene, exposure)
    run_python_benchmark(scene, exposure)
    print(f"wrote Week5 figures and metrics to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
