#!/usr/bin/env python3
"""Export Week 6 pseudo RAW/RGGB training summary."""
# 中文说明：导出 Week6 伪 RAW 实验总结。

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys

import torch
from torch.utils.data import DataLoader
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.data.paired_image_dataset import PairedImageDenoiseDataset
from ai_isp.data.paired_pseudo_raw_dataset import PairedPseudoRawDataset
from ai_isp.metrics.psnr_ssim import batch_psnr, batch_ssim
from ai_isp.models import build_model


DEFAULT_RUNS = [
    ("rgb_300", "stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_300.yaml"),
    ("pseudo_rggb_300", "stage2_ai_isp/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml"),
]


@dataclass
class Week6Row:
    """中文说明：Week6 伪 RAW 实验摘要行。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    label: str
    run: str
    dataset: str
    channels: int
    patch_size: int
    effective_spatial: str
    params: int
    input_psnr: float
    input_ssim: float
    best_psnr: float
    best_psnr_step: int
    best_ssim: float
    best_ssim_step: int
    psnr_gain: float
    ssim_gain: float


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create Week 6 pseudo RAW/RGGB summary.")
    parser.add_argument("--runs-root", default="stage2_ai_isp/runs")
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week6_pseudo_raw_training")
    return parser.parse_args()


def read_config(path: Path) -> dict:
    """中文说明：读取外部文件或模型状态，并转换成当前脚本后续步骤需要的格式。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_project_path(path: str | Path) -> Path:
    """中文说明：把配置中的相对路径解析到项目根目录下，避免从不同工作目录运行时路径漂移。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    resolved = Path(path)
    return resolved if resolved.is_absolute() else ROOT / resolved


def build_val_dataset(config: dict):
    """中文说明：构造后续流程需要的对象或可视化产物，把零散配置集中成可复用结果。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    data_cfg = config["data"]
    val_cfg = data_cfg["val"]
    dataset_cls = PairedPseudoRawDataset if data_cfg["dataset"] == "paired_pseudo_raw" else PairedImageDenoiseDataset
    return dataset_cls(
        noisy_dir=resolve_project_path(val_cfg["noisy_dir"]),
        clean_dir=resolve_project_path(val_cfg["clean_dir"]),
        patch_size=data_cfg["patch_size"],
        size=data_cfg["val_size"],
        seed=config["experiment"].get("seed", 42) + 10000,
    )


def measure_input_baseline(config: dict) -> tuple[float, float]:
    """中文说明：实现 `measure_input_baseline` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    dataset = build_val_dataset(config)
    loader = DataLoader(dataset, batch_size=config["train"]["batch_size"], shuffle=False)
    psnr_values = []
    ssim_values = []
    for batch in loader:
        noisy = batch["noisy"]
        clean = batch["clean"]
        psnr_values.append(batch_psnr(noisy, clean))
        ssim_values.append(batch_ssim(noisy, clean))
    return torch.cat(psnr_values).mean().item(), torch.cat(ssim_values).mean().item()


def read_metrics(run_dir: Path) -> tuple[float, int, float, int]:
    """中文说明：读取训练过程记录的 metrics.csv，并转换成后续汇总需要的数据结构。
    
    输入：run_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    with (run_dir / "metrics.csv").open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    best_psnr = max(rows, key=lambda row: float(row["val_psnr"]))
    best_ssim = max(rows, key=lambda row: float(row["val_ssim"]))
    return (
        float(best_psnr["val_psnr"]),
        int(float(best_psnr["step"])),
        float(best_ssim["val_ssim"]),
        int(float(best_ssim["step"])),
    )


