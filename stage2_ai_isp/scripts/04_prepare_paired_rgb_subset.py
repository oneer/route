#!/usr/bin/env python3
"""Normalize paired RGB denoise images into train/val noisy-clean folders."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

from PIL import Image


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a small paired RGB denoise subset from noisy/clean folders."
    )
    parser.add_argument("--source-noisy-dir", required=True, help="Source noisy image root.")
    parser.add_argument("--source-clean-dir", required=True, help="Source clean/GT image root.")
    parser.add_argument(
        "--output-dir",
        default="stage2_ai_isp/datasets/sidd_tiny",
        help="Output root containing train/val noisy/clean folders.",
    )
    parser.add_argument("--train-count", type=int, default=80, help="Training pairs to write.")
    parser.add_argument("--val-count", type=int, default=20, help="Validation pairs to write.")
    parser.add_argument(
        "--size",
        type=int,
        default=0,
        help="Optional center-crop size after resizing short side. 0 keeps original size.",
    )
    return parser.parse_args()


def list_images(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    ]


def pair_key(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    key = rel.as_posix().lower()
    key = re.sub(r"\b(noisy|clean|gt|srgb|rgb)\b", "", key)
    key = re.sub(r"(^|[_\-.])(noisy|clean|gt|srgb|rgb)([_\-.]|$)", r"\1", key)
    return re.sub(r"[^a-z0-9]+", "", key)


def center_crop(image: Image.Image, size: int) -> Image.Image:
    width, height = image.size
    scale = size / min(width, height)
    resized = image.resize((round(width * scale), round(height * scale)), Image.Resampling.BICUBIC)
    left = (resized.width - size) // 2
    top = (resized.height - size) // 2
    return resized.crop((left, top, left + size, top + size))


def save_pair(noisy_path: Path, clean_path: Path, noisy_out: Path, clean_out: Path, size: int) -> None:
    noisy = Image.open(noisy_path).convert("RGB")
    clean = Image.open(clean_path).convert("RGB")
    if size > 0:
        noisy = center_crop(noisy, size)
        clean = center_crop(clean, size)
    elif noisy.size != clean.size:
        raise ValueError(f"Size mismatch: {noisy_path} vs {clean_path}")

    noisy_out.parent.mkdir(parents=True, exist_ok=True)
    clean_out.parent.mkdir(parents=True, exist_ok=True)
    noisy.save(noisy_out)
    clean.save(clean_out)


def main() -> None:
    args = parse_args()
    noisy_root = Path(args.source_noisy_dir)
    clean_root = Path(args.source_clean_dir)
    output_root = Path(args.output_dir)

    noisy_by_key = {pair_key(path, noisy_root): path for path in list_images(noisy_root)}
    clean_by_key = {pair_key(path, clean_root): path for path in list_images(clean_root)}
    keys = sorted(set(noisy_by_key) & set(clean_by_key))
    total = args.train_count + args.val_count
    if len(keys) < total:
        raise ValueError(f"Need {total} pairs, found {len(keys)} matched pairs.")

    for index, key in enumerate(keys[:total], start=1):
        split = "train" if index <= args.train_count else "val"
        split_index = index if split == "train" else index - args.train_count
        name = f"pair_{split_index:05d}.png"
        save_pair(
            noisy_by_key[key],
            clean_by_key[key],
            output_root / split / "noisy" / name,
            output_root / split / "clean" / name,
            args.size,
        )

    print(f"wrote {args.train_count} train pairs and {args.val_count} val pairs to {output_root}")


if __name__ == "__main__":
    main()
