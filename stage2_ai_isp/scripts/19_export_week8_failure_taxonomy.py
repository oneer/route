#!/usr/bin/env python3
"""Export Week 8 failure taxonomy from crop-level metrics."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FailureRow:
    run: str
    crop_mae: float
    failure_type: str
    evidence: str
    likely_reason: str
    next_step: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Week 8 failure taxonomy table.")
    parser.add_argument(
        "--crop-metrics",
        default="stage2_ai_isp/reports/figures/week8_failure_case_crops/failure_case_crop_metrics.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="stage2_ai_isp/reports/figures/week8_failure_taxonomy",
    )
    return parser.parse_args()


def classify(run: str, crop_mae: float, median_mae: float) -> tuple[str, str, str, str]:
    if "low_light" in run:
        return (
            "dark-region enhancement / over-smoothing",
            "Low-light crop has high local error while the task also changes exposure.",
            "The model must brighten, denoise, and preserve color at the same time; synthetic low-light degradation is harder than plain denoise.",
            "Add exposure/noise-specific IQ metrics, inspect dark ROI, and compare brightness/color statistics before changing model size.",
        )
    if "unet" in run:
        return (
            "local texture or color residual",
            "UNet can keep structural similarity high, but crop MAE is relatively high.",
            "Encoder-decoder structure preserves coarse structure, but direct-output training may leave pixel/color residual in local crops.",
            "Inspect texture/edge crops; compare residual-output UNet or add local/color-aware analysis.",
        )
    if "nafnet" in run:
        return (
            "under-trained modern block / residual noise",
            "NAFNet-lite improves over input baseline but still trails the strongest DnCNN run.",
            "The simplified NAFNet-lite setting uses limited data and 1000 steps, without full official training strategy.",
            "Extend NAFNet-lite to 2000 steps or test Charbonnier loss before judging the architecture.",
        )
    if "patch64" in run:
        return (
            "context-limited denoise",
            "Patch64 has competitive SSIM but lower PSNR than patch128.",
            "Smaller patch sees less spatial context, which can limit pixel-accurate restoration on texture/edge regions.",
            "Use patch64 for quick ablation, but keep patch128 for final-quality runs.",
        )
    if "dncnn_l1" in run:
        return (
            "strong baseline / residual local error",
            "DnCNN L1 has the best global metrics, but crop error is still non-zero.",
            "Residual denoise fits the task well, but local texture and color differences remain due to tiny data and simple loss.",
            "Use it as the current baseline; inspect error map before deciding whether Charbonnier or more data is worthwhile.",
        )
    if "dncnn_l2" in run:
        note = "Crop MAE is below or near the group median." if crop_mae <= median_mae else "Crop MAE is above the group median."
        return (
            "baseline smoothing / residual local error",
            f"DnCNN L2 is strong globally; {note}",
            "MSE aligns with PSNR but can slightly smooth uncertain texture.",
            "Compare against DnCNN L1 and crop-level visual details rather than relying only on PSNR.",
        )
    return (
        "unclassified local error",
        "Crop has measurable output-clean difference.",
        "The current automatic taxonomy does not know this run type.",
        "Inspect triplet, error map, and config manually.",
    )


def read_metrics(path: Path) -> list[tuple[str, float]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [(row["run"], float(row["crop_mae"])) for row in reader]


def write_csv(rows: list[FailureRow], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "week8_failure_taxonomy.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["run", "crop_mae", "failure_type", "evidence", "likely_reason", "next_step"])
        for row in rows:
            writer.writerow(
                [
                    row.run,
                    f"{row.crop_mae:.6f}",
                    row.failure_type,
                    row.evidence,
                    row.likely_reason,
                    row.next_step,
                ]
            )
    return path


def write_markdown(rows: list[FailureRow], output_dir: Path) -> Path:
    path = output_dir / "week8_failure_taxonomy.md"
    lines = [
        "# Week 8 Failure Taxonomy",
        "",
        "This table turns crop-level evidence into actionable debugging hypotheses.",
        "",
        "| Run | Crop MAE | Failure Type | Evidence | Likely Reason | Next Step |",
        "|---|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.run,
                    f"{row.crop_mae:.6f}",
                    row.failure_type,
                    row.evidence,
                    row.likely_reason,
                    row.next_step,
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Reading Notes",
        "",
        "- This taxonomy is a first-pass diagnosis from crop metrics and run identity.",
        "- It must be read together with `failure_case_crop_sheet.png` and the Week 4 error maps.",
        "- The goal is not to prove a final cause, but to decide the next experiment without guessing blindly.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    metrics = read_metrics(Path(args.crop_metrics))
    maes = sorted(mae for _, mae in metrics)
    median_mae = maes[len(maes) // 2] if maes else 0.0
    rows = []
    for run, crop_mae in metrics:
        failure_type, evidence, likely_reason, next_step = classify(run, crop_mae, median_mae)
        rows.append(
            FailureRow(
                run=run,
                crop_mae=crop_mae,
                failure_type=failure_type,
                evidence=evidence,
                likely_reason=likely_reason,
                next_step=next_step,
            )
        )
    output_dir = Path(args.output_dir)
    csv_path = write_csv(rows, output_dir)
    md_path = write_markdown(rows, output_dir)
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    for row in rows:
        print(f"{row.run}: mae={row.crop_mae:.6f} type={row.failure_type}")


if __name__ == "__main__":
    main()