def effective_spatial(config: dict) -> str:
    """中文说明：实现 `effective_spatial` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    patch_size = int(config["data"]["patch_size"])
    if config["data"]["dataset"] == "paired_pseudo_raw":
        return f"{patch_size // 2}x{patch_size // 2} pack from {patch_size}x{patch_size} RGB crop"
    return f"{patch_size}x{patch_size}"


def summarize(label: str, config_path: Path, runs_root: Path) -> Week6Row:
    """中文说明：从原始记录中提炼关键统计量，降低报告和诊断脚本的重复逻辑。
    
    输入：label、config_path、runs_root。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    config = read_config(config_path)
    run_name = config["experiment"]["name"]
    channels = int(config["model"].get("in_channels", 3))
    params = sum(parameter.numel() for parameter in build_model(config["model"]).parameters())
    input_psnr, input_ssim = measure_input_baseline(config)
    best_psnr, best_psnr_step, best_ssim, best_ssim_step = read_metrics(runs_root / run_name)
    return Week6Row(
        label=label,
        run=run_name,
        dataset=config["data"]["dataset"],
        channels=channels,
        patch_size=int(config["data"]["patch_size"]),
        effective_spatial=effective_spatial(config),
        params=params,
        input_psnr=input_psnr,
        input_ssim=input_ssim,
        best_psnr=best_psnr,
        best_psnr_step=best_psnr_step,
        best_ssim=best_ssim,
        best_ssim_step=best_ssim_step,
        psnr_gain=best_psnr - input_psnr,
        ssim_gain=best_ssim - input_ssim,
    )


def write_csv(rows: list[Week6Row], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 CSV，便于表格查看和后续报告引用。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "week6_pseudo_raw_summary.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "label",
                "run",
                "dataset",
                "channels",
                "patch_size",
                "effective_spatial",
                "params",
                "input_psnr",
                "input_ssim",
                "best_psnr",
                "best_psnr_step",
                "best_ssim",
                "best_ssim_step",
                "psnr_gain",
                "ssim_gain",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.label,
                    row.run,
                    row.dataset,
                    row.channels,
                    row.patch_size,
                    row.effective_spatial,
                    row.params,
                    f"{row.input_psnr:.4f}",
                    f"{row.input_ssim:.5f}",
                    f"{row.best_psnr:.4f}",
                    row.best_psnr_step,
                    f"{row.best_ssim:.5f}",
                    row.best_ssim_step,
                    f"{row.psnr_gain:.4f}",
                    f"{row.ssim_gain:.5f}",
                ]
            )
    return path


def write_markdown(rows: list[Week6Row], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 Markdown，便于直接放入阶段文档。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    path = output_dir / "week6_pseudo_raw_summary.md"
    lines = [
        "# Week 6 Pseudo RAW/RGGB Training Summary",
        "",
        "This summary compares the RGB denoise baseline with the pseudo RGGB 4-channel baseline.",
        "",
        "| Label | Run | Dataset | Channels | Effective spatial | Params | Input PSNR/SSIM | Best PSNR | Best SSIM | Gain PSNR/SSIM |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.label,
                    row.run,
                    row.dataset,
                    str(row.channels),
                    row.effective_spatial,
                    str(row.params),
                    f"{row.input_psnr:.4f}/{row.input_ssim:.5f}",
                    f"{row.best_psnr:.4f}@{row.best_psnr_step}",
                    f"{row.best_ssim:.5f}@{row.best_ssim_step}",
                    f"{row.psnr_gain:.4f}/{row.ssim_gain:.5f}",
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- The pseudo RGGB path is RAW-like, not real sensor RAW.",
        "- Pseudo RGGB converts each RGB crop into a 4-channel RGGB pack, so the model input has 4 channels and half spatial resolution.",
        "- RGB and pseudo RGGB PSNR values are not a perfect apples-to-apples image-domain comparison, but they verify that the RAW-shaped path is trainable.",
        "- The key Week 6 acceptance criterion is that the pseudo RGGB run produces metrics and checkpoints and exceeds its own noisy input baseline.",
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
    rows = [summarize(label, Path(config), runs_root) for label, config in DEFAULT_RUNS]
    output_dir = Path(args.output_dir)
    csv_path = write_csv(rows, output_dir)
    md_path = write_markdown(rows, output_dir)
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    for row in rows:
        print(
            f"{row.label}: input={row.input_psnr:.4f}/{row.input_ssim:.5f} "
            f"best={row.best_psnr:.4f}/{row.best_ssim:.5f} "
            f"gain={row.psnr_gain:.4f}/{row.ssim_gain:.5f}"
        )


if __name__ == "__main__":
    main()
