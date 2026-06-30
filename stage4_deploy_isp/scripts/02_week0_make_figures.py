"""Week 0.5：把基线 CSV 和三联图整理成报告图片。

脚本不重新跑模型，只读取 01 脚本产出的指标和 triplet 图片，生成 PSNR/SSIM
柱状图以及 contact sheet，方便在报告里展示固定集的整体表现。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deploy.common import project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make Week 0.5 report figures.")
    parser.add_argument("--output-dir", default="outputs/week0_baseline")
    parser.add_argument("--max-contact-sheet", type=int, default=6)
    return parser.parse_args()


def read_metrics(path: Path) -> list[dict[str, str]]:
    # CSV 中的值先保持字符串，绘图时再按列转换成 float。
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_metric_bars(rows: list[dict[str, str]], figures_dir: Path) -> None:
    # 同一张图并排展示 noisy 与模型输出，直接体现模型带来的指标提升。
    ids = [r["id"].replace("pair_", "") for r in rows]
    noisy_psnr = np.asarray([float(r["noisy_psnr"]) for r in rows])
    model_psnr = np.asarray([float(r["model_psnr"]) for r in rows])
    noisy_ssim = np.asarray([float(r["noisy_ssim"]) for r in rows])
    model_ssim = np.asarray([float(r["model_ssim"]) for r in rows])

    x = np.arange(len(ids))
    width = 0.38

    plt.figure(figsize=(12, 4.5))
    plt.bar(x - width / 2, noisy_psnr, width, label="Noisy input", color="#7a869a")
    plt.bar(x + width / 2, model_psnr, width, label="PyTorch output", color="#2f7d5c")
    plt.xticks(x, ids, rotation=45, ha="right")
    plt.ylabel("PSNR (dB)")
    plt.title("Week 0.5 fixed-set PSNR")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_dir / "week0_psnr_comparison.png", dpi=160)
    plt.close()

    plt.figure(figsize=(12, 4.5))
    plt.bar(x - width / 2, noisy_ssim, width, label="Noisy input", color="#7a869a")
    plt.bar(x + width / 2, model_ssim, width, label="PyTorch output", color="#2f7d5c")
    plt.xticks(x, ids, rotation=45, ha="right")
    plt.ylabel("Global SSIM")
    plt.title("Week 0.5 fixed-set SSIM")
    plt.ylim(0.65, 1.01)
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_dir / "week0_ssim_comparison.png", dpi=160)
    plt.close()


def make_contact_sheet(triplet_dir: Path, figures_dir: Path, max_images: int) -> None:
    # contact sheet 只取前几张代表样本，避免报告图片过长。
    paths = sorted(triplet_dir.glob("*_triplet.png"))[:max_images]
    if not paths:
        return
    images = [Image.open(p).convert("RGB") for p in paths]
    target_width = 1200
    resized = []
    for image in images:
        # 统一宽度，保留原始宽高比，让不同样本在一张长图里对齐。
        scale = target_width / image.width
        resized.append(image.resize((target_width, int(image.height * scale))))
    gap = 16
    total_h = sum(im.height for im in resized) + gap * (len(resized) - 1)
    sheet = Image.new("RGB", (target_width, total_h), "white")
    y = 0
    for image in resized:
        sheet.paste(image, (0, y))
        y += image.height + gap
    sheet.save(figures_dir / "week0_triplet_contact_sheet.png")


def main() -> None:
    args = parse_args()
    root = project_root()
    out_dir = root / args.output_dir
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    # 这里只做可视化汇总，不改变 week0_metrics.csv 的任何数值。
    rows = read_metrics(out_dir / "week0_metrics.csv")
    plot_metric_bars(rows, figures_dir)
    make_contact_sheet(out_dir / "triplets", figures_dir, args.max_contact_sheet)
    print(f"Wrote figures to {figures_dir}")


if __name__ == "__main__":
    main()
