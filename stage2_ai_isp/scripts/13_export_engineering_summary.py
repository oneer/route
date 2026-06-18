#!/usr/bin/env python3
"""Export a job-facing engineering summary for Stage 2 runs."""

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
    model = build_model(config["model"])
    return sum(parameter.numel() for parameter in model.parameters())


def read_checkpoint(run_dir: Path) -> tuple[dict, float]:
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
    args = parse_args()
    rows = load_rows(Path(args.leaderboard), Path(args.runs_root))
    csv_path = write_csv(rows, Path(args.output_dir))
    write_markdown(rows, Path(args.report_md), csv_path)
    print(f"saved: {csv_path}")
    print(f"saved: {args.report_md}")


if __name__ == "__main__":
    main()
