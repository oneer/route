#!/usr/bin/env python3
"""Export Week 1 toy RGB denoise summary from existing run metrics."""
# 中文说明：导出 Week1 toy 实验总结。

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class ExperimentSpec:
    """中文说明：实验规格描述，用于把多个 Week1 实验统一汇总和绘图。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    group: str
    run: str
    label: str
    lesson: str


EXPERIMENTS = [
    ExperimentSpec("TinyCNN probe", "toy_rgb_denoise_tiny_10", "TinyCNN 10 steps", "training just starts"),
    ExperimentSpec("TinyCNN probe", "toy_rgb_denoise_tiny_50", "TinyCNN 50 steps", "loss/metrics begin to improve"),
    ExperimentSpec("TinyCNN probe", "toy_rgb_denoise_tiny_100_probe", "TinyCNN 100 steps", "closed loop is working"),
    ExperimentSpec("Model baseline", "toy_rgb_denoise_dncnn", "DnCNN residual 300", "stronger denoise prior"),
    ExperimentSpec("Model baseline", "toy_rgb_denoise_dncnn_direct", "DnCNN direct 300", "direct clean is harder"),
    ExperimentSpec("Model baseline", "toy_rgb_denoise_unet", "UNet 300", "model name is not enough"),
    ExperimentSpec("Residual vs direct", "toy_rgb_denoise_dncnn_long", "DnCNN residual 1000", "residual keeps improving"),
    ExperimentSpec("Residual vs direct", "toy_rgb_denoise_dncnn_direct_long", "DnCNN direct 1000", "direct improves but lags"),
    ExperimentSpec("Loss", "toy_rgb_denoise_dncnn_l1_loss", "DnCNN L1", "SSIM-oriented comparison"),
    ExperimentSpec("Loss", "toy_rgb_denoise_dncnn_l2_loss", "DnCNN L2/MSE", "PSNR-oriented comparison"),
    ExperimentSpec("Patch", "toy_rgb_denoise_dncnn_l2_patch128", "DnCNN patch 128", "more context, more cost"),
    ExperimentSpec("Noise", "toy_rgb_denoise_dncnn_l2_shot_read_calibrated", "DnCNN shot/read", "sensor-noise intuition"),
    ExperimentSpec("Paired smoke", "paired_rgb_smoke_dncnn_l2", "Paired RGB smoke", "folder pair pipeline"),
]


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create Week 1 summary table and figure.")
    parser.add_argument("--runs-root", default="stage2_ai_isp/runs")
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week1_summary")
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """中文说明：选择绘图可用字体；找不到指定字体时回退到默认字体。
    
    输入：size、bold。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def read_metrics(path: Path) -> list[dict[str, str]]:
    """中文说明：读取训练过程记录的 metrics.csv，并转换成后续汇总需要的数据结构。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def summarize_run(runs_root: Path, spec: ExperimentSpec) -> dict[str, str] | None:
    """中文说明：读取单次实验的曲线、checkpoint 和可视化资产，形成统一摘要。
    
    输入：runs_root、spec。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    rows = read_metrics(runs_root / spec.run / "metrics.csv")
    if not rows:
        return None
    final = rows[-1]
    best_psnr_row = max(rows, key=lambda row: float(row["val_psnr"]))
    best_ssim_row = max(rows, key=lambda row: float(row["val_ssim"]))
    return {
        "group": spec.group,
        "run": spec.run,
        "label": spec.label,
        "lesson": spec.lesson,
        "final_step": final["step"],
        "final_loss": final["train_loss"],
        "final_psnr": final["val_psnr"],
        "final_ssim": final["val_ssim"],
        "best_psnr": best_psnr_row["val_psnr"],
        "best_psnr_step": best_psnr_row["step"],
        "best_ssim": best_ssim_row["val_ssim"],
        "best_ssim_step": best_ssim_row["step"],
    }


def write_csv(rows: list[dict[str, str]], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 CSV，便于表格查看和后续报告引用。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "week1_core_experiments.csv"
    fieldnames = [
        "group",
        "run",
        "label",
        "lesson",
        "final_step",
        "final_loss",
        "final_psnr",
        "final_ssim",
        "best_psnr",
        "best_psnr_step",
        "best_ssim",
        "best_ssim_step",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_png(rows: list[dict[str, str]], output_dir: Path) -> Path:
    """中文说明：将当前脚本整理出的结果写入磁盘，作为阶段产物或报告素材。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    width = 1760
    header_h = 88
    row_h = 48
    image = Image.new("RGB", (width, header_h + row_h * (len(rows) + 1)), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.text((36, 26), "Week 1 Toy RGB Denoise Core Experiments", fill=(30, 42, 55), font=font(30, True))

    columns = [
        ("Group", 36),
        ("Experiment", 250),
        ("Final PSNR", 690),
        ("Final SSIM", 850),
        ("Best PSNR", 1010),
        ("Best SSIM", 1170),
        ("Lesson", 1330),
    ]
    y = header_h
    draw.rectangle([24, y, width - 24, y + row_h], fill=(226, 232, 240))
    for label, x in columns:
        draw.text((x, y + 13), label, fill=(30, 42, 55), font=font(16, True))

    for idx, row in enumerate(rows, start=1):
        y = header_h + idx * row_h
        fill = (255, 255, 255) if idx % 2 else (242, 246, 250)
        draw.rectangle([24, y, width - 24, y + row_h], fill=fill)
        values = [
            row["group"],
            row["label"],
            f"{float(row['final_psnr']):.2f}",
            f"{float(row['final_ssim']):.4f}",
            f"{float(row['best_psnr']):.2f}@{row['best_psnr_step']}",
            f"{float(row['best_ssim']):.4f}@{row['best_ssim_step']}",
            row["lesson"],
        ]
        for value, (_, x) in zip(values, columns):
            draw.text((x, y + 13), value, fill=(30, 42, 55), font=font(15))

    path = output_dir / "week1_core_experiments.png"
    image.save(path)
    return path


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    runs_root = Path(args.runs_root)
    output_dir = Path(args.output_dir)
    rows = [row for spec in EXPERIMENTS if (row := summarize_run(runs_root, spec))]
    if not rows:
        raise ValueError(f"No Week 1 metrics found under {runs_root}")
    csv_path = write_csv(rows, output_dir)
    png_path = write_png(rows, output_dir)
    print(f"wrote {csv_path}")
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
