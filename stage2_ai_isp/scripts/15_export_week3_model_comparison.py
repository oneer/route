#!/usr/bin/env python3
"""Export Week 3 real RGB model comparison from existing run folders."""
# 中文说明：导出 Week3 模型对比报告。

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
    """中文说明：单次训练运行的摘要结构，聚合最佳指标、最终指标和可视化路径。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
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
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create Week 3 model comparison table.")
    parser.add_argument("--runs-root", default="stage2_ai_isp/runs")
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week3_model_comparison")
    parser.add_argument("--input-psnr", type=float, default=26.7302)
    parser.add_argument("--input-ssim", type=float, default=0.52412)
    parser.add_argument("--runs", nargs="*", default=DEFAULT_RUNS)
    return parser.parse_args()


def read_metrics(path: Path) -> list[dict[str, float]]:
    """中文说明：读取训练过程记录的 metrics.csv，并转换成后续汇总需要的数据结构。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    return checkpoint["config"], checkpoint_path.stat().st_size / (1024 * 1024)


def count_params(config: dict) -> int:
    """中文说明：实现 `count_params` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    model = build_model(config["model"])
    return sum(parameter.numel() for parameter in model.parameters())


def group_name(config: dict) -> str:
    """中文说明：实现 `group_name` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    steps = int(config["train"]["steps"])
    if steps <= 300:
        return "short_300"
    if "patch64" in config["experiment"]["name"]:
        return "patch_ablation"
    if config["model"]["name"] == "dncnn" and config["train"]["loss"] == "l1":
        return "loss_ablation"
    return "standard"


def summarize_run(run_dir: Path, input_psnr: float, input_ssim: float) -> RunSummary:
    """中文说明：读取单次实验的曲线、checkpoint 和可视化资产，形成统一摘要。
    
    输入：run_dir、input_psnr、input_ssim。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：把汇总结果写成 CSV，便于表格查看和后续报告引用。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：把汇总结果写成 Markdown，便于直接放入阶段文档。
    
    输入：rows、output_dir、input_psnr、input_ssim。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
