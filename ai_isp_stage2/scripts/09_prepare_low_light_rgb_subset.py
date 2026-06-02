#!/usr/bin/env python3
"""Create a deterministic low-light RGB enhancement subset from clean images."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare low-light RGB pairs from clean SIDD crops.")
    parser.add_argument("--source-root", default="ai_isp_stage2/datasets/sidd_tiny")
    parser.add_argument("--output-dir", default="ai_isp_stage2/datasets/sidd_low_light_tiny")
    parser.add_argument("--figure-dir", default="ai_isp_stage2/reports/figures/week7_low_light_rgb")
    parser.add_argument("--exposure", type=float, default=0.28)
    parser.add_argument("--read-noise", type=float, default=0.015)
    parser.add_argument("--shot-noise", type=float, default=0.025)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--max-figure-samples", type=int, default=8)
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


def list_pngs(path: Path) -> list[Path]:
    return sorted(path.glob("*.png"))


def degrade(clean: np.ndarray, rng: np.random.Generator, exposure: float, read_noise: float, shot_noise: float) -> np.ndarray:
    linear = np.clip(clean, 0.0, 1.0) ** 2.2
    low_linear = linear * exposure
    noise_std = read_noise + shot_noise * np.sqrt(np.clip(low_linear, 0.0, 1.0))
    noisy = low_linear + rng.normal(0.0, noise_std, size=low_linear.shape)
    srgb = np.clip(noisy, 0.0, 1.0) ** (1.0 / 2.2)
    return srgb.astype(np.float32)


def to_uint8(array: np.ndarray) -> np.ndarray:
    return (np.clip(array, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def make_grid(pairs: list[tuple[Path, Path]], output_path: Path) -> None:
    thumb_w = 160
    label_h = 30
    row_h = 2 * thumb_w + label_h
    cols = len(pairs)
    sheet = Image.new("RGB", (cols * thumb_w, row_h), (248, 250, 252))
    draw = ImageDraw.Draw(sheet)
    for idx, (low_path, clean_path) in enumerate(pairs):
        low = Image.open(low_path).convert("RGB").resize((thumb_w, thumb_w), Image.Resampling.BICUBIC)
        clean = Image.open(clean_path).convert("RGB").resize((thumb_w, thumb_w), Image.Resampling.BICUBIC)
        x = idx * thumb_w
        draw.text((x + 8, 6), low_path.name, fill=(30, 42, 55), font=font(13, True))
        sheet.paste(low, (x, label_h))
        sheet.paste(clean, (x, label_h + thumb_w))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def main() -> None:
    args = parse_args()
    source_root = Path(args.source_root)
    output_root = Path(args.output_dir)
    figure_dir = Path(args.figure_dir)
    rows = []
    figure_pairs: list[tuple[Path, Path]] = []

    for split in ["train", "val"]:
        clean_paths = list_pngs(source_root / split / "clean")
        for index, clean_path in enumerate(clean_paths, start=1):
            rng = np.random.default_rng(args.seed + (0 if split == "train" else 10000) + index)
            clean = np.asarray(Image.open(clean_path).convert("RGB"), dtype=np.float32) / 255.0
            low = degrade(clean, rng, args.exposure, args.read_noise, args.shot_noise)
            name = clean_path.name
            low_out = output_root / split / "noisy" / name
            clean_out = output_root / split / "clean" / name
            low_out.parent.mkdir(parents=True, exist_ok=True)
            clean_out.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(to_uint8(low)).save(low_out)
            Image.fromarray(to_uint8(clean)).save(clean_out)
            rows.append([split, name, clean_path.as_posix(), low_out.as_posix(), clean_out.as_posix()])
            if split == "val" and len(figure_pairs) < args.max_figure_samples:
                figure_pairs.append((low_out, clean_out))

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "name", "source_clean", "low", "clean"])
        writer.writerows(rows)

    make_grid(figure_pairs, figure_dir / "low_light_pairs_grid.png")
    print(f"wrote {manifest_path}")
    print(f"wrote {figure_dir / 'low_light_pairs_grid.png'}")


if __name__ == "__main__":
    main()
