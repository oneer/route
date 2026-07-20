#!/usr/bin/env python3
"""Evaluate traditional/ML outputs by frozen Camera scene groups."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import imageio.v3 as iio
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.metrics.camera_scene import aggregate_by_scene_method, evaluate_scene_candidate

MANIFEST_FIELDS = [
    "sample_id", "source_scene", "scene_group", "source_device", "iso", "method",
    "input_path", "output_path", "reference_path", "split", "precision",
    "latency_ms", "latency_scope", "model_size_mb", "status", "boundary",
]
METRIC_FIELDS = [
    "input_psnr", "output_psnr", "psnr_gain", "output_ssim", "noise_rmse_reduction",
    "texture_retention", "edge_loss", "color_bias", "failure_type",
]
SUMMARY_FIELDS = [
    "scene_group", "method", "sample_count",
    "mean_input_psnr", "mean_output_psnr", "mean_psnr_gain", "mean_output_ssim",
    "mean_noise_rmse_reduction", "mean_texture_retention", "mean_edge_loss",
    "mean_color_bias", "failure_count", "failure_rate",
]


def _load_rgb(path: Path) -> np.ndarray:
    image = iio.imread(path)
    if image.ndim == 2:
        image = np.repeat(image[:, :, None], 3, axis=2)
    if image.shape[2] == 4:
        image = image[:, :, :3]
    scale = 255.0 if np.issubdtype(image.dtype, np.integer) else 1.0
    return image.astype(np.float32) / scale


def _write(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _method_rollup(rows: list[dict]) -> list[dict[str, float | int | str]]:
    methods = sorted({str(row["method"]) for row in rows})
    result = []
    for method in methods:
        items = [row for row in rows if row["method"] == method]
        result.append(
            {
                "method": method,
                "sample_count": len(items),
                "psnr": float(np.mean([float(row["output_psnr"]) for row in items])),
                "psnr_gain": float(np.mean([float(row["psnr_gain"]) for row in items])),
                "ssim": float(np.mean([float(row["output_ssim"]) for row in items])),
                "texture": float(np.mean([float(row["texture_retention"]) for row in items])),
                "color_bias": float(np.mean([float(row["color_bias"]) for row in items])),
                "failures": sum(row["failure_type"] != "acceptable" for row in items),
            }
        )
    return result


def _write_reports(rows: list[dict], summary: list[dict], report_root: Path) -> None:
    rollup = _method_rollup(rows)
    lines = [
        "# Camera-scene ML evaluation", "",
        "Frozen evaluation split: 10 public SIDD paired sRGB crops (`val` pair_00011..pair_00020). Source scenes are disjoint from training according to the tracked dataset audit.",
        "", "| Method | Samples | PSNR | PSNR gain | SSIM | Texture retention | Color bias | Failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in rollup:
        lines.append(
            f"| {item['method']} | {item['sample_count']} | {item['psnr']:.3f} | {item['psnr_gain']:.3f} | "
            f"{item['ssim']:.4f} | {item['texture']:.3f} | {item['color_bias']:.5f} | {item['failures']} |"
        )
    lines.extend([
        "", "## Grouping", "",
        "Results are grouped by the real SIDD source device code retained in `source_scene`; per-sample rows also retain ISO. This is more traceable than an invented semantic scene label, but it is not a self-captured Camera feature test set.",
        "", "## Failure taxonomy", "",
        "The deterministic evaluator can emit `quality_regression`, `color_shift`, `over_smoothing`, `edge_loss`, and `excess_high_frequency`. The last label is a residual-noise/oversharpening diagnostic flag, not automatic proof of halo; the CSV reports observed counts without forcing examples into a class.",
        "", "## Boundary", "",
        "DnCNN operates on rendered paired sRGB. It is an RGB restoration feature, not a Bayer/linear Sensor RAW AI-ISP. FP16 is omitted from this image-quality table because a complete frozen-split FP16 output set is not tracked.", "",
    ])
    (report_root / "camera_scene_ml_evaluation.md").write_text("\n".join(lines), encoding="utf-8")

    by_method = {str(item["method"]): item for item in rollup}
    traditional = by_method.get("stage1_bilateral")
    ml = by_method.get("dncnn_ort_fp32")
    tradeoff = [
        "# Traditional vs ML trade-off", "",
        "The comparison uses identical inputs and references. Traditional latency is a warmed single-call measurement from the current run; ORT latency is the existing audited aggregate p50 and therefore is not a direct end-to-end timing race.", "",
    ]
    if traditional and ml:
        tradeoff.extend([
            f"- DnCNN improves mean PSNR by {ml['psnr'] - traditional['psnr']:.3f} dB over the bilateral baseline.",
            f"- DnCNN changes mean texture retention by {ml['texture'] - traditional['texture']:+.3f} relative to bilateral.",
            f"- Observed classified failures: bilateral={traditional['failures']}, DnCNN={ml['failures']}.",
            "- Deployment choice must still consider backend latency, memory, power, and content-specific artifacts; this table alone does not justify always-on ML.", "",
        ])
    tradeoff.extend([
        "## Suggested policy", "",
        "Use the ML path when the frozen evaluation confirms meaningful restoration gain and no texture/color failure trigger. Fall back to the traditional path when the ML result crosses a declared artifact threshold or when the deployment budget cannot absorb the measured backend cost.", "",
        "## Non-claims", "",
        "No production tuning, Sensor RAW processing, Snapdragon latency, mobile power, or INT8/TensorRT quality result is claimed here.", "",
    ])
    (report_root / "traditional_vs_ml_tradeoff.md").write_text("\n".join(tradeoff), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "camera_scene_eval_manifest.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "figures" / "camera_scene_evaluation")
    args = parser.parse_args()
    with args.manifest.open("r", encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    rows: list[dict] = []
    for item in manifest:
        if item["status"] != "available":
            continue
        metrics = evaluate_scene_candidate(
            _load_rgb(ROOT / item["input_path"]),
            _load_rgb(ROOT / item["output_path"]),
            _load_rgb(ROOT / item["reference_path"]),
        )
        rows.append({**item, **metrics})
    summary = aggregate_by_scene_method(rows)
    _write(args.output_dir / "per_sample_metrics.csv", rows, MANIFEST_FIELDS + METRIC_FIELDS)
    _write(args.output_dir / "scene_method_summary.csv", summary, SUMMARY_FIELDS)
    _write_reports(rows, summary, ROOT / "reports")
    print(f"camera_scene_evaluation={args.output_dir} samples={len(rows)} groups={len(summary)}")


if __name__ == "__main__":
    main()
