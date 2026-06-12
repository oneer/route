#!/usr/bin/env python3
"""Export Week 3 real RGB model comparison from existing run folders."""

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


DEFAULT_RUNS = [
    "paired_rgb_sidd_tiny_dncnn_l2_300",
    "paired_rgb_sidd_tiny_unet_l1_300",
    "paired_rgb_sidd_tiny_nafnet_lite_l1_300",
    "paired_rgb_sidd_tiny_dncnn_l2_2000",
    "paired_rgb_sidd_tiny_dncnn_l1_2000",
    "paired_rgb_sidd_tiny_dncnn_l2_patch64_2000",
    "paired_rgb_sidd_tiny_unet_l1_1000",
    "paired_rgb_sidd_tiny_nafnet_lite_l1_1000",
]


@dataclass
class RunSummary:
    run: str
    group: str
    model: str
    loss: str
    residual: bool
    patch_size: int
    steps: int
    batch_size: int
    params: int
    checkpoint_mb: float
    best_psnr: float
    best_psnr_step: int
    best_ssim: float
    best_ssim_step: int
    last_psnr: float
    last_ssim: float
    psnr_gain: float
    ssim_gain: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Week 3 model comparison table.")
    parser.add_argument("--runs-root", default="ai_isp_stage2/runs")
    parser.add_argument("--output-dir", default="ai_isp_stage2/reports/figures/week3_model_comparison")
    parser.add_argument("--input-psnr", type=float, default=26.7302)
    parser.add_argument("--input-ssim", type=float, default=0.52412)
    parser.add_argument("--runs", nargs="*", default=DEFAULT_RUNS)
    return parser.parse_args()


def read_metrics(path: Path) -> list[dict[str, float]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {
                "step": float(row["step"]),
                "train_loss": float(row["train_loss"]),
                "val_psnr": float(row["val_psnr"]),
                "val_ssim": float(row["val_ssim"]),
            }
            for row in reader
        ]


def read_checkpoint(run_dir: Path) -> tuple[dict, float]:
    checkpoint_path = run_dir / "checkpoints" / "best_psnr.pth"
    if not checkpoint_path.exists():
        checkpoint_path = run_dir / "checkpoints" / "last.pth"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"No checkpoint found in {run_dir}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    return checkpoint["config"], checkpoint_path.stat().st_size / (1024 * 1024)


def count_params(config: dict) -> int:
    model = build_model(config["model"])
    return sum(parameter.numel() for parameter in model.parameters())


def group_name(config: dict) -> str:
    steps = int(config["train"]["steps"])
    if steps <= 300:
        return "short_300"
    if "patch64" in config["experiment"]["name"]:
        return "patch_ablation"
    if config["model"]["name"] == "dncnn" and config["train"]["loss"] == "l1":
        return "loss_ablation"
    return "standard"


def summarize_run(run_dir: Path, input_psnr: float, input_ssim: float) -> RunSummary:
    rows = read_metrics(run_dir / "metrics.csv")
    config, checkpoint_mb = read_checkpoint(run_dir)
    best_psnr_row = max(rows, key=lambda row: row["val_psnr"])
    best_ssim_row = max(rows, key=lambda row: row["val_ssim"])
    last = rows[-1]
    model_cfg = config["model"]
    train_cfg = config["train"]
    return RunSummary(
        run=run_dir.name,
        group=group_name(config),
        model=str(model_cfg["name"]),
        loss=str(train_cfg["loss"]),
        residual=bool(model_cfg.get("residual", False)),
        patch_size=int(config["data"]["patch_size"]),
        steps=int(train_cfg["steps"]),
        batch_size=int(train_cfg["batch_size"]),
        params=count_params(config),
        checkpoint_mb=checkpoint_mb,
        best_psnr=float(best_psnr_row["val_psnr"]),
        best_psnr_step=int(best_psnr_row["step"]),
        best_ssim=float(best_ssim_row["val_ssim"]),
        best_ssim_step=int(best_ssim_row["step"]),
        last_psnr=float(last["val_psnr"]),
        last_ssim=float(last["val_ssim"]),
        psnr_gain=float(best_psnr_row["val_psnr"]) - input_psnr,
        ssim_gain=float(best_ssim_row["val_ssim"]) - input_ssim,
    )


def write_csv(rows: list[RunSummary], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "week3_model_comparison.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "group",
                "run",
                "model",
                "loss",
                "residual",
                "patch_size",
                "steps",
                "batch_size",
                "params",
                "checkpoint_mb",
                "best_psnr",
                "best_psnr_step",
                "best_ssim",
                "best_ssim_step",
                "last_psnr",
                "last_ssim",
                "psnr_gain_vs_input",
                "ssim_gain_vs_input",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.group,
                    row.run,
                    row.model,
                    row.loss,
                    row.residual,
                    row.patch_size,
                    row.steps,
                    row.batch_size,
                    row.params,
                    f"{row.checkpoint_mb:.3f}",
                    f"{row.best_psnr:.4f}",
                    row.best_psnr_step,
                    f"{row.best_ssim:.5f}",
                    row.best_ssim_step,
                    f"{row.last_psnr:.4f}",
                    f"{row.last_ssim:.5f}",
                    f"{row.psnr_gain:.4f}",
                    f"{row.ssim_gain:.5f}",
                ]
            )
    return path


def write_markdown(rows: list[RunSummary], output_dir: Path, input_psnr: float, input_ssim: float) -> Path:
    path = output_dir / "week3_model_comparison.md"
    lines = [
        "# Week 3 Model Comparison",
        "",
        "This table summarizes real paired RGB denoise runs on the SIDD tiny subset.",
        "",
        f"Input noisy baseline: PSNR `{input_psnr:.4f}`, SSIM `{input_ssim:.5f}`.",
        "",
        "| Group | Run | Model | Loss | Residual | Patch | Steps | Params | Checkpoint MB | Best PSNR | Best SSIM | PSNR gain | SSIM gain |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.group,
                    row.run,
                    row.model,
                    row.loss,
                    str(row.residual),
                    str(row.patch_size),
                    str(row.steps),
                    str(row.params),
                    f"{row.checkpoint_mb:.3f}",
                    f"{row.best_psnr:.4f}@{row.best_psnr_step}",
                    f"{row.best_ssim:.5f}@{row.best_ssim_step}",
                    f"{row.psnr_gain:.4f}",
                    f"{row.ssim_gain:.5f}",
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Reading Notes",
        "",
        "- `short_300` checks whether each model can learn on the real paired RGB subset.",
        "- `standard` is better for model-capability comparison.",
        "- `loss_ablation` compares DnCNN L1 vs L2 under the same 2000-step setting.",
        "- `patch_ablation` compares patch 64 vs patch 128 for DnCNN L2.",
        "- A run is useful only if it exceeds the noisy input baseline and has a plausible visualization.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    runs_root = Path(args.runs_root)
    rows = [
        summarize_run(runs_root / run, args.input_psnr, args.input_ssim)
        for run in args.runs
        if (runs_root / run / "metrics.csv").exists()
    ]
    output_dir = Path(args.output_dir)
    csv_path = write_csv(rows, output_dir)
    md_path = write_markdown(rows, output_dir, args.input_psnr, args.input_ssim)
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    for row in rows:
        print(
            f"{row.run}: best_psnr={row.best_psnr:.4f}@{row.best_psnr_step} "
            f"best_ssim={row.best_ssim:.5f}@{row.best_ssim_step} "
            f"gain={row.psnr_gain:.4f}/{row.ssim_gain:.5f}"
        )


if __name__ == "__main__":
    main()
