"""Inspect paired noisy/clean image folders and create a visual manifest."""
# 中文说明：检查配对数据集文件数量、尺寸和可视化网格。

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--noisy-dir", required=True)
    parser.add_argument("--clean-dir", required=True)
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week2_dataset_inspection")
    parser.add_argument("--max-samples", type=int, default=8)
    return parser.parse_args()


def list_images(root: Path) -> dict[str, Path]:
    """中文说明：枚举目录中的图片文件，并按文件名排序保证结果稳定。
    
    输入：root。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    return {
        path.name: path
        for path in sorted(root.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    }


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


def write_manifest(pairs: list[tuple[str, Path, Path]], output_dir: Path) -> Path:
    """中文说明：将当前脚本整理出的结果写入磁盘，作为阶段产物或报告素材。
    
    输入：pairs、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    path = output_dir / "paired_manifest.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "noisy_path", "clean_path", "noisy_size", "clean_size", "same_size"])
        for name, noisy_path, clean_path in pairs:
            noisy_size = Image.open(noisy_path).size
            clean_size = Image.open(clean_path).size
            writer.writerow([name, noisy_path, clean_path, noisy_size, clean_size, noisy_size == clean_size])
    return path


def make_grid(pairs: list[tuple[str, Path, Path]], output_dir: Path, max_samples: int) -> Path:
    """中文说明：构造后续流程需要的对象或可视化产物，把零散配置集中成可复用结果。
    
    输入：pairs、output_dir、max_samples。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    samples = pairs[:max_samples]
    thumb_w, thumb_h = 220, 160
    label_h = 54
    row_h = thumb_h + label_h
    width = thumb_w * 2
    height = row_h * len(samples)
    image = Image.new("RGB", (width, height), (250, 252, 253))
    draw = ImageDraw.Draw(image)

    for idx, (name, noisy_path, clean_path) in enumerate(samples):
        y = idx * row_h
        draw.text((10, y + 8), f"{name} noisy", fill=(30, 42, 55), font=font(15, True))
        draw.text((thumb_w + 10, y + 8), f"{name} clean", fill=(30, 42, 55), font=font(15, True))
        for col, path in enumerate([noisy_path, clean_path]):
            tile = Image.open(path).convert("RGB")
            tile.thumbnail((thumb_w - 12, thumb_h - 12), Image.BICUBIC)
            x = col * thumb_w + (thumb_w - tile.width) // 2
            image.paste(tile, (x, y + label_h))

    path = output_dir / "paired_samples_grid.png"
    image.save(path)
    return path


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    noisy_dir = Path(args.noisy_dir)
    clean_dir = Path(args.clean_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    noisy = list_images(noisy_dir)
    clean = list_images(clean_dir)
    names = sorted(set(noisy) & set(clean))
    if not names:
        raise ValueError(f"No matched image names in {noisy_dir} and {clean_dir}")
    pairs = [(name, noisy[name], clean[name]) for name in names]

    manifest = write_manifest(pairs, output_dir)
    grid = make_grid(pairs, output_dir, args.max_samples)
    print(f"matched_pairs={len(pairs)}")
    print(f"wrote {manifest}")
    print(f"wrote {grid}")


if __name__ == "__main__":
    main()
