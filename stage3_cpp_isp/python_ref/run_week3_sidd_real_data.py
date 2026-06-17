from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from denoise_ref import bilateral_filter
from noise_model_ref import gaussian_filter, psnr


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT.parent / "stage2_ai_isp" / "datasets" / "sidd_tiny"
OUTPUT_ROOT = ROOT / "data" / "real_cases" / "sidd_tiny"
FIGURE_DIR = ROOT / "reports" / "figures" / "week3_sidd_real"
REPORT_PATH = ROOT / "reports" / "week3_sidd_real_data_bridge.md"


def read_png(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    return np.asarray(image, dtype=np.float32) / 255.0


def write_png(path: Path, image: np.ndarray) -> None:
    array = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(array, mode="RGB").save(path)


def crop_center(image: np.ndarray, size: int) -> np.ndarray:
    h, w = image.shape[:2]
    y0 = max((h - size) // 2, 0)
    x0 = max((w - size) // 2, 0)
    return image[y0 : y0 + size, x0 : x0 + size]


def rgb_gaussian(image: np.ndarray, radius: int = 2, sigma: float = 1.1) -> np.ndarray:
    channels = [gaussian_filter(image[..., c], radius=radius, sigma=sigma) for c in range(3)]
    return np.stack(channels, axis=-1)


def rgb_bilateral(
    image: np.ndarray,
    radius: int = 2,
    sigma_spatial: float = 1.5,
    sigma_range: float = 0.07,
) -> np.ndarray:
    channels = [
        bilateral_filter(
            image[..., c],
            radius=radius,
            sigma_spatial=sigma_spatial,
            sigma_range=sigma_range,
        )
        for c in range(3)
    ]
    return np.stack(channels, axis=-1)


def mean_abs_error(reference: np.ndarray, image: np.ndarray) -> float:
    return float(np.mean(np.abs(reference - image)))


def residual_std(reference: np.ndarray, image: np.ndarray) -> float:
    return float(np.std(image - reference))


def load_pairs(dataset_root: Path, split: str) -> list[tuple[str, Path, Path]]:
    noisy_dir = dataset_root / split / "noisy"
    clean_dir = dataset_root / split / "clean"
    pairs: list[tuple[str, Path, Path]] = []
    for noisy_path in sorted(noisy_dir.glob("*.png")):
        clean_path = clean_dir / noisy_path.name
        if clean_path.exists():
            pairs.append((noisy_path.name, noisy_path, clean_path))
    return pairs


def write_stage3_manifest(dataset_root: Path, rows: list[dict[str, str]]) -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_ROOT / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "name",
                "noisy_path",
                "clean_path",
                "source",
                "note",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    dataset_card = OUTPUT_ROOT / "README.md"
    dataset_card.write_text(
        "\n".join(
            [
                "# SIDD Tiny sRGB Bridge",
                "",
                "This directory intentionally stores metadata instead of copying image data.",
                f"- Source dataset: `{dataset_root.as_posix()}`",
                f"- Manifest: `{manifest_path.as_posix()}`",
                "- Image type: paired noisy / GT sRGB PNG crops",
                "- ISP meaning: useful for real-image denoise behavior, not a replacement for RAW sensor data.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest_path


def save_pair_grid(samples: list[dict[str, object]], path: Path) -> None:
    fig, axes = plt.subplots(len(samples), 5, figsize=(13, 3.0 * len(samples)))
    if len(samples) == 1:
        axes = np.expand_dims(axes, axis=0)

    titles = ["noisy", "GT", "Gaussian", "bilateral", "bilateral error x8"]
    for row_ax, sample in zip(axes, samples):
        images = [
            sample["noisy"],
            sample["clean"],
            sample["gaussian"],
            sample["bilateral"],
            np.abs(sample["bilateral"] - sample["clean"]) * 8.0,
        ]
        for ax, title, image in zip(row_ax, titles, images):
            ax.imshow(np.clip(image, 0.0, 1.0))
            ax.set_title(title, fontsize=9)
            ax.axis("off")

    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def write_report(
    manifest_path: Path,
    pair_count: int,
    metrics_path: Path,
    figure_path: Path,
    rows: list[dict[str, object]],
) -> None:
    best_row = max(rows, key=lambda row: float(row["bilateral_psnr"]))
    mean_noisy = float(np.mean([float(row["noisy_psnr"]) for row in rows]))
    mean_gauss = float(np.mean([float(row["gaussian_psnr"]) for row in rows]))
    mean_bilat = float(np.mean([float(row["bilateral_psnr"]) for row in rows]))

    REPORT_PATH.write_text(
        "\n".join(
            [
                "# Week 3.5: SIDD Tiny sRGB Real Data Bridge",
                "",
                "## Goal",
                "",
                "This bridge connects Stage 3 traditional ISP denoise experiments to the existing Stage 2 SIDD tiny paired dataset. The data is real phone sRGB noisy/GT pairs, so it is stronger than synthetic noise for visual sanity checks, while still not being RAW sensor-domain data.",
                "",
                "## Dataset",
                "",
                f"- Pair count discovered: {pair_count}",
                f"- Stage3 manifest: `{manifest_path.as_posix()}`",
                "- Format: `train/val` paired `noisy` and `clean` PNG crops",
                "- Current use: validate denoise behavior on real sRGB noise and texture",
                "- Limitation: black level, CFA, gain map, and RAW noise calibration are not available in this sRGB subset",
                "",
                "## Baseline",
                "",
                "For a small validation subset, this report compares noisy input, Gaussian filtering, and bilateral filtering. The bilateral implementation is the same Python reference used in Week 3, applied per RGB channel on center crops to keep runtime reasonable.",
                "",
                f"- Mean noisy PSNR: {mean_noisy:.3f} dB",
                f"- Mean Gaussian PSNR: {mean_gauss:.3f} dB",
                f"- Mean bilateral PSNR: {mean_bilat:.3f} dB",
                f"- Best bilateral sample: `{best_row['name']}` at {float(best_row['bilateral_psnr']):.3f} dB",
                "",
                f"![SIDD real comparison](figures/week3_sidd_real/{figure_path.name})",
                "",
                "## Engineering Notes",
                "",
                "- This is intentionally a bridge, not a dataset copy. The manifest points to the existing Stage 2 files.",
                "- The same metric code now runs on synthetic vectors and real paired crops, which makes later C++ parity checks easier.",
                "- For an ISP algorithm interview, describe this as a real-image validation set for denoise artifacts, not as RAW ISP evidence.",
                "",
                "## Outputs",
                "",
                f"- Metrics CSV: `{metrics_path.as_posix()}`",
                f"- Figure: `{figure_path.as_posix()}`",
                f"- Data card: `{(OUTPUT_ROOT / 'README.md').as_posix()}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge Stage2 SIDD tiny data into Stage3.")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument("--max-samples", type=int, default=6)
    parser.add_argument("--crop-size", type=int, default=128)
    args = parser.parse_args()

    dataset_root = args.dataset_root.resolve()
    pairs = load_pairs(dataset_root, args.split)
    if not pairs:
        raise FileNotFoundError(f"No paired PNG files found under {dataset_root / args.split}")

    manifest_rows = []
    for split in ["train", "val"]:
        for name, noisy_path, clean_path in load_pairs(dataset_root, split):
            manifest_rows.append(
                {
                    "split": split,
                    "name": name,
                    "noisy_path": noisy_path.as_posix(),
                    "clean_path": clean_path.as_posix(),
                    "source": "stage2_ai_isp/datasets/sidd_tiny",
                    "note": "paired sRGB crop; not RAW",
                }
            )

    manifest_path = write_stage3_manifest(dataset_root, manifest_rows)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    selected = pairs[: args.max_samples]
    metric_rows: list[dict[str, object]] = []
    visual_samples: list[dict[str, object]] = []

    crop_dir = FIGURE_DIR / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)

    for name, noisy_path, clean_path in selected:
        noisy = crop_center(read_png(noisy_path), args.crop_size)
        clean = crop_center(read_png(clean_path), args.crop_size)
        gaussian = rgb_gaussian(noisy)
        bilateral = rgb_bilateral(noisy)

        write_png(crop_dir / f"{Path(name).stem}_noisy.png", noisy)
        write_png(crop_dir / f"{Path(name).stem}_gt.png", clean)
        write_png(crop_dir / f"{Path(name).stem}_bilateral.png", bilateral)

        metric_rows.append(
            {
                "name": name,
                "split": args.split,
                "crop_size": args.crop_size,
                "noisy_psnr": psnr(clean, noisy),
                "gaussian_psnr": psnr(clean, gaussian),
                "bilateral_psnr": psnr(clean, bilateral),
                "noisy_mae": mean_abs_error(clean, noisy),
                "gaussian_mae": mean_abs_error(clean, gaussian),
                "bilateral_mae": mean_abs_error(clean, bilateral),
                "noisy_residual_std": residual_std(clean, noisy),
                "gaussian_residual_std": residual_std(clean, gaussian),
                "bilateral_residual_std": residual_std(clean, bilateral),
            }
        )
        if len(visual_samples) < 4:
            visual_samples.append(
                {
                    "noisy": noisy,
                    "clean": clean,
                    "gaussian": gaussian,
                    "bilateral": bilateral,
                }
            )

    metrics_path = FIGURE_DIR / "week3_sidd_real_metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metric_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metric_rows)

    figure_path = FIGURE_DIR / "week3_sidd_real_comparison.png"
    save_pair_grid(visual_samples, figure_path)
    write_report(manifest_path, len(manifest_rows), metrics_path, figure_path, metric_rows)

    print(f"wrote manifest to {manifest_path}")
    print(f"wrote metrics to {metrics_path}")
    print(f"wrote figure to {figure_path}")
    print(f"wrote report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
