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
    ratio = crop_mae / max(median_mae, 1e-12)
    if ratio >= 1.1:
        return (
            "high local error",
            f"Top-error crop MAE is {ratio:.2f}x the group median.",
            "The numeric evidence locates a difficult ROI but cannot identify whether the cause is texture, color, alignment, data, loss, or model capacity.",
            "Inspect the exact ROI and full-image error map, assign a human failure label, then design one controlled experiment.",
        )
    if ratio <= 0.9:
        return (
            "lower relative local error",
            f"Top-error crop MAE is {ratio:.2f}x the group median.",
            "This ROI is lower than peers under the current crop-mining rule, but one crop cannot establish global superiority.",
            "Check full-image PSNR/SSIM and additional top-k ROIs before drawing a model conclusion.",
        )
    return (
        "moderate local error",
        f"Top-error crop MAE is {ratio:.2f}x the group median.",
        "Automatic metrics show severity, not semantic cause.",
        "Inspect the ROI and label it as flat/edge/texture/dark/color/alignment before proposing a fix.",
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
