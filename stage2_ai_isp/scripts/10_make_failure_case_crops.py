#!/usr/bin/env python3
"""Make zoomed crop sheets from saved noisy/output/clean triplets."""
# 中文说明：从可视化结果中裁剪高误差区域，生成失败案例素材。

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create crop-level failure case sheets.")
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week8_failure_case_crops")
    parser.add_argument("--crop-size", type=int, default=96)
    parser.add_argument("--zoom", type=int, default=3)
    parser.add_argument(
        "--crop-mode",
        choices=["top_error", "center"],
        default="top_error",
        help="Use the highest-error ROI or the historical center crop.",
    )
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


def pick_last_vis(run: Path) -> Path:
    """中文说明：实现 `pick_last_vis` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：run。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    images = sorted((run / "vis").glob("step_*.png"))
    if not images:
        raise FileNotFoundError(f"No vis images in {run / 'vis'}")
    return images[-1]


def split_triplet(path: Path) -> tuple[Image.Image, Image.Image, Image.Image]:
    """中文说明：实现 `split_triplet` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    image = Image.open(path).convert("RGB")
    panel_w = image.width // 3
    return (
        image.crop((0, 0, panel_w, image.height)),
        image.crop((panel_w, 0, panel_w * 2, image.height)),
        image.crop((panel_w * 2, 0, panel_w * 3, image.height)),
    )


def center_crop(image: Image.Image, size: int) -> Image.Image:
    """中文说明：从图像中心裁剪固定大小区域，保证 noisy/clean 对齐且便于快速实验。
    
    输入：image、size。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    left = (image.width - size) // 2
    top = (image.height - size) // 2
    return image.crop((left, top, left + size, top + size))


def top_error_box(
    output: Image.Image, clean: Image.Image, size: int
) -> tuple[int, int, int, int]:
    """Find the size×size window with the largest mean absolute RGB error."""
    # 中文说明：补充说明：`top_error_box` 是当前模块流程中的一个复用步骤。
    out = np.asarray(output, dtype=np.float32) / 255.0
    target = np.asarray(clean, dtype=np.float32) / 255.0
    error = np.mean(np.abs(out - target), axis=2)
    height, width = error.shape
    if size > height or size > width:
        raise ValueError(f"crop_size={size} is larger than image {width}x{height}")
    integral = np.pad(error, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    sums = (
        integral[size:, size:]
        - integral[:-size, size:]
        - integral[size:, :-size]
        + integral[:-size, :-size]
    )
    y, x = np.unravel_index(np.argmax(sums), sums.shape)
    return int(x), int(y), int(x + size), int(y + size)


def error_image(output: Image.Image, clean: Image.Image) -> tuple[Image.Image, float]:
    """中文说明：实现 `error_image` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：output、clean。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    out = np.asarray(output, dtype=np.float32) / 255.0
    tgt = np.asarray(clean, dtype=np.float32) / 255.0
    err = np.mean(np.abs(out - tgt), axis=2)
    mae = float(np.mean(err))
    img = Image.fromarray((np.clip(err * 6.0, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).convert("RGB")
    return img, mae


def labeled(title: str, image: Image.Image, zoom: int) -> Image.Image:
    """中文说明：实现 `labeled` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：title、image、zoom。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    resized = image.resize((image.width * zoom, image.height * zoom), Image.Resampling.NEAREST)
    label_h = 34
    panel = Image.new("RGB", (resized.width, resized.height + label_h), (248, 250, 252))
    draw = ImageDraw.Draw(panel)
    draw.text((8, 8), title, fill=(30, 42, 55), font=font(15, True))
    panel.paste(resized, (0, label_h))
    return panel


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    run_rows = []
    for run_text in args.runs:
        run = Path(run_text)
        vis = pick_last_vis(run)
        noisy, output, clean = split_triplet(vis)
        selected_size = min(args.crop_size, output.width, output.height)
        if args.crop_mode == "top_error":
            box = top_error_box(output, clean, selected_size)
        else:
            left = (output.width - selected_size) // 2
            top = (output.height - selected_size) // 2
            box = (left, top, left + selected_size, top + selected_size)
        noisy_c = noisy.crop(box)
        output_c = output.crop(box)
        clean_c = clean.crop(box)
        error_c, mae = error_image(output_c, clean_c)
        if selected_size != args.crop_size:
            display_size = (args.crop_size, args.crop_size)
            noisy_c = noisy_c.resize(display_size, Image.Resampling.NEAREST)
            output_c = output_c.resize(display_size, Image.Resampling.NEAREST)
            clean_c = clean_c.resize(display_size, Image.Resampling.NEAREST)
            error_c = error_c.resize(display_size, Image.Resampling.NEAREST)
        rows.append(
            (
                run.name,
                vis.name,
                noisy_c,
                output_c,
                clean_c,
                error_c,
                mae,
                box,
                selected_size,
            )
        )
        run_rows.append(
            [
                run.name,
                vis.name,
                args.crop_mode,
                box[0],
                box[1],
                selected_size,
                f"{mae:.6f}",
            ]
        )

    panel_w = args.crop_size * args.zoom
    label_h = 34
    row_h = panel_w + label_h + 44
    sheet = Image.new("RGB", (panel_w * 4, row_h * len(rows)), (238, 242, 246))
    draw = ImageDraw.Draw(sheet)
    for row_idx, (
        run_name,
        vis_name,
        noisy,
        output,
        clean,
        err,
        mae,
        box,
        selected_size,
    ) in enumerate(rows):
        y = row_idx * row_h
        draw.text(
            (10, y + 6),
            f"{run_name} / {vis_name} / {args.crop_mode} "
            f"({box[0]},{box[1]},{selected_size}) / MAE={mae:.6f}",
            fill=(30, 42, 55),
            font=font(18, True),
        )
        panels = [
            labeled("noisy/low", noisy, args.zoom),
            labeled("output", output, args.zoom),
            labeled("clean", clean, args.zoom),
            labeled("error x6", err, args.zoom),
        ]
        for idx, panel in enumerate(panels):
            sheet.paste(panel, (idx * panel_w, y + 44))

    figure_path = output_dir / "failure_case_crop_sheet.png"
    sheet.save(figure_path)
    csv_path = output_dir / "failure_case_crop_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["run", "vis_image", "crop_mode", "x", "y", "roi_size", "crop_mae"]
        )
        writer.writerows(run_rows)
    print(f"wrote {figure_path}")
    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
