#!/usr/bin/env python3
"""Export a job-facing engineering summary for Stage 2 runs."""
# 中文说明：导出工程摘要，关注参数量、checkpoint 和可部署性信息。

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.models import build_model


@dataclass
class RunEngineeringSummary:
    """中文说明：工程维度摘要，记录参数量、checkpoint 信息和关键指标。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    run: str
    task: str
    model: str
    channels: int
    params: int
    checkpoint_mb: float
    best_psnr: float
    best_ssim: float
    best_psnr_step: int
    best_ssim_step: int


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create Stage 2 engineering summary.")
    parser.add_argument(
        "--leaderboard",
        default="stage2_ai_isp/reports/figures/week9_stage2_summary/stage2_leaderboard.csv",
    )
    parser.add_argument(
        "--runs-root",
        default="stage2_ai_isp/runs",
    )
    parser.add_argument(
        "--output-dir",
        default="stage2_ai_isp/reports/figures/week10_engineering_summary",
    )
    parser.add_argument(
        "--report-md",
        default="stage2_ai_isp/reports/stage2_engineering_summary.md",
    )
    return parser.parse_args()


def count_params(config: dict) -> int:
    """中文说明：实现 `count_params` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    model = build_model(config["model"])
    return sum(parameter.numel() for parameter in model.parameters())


def read_checkpoint(run_dir: Path) -> tuple[dict, float]:
    """中文说明：读取外部文件或模型状态，并转换成当前脚本后续步骤需要的格式。
    
    输入：run_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    checkpoint_path = run_dir / "checkpoints" / "best_psnr.pth"
    if not checkpoint_path.exists():
        checkpoint_path = run_dir / "checkpoints" / "last.pth"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"No checkpoint found in {run_dir}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    config = checkpoint["config"]
    checkpoint_mb = checkpoint_path.stat().st_size / (1024 * 1024)
    return config, checkpoint_mb


def load_rows(leaderboard: Path, runs_root: Path) -> list[RunEngineeringSummary]:
    """中文说明：读取外部文件或模型状态，并转换成当前脚本后续步骤需要的格式。
    
    输入：leaderboard、runs_root。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    rows: list[RunEngineeringSummary] = []
    with leaderboard.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_name = row["run"]
            run_dir = runs_root / run_name
            config, checkpoint_mb = read_checkpoint(run_dir)
            model_cfg = config["model"]
            rows.append(
                RunEngineeringSummary(
                    run=run_name,
                    task=row["task"],
                    model=model_cfg["name"],
                    channels=int(model_cfg.get("in_channels", 3)),
                    params=count_params(config),
                    checkpoint_mb=checkpoint_mb,
                    best_psnr=float(row["best_psnr"]),
                    best_ssim=float(row["best_ssim"]),
                    best_psnr_step=int(row["best_psnr_step"]),
                    best_ssim_step=int(row["best_ssim_step"]),
                )
            )
    return rows


def write_csv(rows: list[RunEngineeringSummary], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 CSV，便于表格查看和后续报告引用。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "stage2_engineering_summary.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "task",
                "run",
                "model",
                "channels",
                "params",
                "checkpoint_mb",
                "best_psnr",
                "best_ssim",
                "best_psnr_step",
                "best_ssim_step",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.task,
                    row.run,
                    row.model,
                    row.channels,
                    row.params,
                    f"{row.checkpoint_mb:.3f}",
                    f"{row.best_psnr:.4f}",
                    f"{row.best_ssim:.5f}",
                    row.best_psnr_step,
                    row.best_ssim_step,
                ]
            )
    return path


def write_markdown(rows: list[RunEngineeringSummary], report_path: Path, csv_path: Path) -> None:
    """中文说明：把汇总结果写成 Markdown，便于直接放入阶段文档。
    
    输入：rows、report_path、csv_path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    lines = [
        "# Stage 2 Engineering Summary",
        "",
        "This report upgrades the Week 9 leaderboard into a job-facing engineering table.",
        "",
        f"CSV: `{csv_path.as_posix()}`",
        "",
        "| Task | Run | Model | Channels | Params | Checkpoint MB | PSNR | SSIM |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.task,
                    row.run,
                    row.model,
                    str(row.channels),
                    str(row.params),
                    f"{row.checkpoint_mb:.3f}",
                    f"{row.best_psnr:.4f}",
                    f"{row.best_ssim:.5f}",
                ]
            )
            + " |"
        )

    lines += [
        "",
        "## Interview Use",
        "",
        "- Use PSNR/SSIM to discuss restoration quality.",
        "- Use params and checkpoint size to discuss deployability.",
        "- Use channel count to distinguish RGB and RAW-like experiments.",
        "- Merge held-out test and deployment evidence from reports/deployment_evidence.json.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    rows = load_rows(Path(args.leaderboard), Path(args.runs_root))
    csv_path = write_csv(rows, Path(args.output_dir))
    write_markdown(rows, Path(args.report_md), csv_path)
    print(f"saved: {csv_path}")
    print(f"saved: {args.report_md}")


if __name__ == "__main__":
    main()
