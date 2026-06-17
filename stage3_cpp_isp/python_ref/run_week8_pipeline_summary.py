from __future__ import annotations

import csv
import subprocess
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from make_test_vectors import write_cpf32
from run_week5_tone_mapping import make_hdr_like_scene
from run_week7_ltm_hdr_toy import make_aligned_exposures, read_cpf32
from tone_mapping_ref import apply_gamma, luminance, percentile_exposure


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week8"
ALIGN_DIR = ROOT / "data" / "week8_pipeline"
BUILD_DIR = ROOT / "build"


def save_png(path: Path, image: np.ndarray) -> None:
    image = np.clip(image, 0.0, 1.0)
    Image.fromarray((image * 255.0 + 0.5).astype(np.uint8)).save(path)


def run_command(args: list[str]) -> float:
    begin = time.perf_counter()
    subprocess.run(args, check=True)
    return (time.perf_counter() - begin) * 1000.0


def image_metrics(name: str, image: np.ndarray) -> dict[str, float | str]:
    y = luminance(image)
    return {
        "case": name,
        "mean_luma": float(np.mean(y)),
        "p95_luma": float(np.percentile(y, 95)),
        "clip_fraction": float(np.mean(image >= 0.999)),
        "min_value": float(np.min(image)),
        "max_value": float(np.max(image)),
    }


def make_noisy_scene(scene: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(20260617)
    noise = rng.normal(0.0, 0.015, size=scene.shape).astype(np.float32)
    return np.clip(scene + noise, 0.0, None).astype(np.float32)


def plot_outputs(outputs: list[tuple[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(2, len(outputs), figsize=(4.0 * len(outputs), 6.0))
    reference_luma = luminance(outputs[0][1])
    for col, (title, image) in enumerate(outputs):
        axes[0, col].imshow(np.clip(image, 0.0, 1.0))
        axes[0, col].set_title(title, fontsize=9)
        axes[0, col].axis("off")
        delta = np.abs(luminance(image) - reference_luma)
        axes[1, col].imshow(np.clip(delta * 5.0, 0.0, 1.0), cmap="magma")
        axes[1, col].set_title("delta vs global x5", fontsize=9)
        axes[1, col].axis("off")
        save_png(FIGURE_DIR / f"week8_pipeline_{title.replace(' ', '_')}.png", image)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week8_pipeline_comparison.png", dpi=170)
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    ALIGN_DIR.mkdir(parents=True, exist_ok=True)

    scene = make_hdr_like_scene(width=160, height=96)
    noisy_scene = make_noisy_scene(scene)
    exposure = percentile_exposure(scene, 99.0, 1.0)
    short_image, long_image = make_aligned_exposures(scene, 0.18, 0.72)

    input_path = ALIGN_DIR / "week8_scene_noisy.cpf32"
    short_path = ALIGN_DIR / "week8_short.cpf32"
    long_path = ALIGN_DIR / "week8_long.cpf32"
    write_cpf32(input_path, noisy_scene)
    write_cpf32(short_path, short_image)
    write_cpf32(long_path, long_image)

    cases = [
        (
            "global",
            [
                str(BUILD_DIR / "run_pipeline.exe"),
                "single",
                str(input_path),
                str(ALIGN_DIR / "week8_global.cpf32"),
                "gaussian",
                "global",
                "reinhard",
                f"{exposure:.9f}",
                "2.2",
            ],
            ALIGN_DIR / "week8_global.cpf32",
        ),
        (
            "lut",
            [
                str(BUILD_DIR / "run_pipeline.exe"),
                "single",
                str(input_path),
                str(ALIGN_DIR / "week8_lut.cpf32"),
                "gaussian",
                "lut",
                "reinhard",
                f"{exposure:.9f}",
                "2.2",
            ],
            ALIGN_DIR / "week8_lut.cpf32",
        ),
        (
            "local",
            [
                str(BUILD_DIR / "run_pipeline.exe"),
                "single",
                str(input_path),
                str(ALIGN_DIR / "week8_local.cpf32"),
                "gaussian",
                "local",
                "reinhard",
                f"{exposure:.9f}",
                "2.2",
            ],
            ALIGN_DIR / "week8_local.cpf32",
        ),
        (
            "hdr local",
            [
                str(BUILD_DIR / "run_pipeline.exe"),
                "hdr",
                str(short_path),
                str(long_path),
                str(ALIGN_DIR / "week8_hdr_local.cpf32"),
                "none",
                "local",
                "reinhard",
                f"{exposure:.9f}",
                "2.2",
                "0.18",
                "0.72",
            ],
            ALIGN_DIR / "week8_hdr_local.cpf32",
        ),
    ]

    outputs: list[tuple[str, np.ndarray]] = []
    rows: list[dict[str, float | str]] = []
    for name, args, output_path in cases:
        elapsed_ms = run_command(args)
        image = read_cpf32(output_path)
        outputs.append((name, image))
        row = image_metrics(name, image)
        row["pipeline_ms"] = elapsed_ms
        rows.append(row)

    plot_outputs(outputs)
    with (FIGURE_DIR / "week8_pipeline_metrics.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote Week8 pipeline outputs to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
