from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image

from make_test_vectors import write_cpf32


ROOT = Path(__file__).resolve().parents[1]


def read_cpf32(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        if f.readline().strip() != b"CPF32":
            raise ValueError(f"invalid CPF32 file: {path}")
        width, height, channels = map(int, f.readline().decode("ascii").split())
        data = np.frombuffer(f.read(), dtype="<f4").copy()
    return data.reshape(height, width, channels)


def save_preview(path: Path, image: np.ndarray) -> None:
    preview = image[..., :3] if image.shape[-1] >= 3 else image[..., 0]
    preview = np.clip(preview, 0.0, 1.0)
    Image.fromarray((preview * 255.0 + 0.5).astype(np.uint8)).save(path)


def saturation_weight(value: np.ndarray, threshold: float) -> np.ndarray:
    return np.where(
        value <= threshold,
        1.0,
        np.clip((1.0 - value) / max(1.0 - threshold, 1e-6), 0.0, 1.0),
    ).astype(np.float32)


def underexposure_weight(value: np.ndarray, threshold: float) -> np.ndarray:
    return np.where(
        value >= threshold,
        1.0,
        np.clip(value / max(threshold, 1e-6), 0.0, 1.0),
    ).astype(np.float32)


def hdr_merge_aligned(
    short_image: np.ndarray,
    long_image: np.ndarray,
    short_exposure: float,
    long_exposure: float,
    saturation_threshold: float,
    underexposure_threshold: float,
    weight_epsilon: float = 1e-6,
) -> np.ndarray:
    if short_image.shape != long_image.shape:
        raise ValueError(f"shape mismatch: {short_image.shape} vs {long_image.shape}")
    short_max = np.max(short_image, axis=2, keepdims=True)
    long_max = np.max(long_image, axis=2, keepdims=True)
    short_quality = underexposure_weight(short_max, underexposure_threshold)
    long_quality = saturation_weight(long_max, saturation_threshold)
    short_radiance = short_image / short_exposure
    long_radiance = long_image / long_exposure
    merged = (short_quality * short_radiance + long_quality * long_radiance) / (
        short_quality + long_quality + weight_epsilon
    )
    return merged.astype(np.float32)


def write_metrics(path: Path, merged: np.ndarray) -> None:
    luma = merged[..., 0] if merged.shape[-1] == 1 else (
        0.2126 * merged[..., 0] + 0.7152 * merged[..., 1] + 0.0722 * merged[..., 2]
    )
    rows = [
        {"metric": "min", "value": float(np.min(merged))},
        {"metric": "max", "value": float(np.max(merged))},
        {"metric": "mean_luma", "value": float(np.mean(luma))},
        {"metric": "p95_luma", "value": float(np.percentile(luma, 95.0))},
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Python reference for aligned short/long HDR merge")
    parser.add_argument("short")
    parser.add_argument("long")
    parser.add_argument("output")
    parser.add_argument("--short-exposure", type=float, default=0.18)
    parser.add_argument("--long-exposure", type=float, default=0.72)
    parser.add_argument("--saturation-threshold", type=float, default=0.92)
    parser.add_argument("--underexposure-threshold", type=float, default=0.04)
    parser.add_argument("--preview", default="")
    parser.add_argument("--metrics", default="")
    args = parser.parse_args()

    short_image = read_cpf32(Path(args.short))
    long_image = read_cpf32(Path(args.long))
    merged = hdr_merge_aligned(
        short_image,
        long_image,
        args.short_exposure,
        args.long_exposure,
        args.saturation_threshold,
        args.underexposure_threshold,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_cpf32(output_path, merged)
    if args.preview:
        preview_path = Path(args.preview)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        save_preview(preview_path, merged)
    if args.metrics:
        metrics_path = Path(args.metrics)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        write_metrics(metrics_path, merged)


if __name__ == "__main__":
    main()
