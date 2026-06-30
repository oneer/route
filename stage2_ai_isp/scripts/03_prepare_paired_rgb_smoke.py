#!/usr/bin/env python3
"""Create a tiny noisy/clean paired RGB dataset for pipeline smoke tests."""
# 中文说明：生成极小配对 RGB smoke 数据集，用来快速验证真实图片路径。

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Prepare a paired RGB smoke dataset.")
    parser.add_argument(
        "--source-dir",
        default="stage1_soft_isp/reports/figures/fivek_candidates",
        help="Directory containing clean RGB images.",
    )
    parser.add_argument(
        "--output-dir",
        default="stage2_ai_isp/runs/paired_rgb_smoke",
        help="Output directory with clean/noisy subfolders.",
    )
    parser.add_argument("--count", type=int, default=12, help="Number of pairs to write.")
    parser.add_argument("--size", type=int, default=256, help="Resize short side then center-crop.")
    parser.add_argument("--sigma", type=float, default=0.08, help="Gaussian noise sigma.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def center_crop(image: Image.Image, size: int) -> Image.Image:
    """中文说明：从图像中心裁剪固定大小区域，保证 noisy/clean 对齐且便于快速实验。
    
    输入：image、size。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    width, height = image.size
    scale = size / min(width, height)
    resized = image.resize((round(width * scale), round(height * scale)), Image.Resampling.BICUBIC)
    left = (resized.width - size) // 2
    top = (resized.height - size) // 2
    return resized.crop((left, top, left + size, top + size))


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    clean_dir = output_dir / "clean"
    noisy_dir = output_dir / "noisy"
    clean_dir.mkdir(parents=True, exist_ok=True)
    noisy_dir.mkdir(parents=True, exist_ok=True)

    image_paths = [
        path
        for path in sorted(source_dir.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    ][: args.count]
    if not image_paths:
        raise ValueError(f"No source images found in {source_dir}")

    rng = np.random.default_rng(args.seed)
    for index, path in enumerate(image_paths, start=1):
        clean = center_crop(Image.open(path).convert("RGB"), args.size)
        clean_arr = np.asarray(clean, dtype=np.float32) / 255.0
        noisy_arr = clean_arr + rng.normal(0.0, args.sigma, clean_arr.shape).astype(np.float32)
        noisy_arr = np.clip(noisy_arr, 0.0, 1.0)

        name = f"pair_{index:03d}.png"
        clean.save(clean_dir / name)
        Image.fromarray((noisy_arr * 255.0 + 0.5).astype(np.uint8)).save(noisy_dir / name)

    print(f"wrote {len(image_paths)} pairs to {output_dir}")


if __name__ == "__main__":
    main()
