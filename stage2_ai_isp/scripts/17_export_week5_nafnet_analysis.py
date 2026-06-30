#!/usr/bin/env python3
"""Export Week 5 NAFNet-lite architecture and training analysis."""
# 中文说明：导出 Week5 NAFNet 结构与实验分析。

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys

import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.models import build_model
from ai_isp.models.nafnet_lite import NAFBlock, LayerNorm2d, NAFNetLite, SimpleGate


DEFAULT_CONFIGS = [
    "stage2_ai_isp/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_300.yaml",
    "stage2_ai_isp/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml",
    "stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml",
    "stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l1_2000.yaml",
    "stage2_ai_isp/configs/paired_rgb_sidd_tiny_unet_l1_1000.yaml",
]


@dataclass
class ModelRunAnalysis:
    """中文说明：模型运行分析结构，聚合配置、指标和结构统计。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    run: str
    model: str
    width: str
    blocks: str
    loss: str
    patch_size: int
    steps: int
    batch_size: int
    params: int
    input_shape: str
    output_shape: str
    best_psnr: float
    best_psnr_step: int
    best_ssim: float
    best_ssim_step: int
    psnr_gap_to_dncnn_l1: float
    psnr_gap_to_dncnn_l2: float


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create Week 5 NAFNet-lite analysis.")
    parser.add_argument("--configs", nargs="*", default=DEFAULT_CONFIGS)
    parser.add_argument("--runs-root", default="stage2_ai_isp/runs")
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week5_nafnet_analysis")
    return parser.parse_args()


def read_config(path: Path) -> dict:
    """中文说明：读取外部文件或模型状态，并转换成当前脚本后续步骤需要的格式。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_metrics(run_dir: Path) -> tuple[float, int, float, int]:
    """中文说明：读取训练过程记录的 metrics.csv，并转换成后续汇总需要的数据结构。
    
    输入：run_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    metrics_path = run_dir / "metrics.csv"
    with metrics_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    best_psnr = max(rows, key=lambda row: float(row["val_psnr"]))
    best_ssim = max(rows, key=lambda row: float(row["val_ssim"]))
    return (
        float(best_psnr["val_psnr"]),
        int(float(best_psnr["step"])),
        float(best_ssim["val_ssim"]),
        int(float(best_ssim["step"])),
    )


def count_modules(model: torch.nn.Module) -> dict[str, int]:
    """中文说明：实现 `count_modules` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：model。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    return {
        "naf_blocks": sum(1 for module in model.modules() if isinstance(module, NAFBlock)),
        "simple_gates": sum(1 for module in model.modules() if isinstance(module, SimpleGate)),
        "layer_norms": sum(1 for module in model.modules() if isinstance(module, LayerNorm2d)),
    }


def shape_check(model: torch.nn.Module, patch_size: int) -> tuple[str, str]:
    """中文说明：实现 `shape_check` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：model、patch_size。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    model.eval()
    x = torch.randn(2, 3, patch_size, patch_size)
    with torch.no_grad():
        y = model(x)
    if y.shape != x.shape:
        raise ValueError(f"Shape mismatch: input {tuple(x.shape)} output {tuple(y.shape)}")
    return str(tuple(x.shape)), str(tuple(y.shape))


def block_desc(config: dict, model: torch.nn.Module) -> str:
    """中文说明：实现 `block_desc` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config、model。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    model_cfg = config["model"]
    if model_cfg["name"] != "nafnet_lite":
        return "-"
    counts = count_modules(model)
    return (
        f"enc={model_cfg.get('encoder_blocks')}, dec={model_cfg.get('decoder_blocks')}, "
        f"middle={model_cfg.get('middle_blocks')}, naf_blocks={counts['naf_blocks']}, "
        f"gates={counts['simple_gates']}"
    )


def width_desc(config: dict) -> str:
    """中文说明：实现 `width_desc` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    model_cfg = config["model"]
    if model_cfg["name"] == "nafnet_lite":
        return str(model_cfg.get("width"))
    if model_cfg["name"] == "dncnn":
        return f"features={model_cfg.get('features')}"
    if model_cfg["name"] == "unet":
        return f"base={model_cfg.get('base_channels')}"
    return "-"


def summarize(config_path: Path, runs_root: Path, dncnn_l1_psnr: float, dncnn_l2_psnr: float) -> ModelRunAnalysis:
    """中文说明：从原始记录中提炼关键统计量，降低报告和诊断脚本的重复逻辑。
    
    输入：config_path、runs_root、dncnn_l1_psnr、dncnn_l2_psnr。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    config = read_config(config_path)
    run_name = config["experiment"]["name"]
    run_dir = runs_root / run_name
    model = build_model(config["model"])
    params = sum(parameter.numel() for parameter in model.parameters())
    input_shape, output_shape = shape_check(model, int(config["data"]["patch_size"]))
    best_psnr, best_psnr_step, best_ssim, best_ssim_step = read_metrics(run_dir)
    return ModelRunAnalysis(
        run=run_name,
        model=config["model"]["name"],
        width=width_desc(config),
        blocks=block_desc(config, model),
        loss=config["train"]["loss"],
        patch_size=int(config["data"]["patch_size"]),
        steps=int(config["train"]["steps"]),
        batch_size=int(config["train"]["batch_size"]),
        params=params,
        input_shape=input_shape,
        output_shape=output_shape,
        best_psnr=best_psnr,
        best_psnr_step=best_psnr_step,
        best_ssim=best_ssim,
        best_ssim_step=best_ssim_step,
        psnr_gap_to_dncnn_l1=best_psnr - dncnn_l1_psnr,
        psnr_gap_to_dncnn_l2=best_psnr - dncnn_l2_psnr,
    )


