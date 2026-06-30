#!/usr/bin/env python3
"""Export Week 8 failure taxonomy from crop-level metrics."""
# 中文说明：导出 Week8 失败案例分类。

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FailureRow:
    """中文说明：失败案例分类摘要行。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    run: str
    crop_mae: float
    failure_type: str
    evidence: str
    likely_reason: str
    next_step: str


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
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
    """中文说明：实现 `classify` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：run、crop_mae、median_mae。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：读取训练过程记录的 metrics.csv，并转换成后续汇总需要的数据结构。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [(row["run"], float(row["crop_mae"])) for row in reader]


def write_csv(rows: list[FailureRow], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 CSV，便于表格查看和后续报告引用。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：把汇总结果写成 Markdown，便于直接放入阶段文档。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
