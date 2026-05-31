#!/usr/bin/env python3
"""Create a tiny noisy/clean paired RGB dataset for pipeline smoke tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a paired RGB smoke dataset.")
    parser.add_argument(
        "--source-dir",
        default="soft_isp_stage1/reports/figures/fivek_candidates",
        help="Directory containing clean RGB images.",
    )
    parser.add_argument(
        "--output-dir",
        default="ai_isp_stage2/runs/paired_rgb_smoke",
        help="Output directory with clean/noisy subfolders.",
    )
    parser.add_argument("--count", type=int, default=12, help="Number of pairs to write.")
    parser.add_argument("--size", type=int, default=256, help="Resize short side then center-crop.")
    parser.add_argument("--sigma", type=float, default=0.08, help="Gaussian noise sigma.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def center_crop(image: Image.Image, size: int) -> Image.Image:
    width, height = image.size
    scale = size / min(width, height)
    resized = image.resize((round(width * scale), round(height * scale)), Image.Resampling.BICUBIC)
    left = (resized.width - size) // 2
    top = (resized.height - size) // 2
    return resized.crop((left, top, left + size, top + size))


def main() -> None:
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