def write_csv(rows: list[ModelRunAnalysis], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 CSV，便于表格查看和后续报告引用。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "week5_nafnet_analysis.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "run",
                "model",
                "width",
                "blocks",
                "loss",
                "patch_size",
                "steps",
                "batch_size",
                "params",
                "input_shape",
                "output_shape",
                "best_psnr",
                "best_psnr_step",
                "best_ssim",
                "best_ssim_step",
                "psnr_gap_to_dncnn_l1",
                "psnr_gap_to_dncnn_l2",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.run,
                    row.model,
                    row.width,
                    row.blocks,
                    row.loss,
                    row.patch_size,
                    row.steps,
                    row.batch_size,
                    row.params,
                    row.input_shape,
                    row.output_shape,
                    f"{row.best_psnr:.4f}",
                    row.best_psnr_step,
                    f"{row.best_ssim:.5f}",
                    row.best_ssim_step,
                    f"{row.psnr_gap_to_dncnn_l1:.4f}",
                    f"{row.psnr_gap_to_dncnn_l2:.4f}",
                ]
            )
    return path


def write_markdown(rows: list[ModelRunAnalysis], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 Markdown，便于直接放入阶段文档。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    path = output_dir / "week5_nafnet_analysis.md"
    lines = [
        "# Week 5 NAFNet-lite Analysis",
        "",
        "This report checks whether NAFNet-lite is correctly implemented, shape-compatible, and meaningfully compared against Week 3 baselines.",
        "",
        "| Run | Model | Width | Loss | Steps | Params | Shape | Best PSNR | Best SSIM | Gap vs DnCNN L1 | Gap vs DnCNN L2 |",
        "|---|---|---|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.run,
                    row.model,
                    row.width,
                    row.loss,
                    str(row.steps),
                    str(row.params),
                    f"{row.input_shape} -> {row.output_shape}",
                    f"{row.best_psnr:.4f}@{row.best_psnr_step}",
                    f"{row.best_ssim:.5f}@{row.best_ssim_step}",
                    f"{row.psnr_gap_to_dncnn_l1:.4f}",
                    f"{row.psnr_gap_to_dncnn_l2:.4f}",
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## NAFNet-lite Structure Checks",
        "",
    ]
    for row in rows:
        if row.model == "nafnet_lite":
            lines.append(f"- `{row.run}`: {row.blocks}")
    lines += [
        "",
        "## Reading Notes",
        "",
        "- Shape compatibility means each model can be trained with pixel-wise restoration loss.",
        "- The 300-step width=8 NAFNet-lite run is a smoke test, not a capability conclusion.",
        "- The 1000-step width=16 NAFNet-lite run shows clear learning, but still trails DnCNN on this tiny split.",
        "- A fairer next NAFNet-lite experiment would keep width=16 and extend to 2000 steps or compare Charbonnier loss.",
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

    dncnn_l1_psnr, _, _, _ = read_metrics(runs_root / "paired_rgb_sidd_tiny_dncnn_l1_2000")
    dncnn_l2_psnr, _, _, _ = read_metrics(runs_root / "paired_rgb_sidd_tiny_dncnn_l2_2000")
    rows = [
        summarize(Path(config), runs_root, dncnn_l1_psnr, dncnn_l2_psnr)
        for config in args.configs
        if (runs_root / read_config(Path(config))["experiment"]["name"] / "metrics.csv").exists()
    ]
    output_dir = Path(args.output_dir)
    csv_path = write_csv(rows, output_dir)
    md_path = write_markdown(rows, output_dir)
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    for row in rows:
        print(
            f"{row.run}: shape={row.input_shape}->{row.output_shape} "
            f"params={row.params} best={row.best_psnr:.4f}/{row.best_ssim:.5f} "
            f"gap_to_dncnn_l1={row.psnr_gap_to_dncnn_l1:.4f}"
        )


if __name__ == "__main__":
    main()
