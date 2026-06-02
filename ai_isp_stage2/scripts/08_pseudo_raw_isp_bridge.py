#!/usr/bin/env python3
"""Visualize the bridge from sRGB images to pseudo Bayer/RAW concepts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create pseudo RAW/ISP bridge figures.")
    parser.add_argument(
        "--input",
        default="ai_isp_stage2/datasets/sidd_tiny/val/clean/pair_00001.png",
        help="RGB image used as the clean demonstration image.",
    )
    parser.add_argument(
        "--output-dir",
        default="ai_isp_stage2/reports/figures/week6_pseudo_raw_isp",
        help="Directory for generated figures and CSV.",
    )
    parser.add_argument("--crop-size", type=int, default=256)
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


def center_crop(image: Image.Image, size: int) -> Image.Image:
    w, h = image.size
    left = (w - size) // 2
    top = (h - size) // 2
    return image.crop((left, top, left + size, top + size))


def rgb_to_bayer(rgb: np.ndarray) -> np.ndarray:
    """Create an RGGB Bayer mosaic from RGB, using values in [0, 1]."""
    h, w, _ = rgb.shape
    bayer = np.zeros((h, w), dtype=np.float32)
    bayer[0::2, 0::2] = rgb[0::2, 0::2, 0]  # R
    bayer[0::2, 1::2] = rgb[0::2, 1::2, 1]  # Gr
    bayer[1::2, 0::2] = rgb[1::2, 0::2, 1]  # Gb
    bayer[1::2, 1::2] = rgb[1::2, 1::2, 2]  # B
    return bayer


def pack_rggb(bayer: np.ndarray) -> np.ndarray:
    return np.stack(
        [
            bayer[0::2, 0::2],
            bayer[0::2, 1::2],
            bayer[1::2, 0::2],
            bayer[1::2, 1::2],
        ],
        axis=-1,
    )


def nearest_demosaic_from_pack(pack: np.ndarray) -> np.ndarray:
    """Nearest-neighbor demosaic from RGGB pack for concept visualization."""
    r = pack[:, :, 0]
    g = 0.5 * (pack[:, :, 1] + pack[:, :, 2])
    b = pack[:, :, 3]
    rgb_half = np.stack([r, g, b], axis=-1)
    return np.repeat(np.repeat(rgb_half, 2, axis=0), 2, axis=1)


def to_uint8(array: np.ndarray) -> np.ndarray:
    return (np.clip(array, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def heat_gray(array: np.ndarray) -> Image.Image:
    return Image.fromarray(to_uint8(array)).convert("RGB")


def make_labeled_panel(title: str, image: Image.Image, width: int = 256) -> Image.Image:
    ratio = width / image.width
    resized = image.resize((width, int(image.height * ratio)), Image.Resampling.BICUBIC)
    label_h = 42
    panel = Image.new("RGB", (resized.width, resized.height + label_h), (248, 250, 252))
    draw = ImageDraw.Draw(panel)
    draw.text((10, 10), title, fill=(30, 42, 55), font=font(17, True))
    panel.paste(resized, (0, label_h))
    return panel


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image = center_crop(Image.open(args.input).convert("RGB"), args.crop_size)
    rgb = np.asarray(image, dtype=np.float32) / 255.0
    bayer = rgb_to_bayer(rgb)
    pack = pack_rggb(bayer)
    demosaic = nearest_demosaic_from_pack(pack)[: rgb.shape[0], : rgb.shape[1]]
    error = np.mean(np.abs(demosaic - rgb), axis=2)

    channel_names = ["R", "Gr", "Gb", "B"]
    channel_panels = [make_labeled_panel(name, heat_gray(pack[:, :, i]), 128) for i, name in enumerate(channel_names)]
    channel_sheet = Image.new("RGB", (256, channel_panels[0].height * 2), (255, 255, 255))
    for i, panel in enumerate(channel_panels):
        x = (i % 2) * 128
        y = (i // 2) * panel.height
        channel_sheet.paste(panel, (x, y))

    panels = [
        make_labeled_panel("1. clean sRGB", image),
        make_labeled_panel("2. RGGB Bayer mosaic", heat_gray(bayer)),
        make_labeled_panel("3. RAW pack: R/Gr/Gb/B", channel_sheet),
        make_labeled_panel("4. simple demosaic", Image.fromarray(to_uint8(demosaic))),
        make_labeled_panel("5. error x6", heat_gray(error * 6.0)),
    ]
    gap = 12
    total_w = sum(p.width for p in panels) + gap * (len(panels) - 1)
    max_h = max(p.height for p in panels)
    sheet = Image.new("RGB", (total_w, max_h), (238, 242, 246))
    x = 0
    for panel in panels:
        sheet.paste(panel, (x, 0))
        x += panel.width + gap
    figure_path = output_dir / "pseudo_raw_isp_bridge.png"
    sheet.save(figure_path)

    metrics_path = output_dir / "pseudo_raw_metrics.csv"
    mse = float(np.mean((demosaic - rgb) ** 2))
    psnr = float(10.0 * np.log10(1.0 / max(mse, 1e-12)))
    with metrics_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["input", "crop_size", "roundtrip_mse", "roundtrip_psnr"])
        writer.writerow([args.input, args.crop_size, f"{mse:.8f}", f"{psnr:.4f}"])

    print(f"wrote {figure_path}")
    print(f"wrote {metrics_path}")


if __name__ == "__main__":
    main()
