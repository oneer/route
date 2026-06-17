#!/usr/bin/env python3
"""Preview the pseudo RGGB pack used by the Stage 2 upgrade path."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.data.paired_image_dataset import _load_rgb_tensor
from ai_isp.data.pseudo_raw import rggb_pack_to_rgb_preview, rgb_to_rggb_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview pseudo RAW RGGB packs.")
    parser.add_argument(
        "--input-dir",
        default="stage2_ai_isp/datasets/sidd_tiny/val/clean",
        help="RGB image directory to preview.",
    )
    parser.add_argument(
        "--output-dir",
        default="stage2_ai_isp/reports/figures/week10_pseudo_raw_dataset",
        help="Directory for preview figures.",
    )
    parser.add_argument("--max-samples", type=int, default=6)
    return parser.parse_args()


def to_image(tensor) -> Image.Image:
    array = tensor.detach().clamp(0, 1).permute(1, 2, 0).numpy()
    return Image.fromarray((array * 255.0 + 0.5).astype(np.uint8))


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    images = [
        path
        for path in sorted(input_dir.iterdir())
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    ][: args.max_samples]
    if not images:
        raise ValueError(f"No preview images found in {input_dir}")

    rows = []
    cell_w, cell_h = 256, 300
    for path in images:
        rgb = _load_rgb_tensor(path)
        _, height, width = rgb.shape
        rgb = rgb[:, : height - height % 2, : width - width % 2]
        pack = rgb_to_rggb_pack(rgb)
        preview = rggb_pack_to_rgb_preview(pack)

        left = to_image(rgb).resize((cell_w, cell_w), Image.Resampling.BICUBIC)
        right = to_image(preview).resize((cell_w, cell_w), Image.Resampling.NEAREST)
        row = Image.new("RGB", (cell_w * 2, cell_h), "white")
        row.paste(left, (0, 32))
        row.paste(right, (cell_w, 32))
        draw = ImageDraw.Draw(row)
        draw.text((8, 8), f"{path.name} RGB", fill=(20, 20, 20))
        draw.text((cell_w + 8, 8), "RGGB preview", fill=(20, 20, 20))
        draw.text((cell_w + 8, cell_w + 40), f"pack shape: {tuple(pack.shape)}", fill=(20, 20, 20))
        rows.append(row)

    sheet = Image.new("RGB", (cell_w * 2, cell_h * len(rows)), "white")
    for idx, row in enumerate(rows):
        sheet.paste(row, (0, idx * cell_h))

    out_path = output_dir / "pseudo_raw_preview.png"
    sheet.save(out_path)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
