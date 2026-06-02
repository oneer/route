#!/usr/bin/env python3
"""Export a compact Stage 2 leaderboard from generated metric summaries."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Stage 2 final summary table and figure.")
    parser.add_argument(
        "--metric-csvs",
        nargs="+",
        default=[
            "ai_isp_stage2/reports/figures/week4_sidd_tiny_standard_eval/metrics_summary.csv",
            "ai_isp_stage2/reports/figures/week7_low_light_eval/metrics_summary.csv",
        ],
    )
    parser.add_argument("--output-dir", default="ai_isp_stage2/reports/figures/week9_stage2_summary")
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
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


def read_rows(paths: list[str]) -> list[dict[str, str]]:
    rows = []
    for path_text in paths:
        path = Path(path_text)
        if not path.exists():
            continue
        task = path.parent.name
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                row = dict(row)
                row["task"] = task
                rows.append(row)
    return rows


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.metric_csvs)
    if not rows:
        raise ValueError("No metric rows found.")

    out_csv = output_dir / "stage2_leaderboard.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["task", "run", "best_psnr", "best_ssim", "best_psnr_step", "best_ssim_step"])
        for row in rows:
            writer.writerow(
                [
                    row["task"],
                    row["run"],
                    row["best_psnr"],
                    row["best_ssim"],
                    row["best_psnr_step"],
                    row["best_ssim_step"],
                ]
            )

    width = 1500
    row_h = 48
    header_h = 86
    image = Image.new("RGB", (width, header_h + row_h * (len(rows) + 1)), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.text((36, 28), "Stage 2 Final Leaderboard", fill=(30, 42, 55), font=font(30, True))
    columns = [("Task", 36), ("Run", 310), ("Best PSNR", 900), ("Best SSIM", 1080), ("Step", 1260)]
    y = header_h
    draw.rectangle([24, y, width - 24, y + row_h], fill=(226, 232, 240))
    for label, x in columns:
        draw.text((x, y + 13), label, fill=(30, 42, 55), font=font(16, True))
    for idx, row in enumerate(rows, start=1):
        y = header_h + idx * row_h
        fill = (255, 255, 255) if idx % 2 else (242, 246, 250)
        draw.rectangle([24, y, width - 24, y + row_h], fill=fill)
        draw.text((36, y + 13), row["task"], fill=(30, 42, 55), font=font(15))
        draw.text((310, y + 13), row["run"], fill=(30, 42, 55), font=font(15))
        draw.text((900, y + 13), row["best_psnr"], fill=(30, 42, 55), font=font(15, True))
        draw.text((1080, y + 13), row["best_ssim"], fill=(30, 42, 55), font=font(15, True))
        draw.text((1260, y + 13), f"{row['best_psnr_step']} / {row['best_ssim_step']}", fill=(30, 42, 55), font=font(15))

    out_png = output_dir / "stage2_leaderboard.png"
    image.save(out_png)
    print(f"wrote {out_csv}")
    print(f"wrote {out_png}")


if __name__ == "__main__":
    main()
