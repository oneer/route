#!/usr/bin/env python3
"""Prepare a small train/val subset from SIDD Small sRGB."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare sidd_tiny from SIDD Small sRGB.")
    parser.add_argument(
        "--source-root",
        default="stage2_ai_isp/datasets/downloads/SIDD_Small_sRGB_Only/SIDD_Small_sRGB_Only/Data",
        help="SIDD Small Data directory containing scene folders.",
    )
    parser.add_argument(
        "--output-dir",
        default="stage2_ai_isp/datasets/sidd_tiny",
        help="Output root with train/val noisy/clean folders.",
    )
    parser.add_argument("--train-count", type=int, default=80)
    parser.add_argument("--val-count", type=int, default=20)
    parser.add_argument("--crop-size", type=int, default=512)
    return parser.parse_args()


def center_crop(image: Image.Image, size: int) -> Image.Image:
    width, height = image.size
    if width < size or height < size:
        raise ValueError(f"Image is smaller than crop size {size}: {width}x{height}")
    left = (width - size) // 2
    top = (height - size) // 2
    return image.crop((left, top, left + size, top + size))


def find_pairs(source_root: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for scene_dir in sorted(path for path in source_root.iterdir() if path.is_dir()):
        noisy = scene_dir / "NOISY_SRGB_010.PNG"
        clean = scene_dir / "GT_SRGB_010.PNG"
        if noisy.exists() and clean.exists():
            pairs.append((noisy, clean))
    return pairs


def save_pair(noisy_path: Path, clean_path: Path, noisy_out: Path, clean_out: Path, crop_size: int) -> None:
    noisy = Image.open(noisy_path).convert("RGB")
    clean = Image.open(clean_path).convert("RGB")
    if noisy.size != clean.size:
        raise ValueError(f"Size mismatch: {noisy_path} vs {clean_path}")

    noisy = center_crop(noisy, crop_size)
    clean = center_crop(clean, crop_size)
    noisy_out.parent.mkdir(parents=True, exist_ok=True)
    clean_out.parent.mkdir(parents=True, exist_ok=True)
    noisy.save(noisy_out)
    clean.save(clean_out)


def main() -> None:
    args = parse_args()
    source_root = Path(args.source_root)
    output_root = Path(args.output_dir)
    pairs = find_pairs(source_root)
    total = args.train_count + args.val_count
    if len(pairs) < total:
        raise ValueError(f"Need {total} pairs, found {len(pairs)} in {source_root}")

    manifest_rows = []
    for index, (noisy_path, clean_path) in enumerate(pairs[:total], start=1):
        split = "train" if index <= args.train_count else "val"
        split_index = index if split == "train" else index - args.train_count
        name = f"pair_{split_index:05d}.png"
        noisy_out = output_root / split / "noisy" / name
        clean_out = output_root / split / "clean" / name
        save_pair(noisy_path, clean_path, noisy_out, clean_out, args.crop_size)
        manifest_rows.append(
            {
                "split": split,
                "name": name,
                "source_scene": noisy_path.parent.name,
                "source_noisy": noisy_path.as_posix(),
                "source_clean": clean_path.as_posix(),
            }
        )

    output_root.mkdir(parents=True, exist_ok=True)
    with open(output_root / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["split", "name", "source_scene", "source_noisy", "source_clean"]
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"found_pairs={len(pairs)}")
    print(f"wrote train={args.train_count} val={args.val_count} crop_size={args.crop_size}")
    print(f"output_dir={output_root}")


if __name__ == "__main__":
    main()
