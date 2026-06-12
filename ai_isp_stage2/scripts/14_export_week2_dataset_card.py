#!/usr/bin/env python3
"""Export a small dataset card for the Stage 2 paired RGB subset."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import statistics

import numpy as np
from PIL import Image


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Week 2 paired RGB dataset card.")
    parser.add_argument("--dataset-root", default="ai_isp_stage2/datasets/sidd_tiny")
    parser.add_argument("--output-dir", default="ai_isp_stage2/reports/figures/week2_dataset_card")
    parser.add_argument("--name", default="SIDD tiny paired RGB")
    return parser.parse_args()


def list_images(root: Path) -> list[Path]:
    return sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def image_to_float(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    return np.asarray(image, dtype=np.float32) / 255.0


def psnr(noisy: np.ndarray, clean: np.ndarray) -> float:
    mse = float(np.mean((noisy - clean) ** 2))
    if mse <= 0:
        return float("inf")
    return 10.0 * math.log10(1.0 / mse)


def split_summary(dataset_root: Path, split: str) -> dict[str, object]:
    noisy_dir = dataset_root / split / "noisy"
    clean_dir = dataset_root / split / "clean"
    noisy_files = list_images(noisy_dir)
    clean_files = list_images(clean_dir)
    noisy_names = {path.name for path in noisy_files}
    clean_names = {path.name for path in clean_files}
    matched_names = sorted(noisy_names & clean_names)

    sizes: list[tuple[int, int]] = []
    psnr_values: list[float] = []
    mean_abs_values: list[float] = []
    for name in matched_names:
        noisy_path = noisy_dir / name
        clean_path = clean_dir / name
        with Image.open(noisy_path) as noisy_image, Image.open(clean_path) as clean_image:
            sizes.append(noisy_image.size)
            if noisy_image.size != clean_image.size:
                continue
        noisy = image_to_float(noisy_path)
        clean = image_to_float(clean_path)
        psnr_values.append(psnr(noisy, clean))
        mean_abs_values.append(float(np.mean(np.abs(noisy - clean))))

    unique_sizes = sorted(set(sizes))
    return {
        "split": split,
        "noisy_count": len(noisy_files),
        "clean_count": len(clean_files),
        "matched_count": len(matched_names),
        "unmatched_noisy": len(noisy_names - clean_names),
        "unmatched_clean": len(clean_names - noisy_names),
        "unique_sizes": unique_sizes,
        "mean_pair_psnr": statistics.fmean(psnr_values) if psnr_values else float("nan"),
        "mean_abs_diff": statistics.fmean(mean_abs_values) if mean_abs_values else float("nan"),
    }


def write_csv(summaries: list[dict[str, object]], output_dir: Path) -> Path:
    path = output_dir / "week2_dataset_card.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "split",
                "noisy_count",
                "clean_count",
                "matched_count",
                "unmatched_noisy",
                "unmatched_clean",
                "unique_sizes",
                "mean_pair_psnr",
                "mean_abs_diff",
            ]
        )
        for row in summaries:
            writer.writerow(
                [
                    row["split"],
                    row["noisy_count"],
                    row["clean_count"],
                    row["matched_count"],
                    row["unmatched_noisy"],
                    row["unmatched_clean"],
                    ";".join(f"{w}x{h}" for w, h in row["unique_sizes"]),
                    f"{row['mean_pair_psnr']:.4f}",
                    f"{row['mean_abs_diff']:.6f}",
                ]
            )
    return path


def write_markdown(
    name: str,
    dataset_root: Path,
    manifest_rows: list[dict[str, str]],
    summaries: list[dict[str, object]],
    output_dir: Path,
) -> Path:
    path = output_dir / "week2_dataset_card.md"
    scene_count = len({row.get("source_scene", "") for row in manifest_rows if row.get("source_scene")})
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Week 2 Dataset Card: {name}\n\n")
        f.write("## Purpose\n\n")
        f.write(
            "This subset verifies the real paired RGB data path before larger AI-ISP experiments. "
            "It is used to check noisy/clean pairing, image size consistency, noisy-input baseline, "
            "and small-step denoise training.\n\n"
        )
        f.write("## Source\n\n")
        f.write(f"- Dataset root: `{dataset_root.as_posix()}`\n")
        f.write("- Source dataset: SIDD Small sRGB, cropped into a tiny local subset.\n")
        f.write(f"- Manifest rows: {len(manifest_rows)}\n")
        f.write(f"- Unique source scenes: {scene_count}\n\n")
        f.write("## Split Summary\n\n")
        f.write("| Split | Noisy | Clean | Matched | Unmatched noisy | Unmatched clean | Sizes | Mean pair PSNR | Mean abs diff |\n")
        f.write("|---|---:|---:|---:|---:|---:|---|---:|---:|\n")
        for row in summaries:
            sizes = ", ".join(f"{w}x{h}" for w, h in row["unique_sizes"])
            f.write(
                f"| {row['split']} | {row['noisy_count']} | {row['clean_count']} | "
                f"{row['matched_count']} | {row['unmatched_noisy']} | {row['unmatched_clean']} | "
                f"{sizes} | {row['mean_pair_psnr']:.4f} | {row['mean_abs_diff']:.6f} |\n"
            )
        f.write("\n## Checks\n\n")
        f.write("- Noisy and clean files should have identical names inside each split.\n")
        f.write("- Matched count should equal noisy and clean count.\n")
        f.write("- Unmatched noisy / clean counts should be zero.\n")
        f.write("- Image sizes should be consistent within each split.\n")
        f.write("- Mean pair PSNR is a full-crop data sanity metric, not a trained model result.\n")
    return path


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = read_manifest(dataset_root / "manifest.csv")
    summaries = [split_summary(dataset_root, split) for split in ["train", "val"]]
    csv_path = write_csv(summaries, output_dir)
    md_path = write_markdown(args.name, dataset_root, manifest_rows, summaries, output_dir)

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    for summary in summaries:
        print(
            f"{summary['split']}: matched={summary['matched_count']} "
            f"sizes={summary['unique_sizes']} mean_pair_psnr={summary['mean_pair_psnr']:.4f} "
            f"mean_abs_diff={summary['mean_abs_diff']:.6f}"
        )


if __name__ == "__main__":
    main()
