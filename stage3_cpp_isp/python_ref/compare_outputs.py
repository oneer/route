from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read_cpf32(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        if f.readline().strip() != b"CPF32":
            raise ValueError(f"invalid CPF32 file: {path}")
        width, height, channels = map(int, f.readline().decode("ascii").split())
        data = np.frombuffer(f.read(), dtype="<f4").copy()
    return data.reshape(height, width, channels)


def compute_metrics(reference: np.ndarray, output: np.ndarray, threshold: float) -> dict[str, float | int | str]:
    if reference.shape != output.shape:
        raise ValueError(f"shape mismatch: {reference.shape} vs {output.shape}")
    diff = output.astype(np.float64) - reference.astype(np.float64)
    abs_diff = np.abs(diff)
    mse = float(np.mean(diff * diff))
    psnr = math.inf if mse == 0.0 else 20.0 * math.log10(1.0 / math.sqrt(mse))
    return {
        "shape": "x".join(str(v) for v in reference.shape),
        "threshold": threshold,
        "max_abs_error": float(np.max(abs_diff)),
        "mean_abs_error": float(np.mean(abs_diff)),
        "rmse": math.sqrt(mse),
        "psnr_db": psnr,
        "failed_values": int(np.sum(abs_diff > threshold)),
        "total_values": int(abs_diff.size),
    }


def write_csv(path: Path, metrics: dict[str, float | int | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)


def write_error_map(path: Path, reference: np.ndarray, output: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    abs_diff = np.abs(output.astype(np.float32) - reference.astype(np.float32))
    heat = np.max(abs_diff, axis=2) if abs_diff.ndim == 3 else abs_diff
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(heat, cmap="magma")
    ax.set_title("max-channel absolute error")
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two CPF32 tensors and optionally write an error map")
    parser.add_argument("reference")
    parser.add_argument("output")
    parser.add_argument("--threshold", type=float, default=1e-5)
    parser.add_argument("--csv", default="")
    parser.add_argument("--error-map", default="")
    args = parser.parse_args()

    reference = read_cpf32(Path(args.reference))
    output = read_cpf32(Path(args.output))
    metrics = compute_metrics(reference, output, args.threshold)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    if args.csv:
        write_csv(Path(args.csv), metrics)
    if args.error_map:
        write_error_map(Path(args.error_map), reference, output)


if __name__ == "__main__":
    main()
