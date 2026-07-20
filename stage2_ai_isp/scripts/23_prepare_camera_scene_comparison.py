#!/usr/bin/env python3
"""Prepare a same-split traditional-vs-ML Stage 2 evaluation manifest."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import imageio.v3 as iio
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
STAGE1_ROOT = REPO_ROOT / "stage1_soft_isp"
sys.path.insert(0, str(STAGE1_ROOT))

from soft_isp.denoise import bilateral_denoise_rgb


FIELDS = [
    "sample_id", "source_scene", "scene_group", "source_device", "iso",
    "method", "input_path", "output_path", "reference_path", "split",
    "precision", "latency_ms", "latency_scope", "model_size_mb", "status", "boundary",
]


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _stage2_relative(path: Path) -> str:
    return Path(os.path.relpath(path.resolve(), ROOT.resolve())).as_posix()


def _repo_path_from_stage4_manifest(value: str) -> Path:
    return (REPO_ROOT / "stage4_deploy_isp" / value).resolve()


def _parse_scene(source_scene: str) -> tuple[str, str]:
    parts = source_scene.split("_")
    if len(parts) < 4:
        raise ValueError(f"unexpected SIDD source_scene: {source_scene}")
    return parts[2], str(int(parts[3]))


def _write_rgb(path: Path, image_01: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(path, (np.clip(image_01, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evaluation-manifest",
        type=Path,
        default=REPO_ROOT / "stage4_deploy_isp" / "data" / "test_inputs" / "week4_evaluation_manifest.csv",
    )
    parser.add_argument("--sidd-manifest", type=Path, default=ROOT / "datasets" / "sidd_tiny" / "manifest.csv")
    parser.add_argument(
        "--ml-output-dir",
        type=Path,
        default=REPO_ROOT / "stage4_deploy_isp" / "outputs" / "week1_onnx" / "ort_outputs",
    )
    parser.add_argument(
        "--traditional-output-dir",
        type=Path,
        default=ROOT / "reports" / "figures" / "camera_scene_evaluation" / "traditional_outputs",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "camera_scene_eval_manifest.csv")
    parser.add_argument("--sigma-range", type=float, default=0.10)
    args = parser.parse_args()

    evaluation = _read(args.evaluation_manifest)
    source_by_key = {
        (row["split"], row["name"]): row["source_scene"]
        for row in _read(args.sidd_manifest)
    }
    rows: list[dict[str, str]] = []
    for item in evaluation:
        sample_id = item["id"]
        source_scene = source_by_key[("val", item["name"])]
        device, iso = _parse_scene(source_scene)
        scene_group = f"sidd_device_{device}"
        noisy_path = _repo_path_from_stage4_manifest(item["noisy_path"])
        clean_path = _repo_path_from_stage4_manifest(item["clean_path"])
        ml_path = args.ml_output_dir / f"{sample_id}_ort_output.png"
        for required in (noisy_path, clean_path, ml_path):
            if not required.is_file():
                raise FileNotFoundError(required)

        noisy_u8 = iio.imread(noisy_path)[:, :, :3]
        noisy = noisy_u8.astype(np.float32) / 255.0
        bilateral_denoise_rgb(noisy, sigma_range=args.sigma_range)  # warm-up
        start = time.perf_counter()
        traditional = bilateral_denoise_rgb(noisy, sigma_range=args.sigma_range)
        traditional_ms = (time.perf_counter() - start) * 1000.0
        traditional_path = args.traditional_output_dir / f"{sample_id}_bilateral.png"
        _write_rgb(traditional_path, traditional)

        common = {
            "sample_id": sample_id,
            "source_scene": source_scene,
            "scene_group": scene_group,
            "source_device": device,
            "iso": iso,
            "input_path": _stage2_relative(noisy_path),
            "reference_path": _stage2_relative(clean_path),
            "split": "evaluation",
            "status": "available",
        }
        rows.extend(
            [
                {
                    **common,
                    "method": "no_denoise",
                    "output_path": _stage2_relative(noisy_path),
                    "precision": "uint8_srgb",
                    "latency_ms": "0",
                    "latency_scope": "identity baseline; no processing",
                    "model_size_mb": "0",
                    "boundary": "Paired public SIDD sRGB baseline; not Sensor RAW.",
                },
                {
                    **common,
                    "method": "stage1_bilateral",
                    "output_path": _stage2_relative(traditional_path),
                    "precision": "float32_cpu",
                    "latency_ms": f"{traditional_ms:.6f}",
                    "latency_scope": "single warmed 512x512 call; excludes file I/O",
                    "model_size_mb": "0",
                    "boundary": f"Stage 1 OpenCV bilateral RGB baseline; sigma_range={args.sigma_range:g}.",
                },
                {
                    **common,
                    "method": "dncnn_ort_fp32",
                    "output_path": _stage2_relative(ml_path),
                    "precision": "fp32",
                    "latency_ms": "67.151050",
                    "latency_scope": "existing ORT CPU aggregate p50; 1x3x512x512; excludes file I/O",
                    "model_size_mb": "0.014556",
                    "boundary": "Tracked ORT output aligned to PyTorch; paired RGB restoration, not Sensor RAW AI-ISP.",
                },
            ]
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"camera_scene_manifest={args.output} samples={len(evaluation)} rows={len(rows)}")


if __name__ == "__main__":
    main()
