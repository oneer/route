"""Week 4 性能脚本：调用 C++ bilateral 工具/benchmark，整理速度和对齐数据。"""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from denoise_ref import bilateral_filter_range_lut
from make_test_vectors import write_cpf32


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week4"
ALIGN_DIR = ROOT / "data" / "week4_alignment"
BUILD_DIR = ROOT / "build"


def make_alignment_input(size: int = 64) -> np.ndarray:
    y, x = np.indices((size, size), dtype=np.float32)
    base = 0.55 * x / (size - 1) + 0.25 * y / (size - 1)
    edge = np.where(x > size * 0.52, 0.22, 0.0).astype(np.float32)
    texture = 0.035 * np.sin(x * 0.7) * np.cos(y * 0.37)
    return np.clip(base + edge + texture, 0.0, 1.0).astype(np.float32)


def read_csv(path: Path) -> list[dict[str, str]]:
    for encoding in ["utf-8-sig", "utf-16"]:
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"unable to decode {path}")


def run_alignment() -> None:
    ALIGN_DIR.mkdir(parents=True, exist_ok=True)
    image = make_alignment_input()
    reference = bilateral_filter_range_lut(
        image,
        radius=2,
        sigma_spatial=1.5,
        sigma_range=0.08,
        bins=512,
    )

    input_path = ALIGN_DIR / "week4_bilateral_input.cpf32"
    ref_path = ALIGN_DIR / "week4_bilateral_python_ref.cpf32"
    write_cpf32(input_path, image)
    write_cpf32(ref_path, reference)

    compare_rows: list[dict[str, str]] = []
    for mode in ["lut", "tile", "rows", "tiles"]:
        output_path = ALIGN_DIR / f"week4_bilateral_cpp_{mode}.cpf32"
        subprocess.run(
            [str(BUILD_DIR / "run_bilateral_lut.exe"), str(input_path), str(output_path), mode, "4"],
            check=True,
        )
        completed = subprocess.run(
            [
                str(BUILD_DIR / "compare_with_reference.exe"),
                str(ref_path),
                str(output_path),
                "1e-5",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        row: dict[str, str] = {"mode": mode}
        for line in completed.stdout.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                row[key.strip()] = value.strip()
        compare_rows.append(row)

    csv_path = FIGURE_DIR / "week4_python_cpp_alignment.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["mode", "max_abs_error", "mean_abs_error", "rmse", "psnr", "failed_values"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(compare_rows)


def plot_benchmarks() -> None:
    full_csv = ROOT / "reports" / "figures" / "week4_denoise_benchmark_full.csv"
    if not full_csv.exists():
        full_csv = FIGURE_DIR / "week4_denoise_benchmark_full.csv"
    rows = read_csv(full_csv)
    normalized_csv = FIGURE_DIR / "week4_denoise_benchmark_full.csv"
    with normalized_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    thread_rows = [
        row
        for row in rows
        if row["method"] in {"thread_rows", "thread_tiles"} and row["threads"] in {"1", "2", "4", "8"}
    ]
    sizes = ["256x256", "1920x1080", "3840x2160"]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for ax, size in zip(axes, sizes):
        w, h = size.split("x")
        for method, label in [("thread_rows", "row split"), ("thread_tiles", "tile split")]:
            selected = [row for row in thread_rows if row["width"] == w and row["height"] == h and row["method"] == method]
            selected.sort(key=lambda row: int(row["threads"]))
            ax.plot(
                [int(row["threads"]) for row in selected],
                [float(row["speedup"]) for row in selected],
                marker="o",
                label=label,
            )
        ax.plot([1, 2, 4, 8], [1, 2, 4, 8], linestyle="--", color="0.7", label="ideal" if size == sizes[0] else None)
        ax.set_title(size)
        ax.set_xlabel("threads")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("speedup vs single-thread LUT")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week4_thread_speedup.png", dpi=170)
    plt.close(fig)

    tile_rows = [row for row in rows if row["method"] == "tile_lut"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = []
    values = []
    for row in tile_rows:
        labels.append(f"{row['width']}x{row['height']}\n{row['tile_width']}x{row['tile_height']}")
        values.append(float(row["speedup"]))
    ax.bar(np.arange(len(values)), values, color="#4C78A8")
    ax.axhline(1.0, color="0.25", linewidth=1)
    ax.set_xticks(np.arange(len(values)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("speedup vs untiled LUT")
    ax.set_title("Tile-size sensitivity")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week4_tile_sensitivity.png", dpi=170)
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    run_alignment()
    plot_benchmarks()
    print(f"wrote Week4 alignment and figures to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
