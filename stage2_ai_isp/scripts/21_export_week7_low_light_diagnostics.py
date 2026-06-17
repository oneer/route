#!/usr/bin/env python3
"""Export low-light specific diagnostics for Week 7."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.models import build_model


@dataclass
class DiagnosticSummary:
    name: str
    luma_mean: float
    luma_mae: float
    dark_luma_mae: float
    rgb_mae: float
    under_enhanced_pct: float
    over_enhanced_pct: float
    black_clip_pct: float
    white_clip_pct: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Week 7 low-light diagnostics.")
    parser.add_argument("--config", default="stage2_ai_isp/configs/low_light_sidd_tiny_unet_l1_300.yaml")
    parser.add_argument(
        "--checkpoint",
        default="stage2_ai_isp/runs/low_light_sidd_tiny_unet_l1_300/checkpoints/best_psnr.pth",
    )
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week7_low_light_diagnostics")
    parser.add_argument("--max-images", type=int, default=20)
    parser.add_argument("--dark-threshold", type=float, default=0.25)
    parser.add_argument("--delta-threshold", type=float, default=0.10)
    return parser.parse_args()


def load_rgb(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    return np.asarray(image, dtype=np.float32) / 255.0


def to_tensor(image: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)


def luma(image: np.ndarray) -> np.ndarray:
    return 0.299 * image[..., 0] + 0.587 * image[..., 1] + 0.114 * image[..., 2]


def summarize(name: str, image: np.ndarray, clean: np.ndarray, dark_mask: np.ndarray, delta_threshold: float) -> DiagnosticSummary:
    image_luma = luma(image)
    clean_luma = luma(clean)
    delta = image_luma - clean_luma
    return DiagnosticSummary(
        name=name,
        luma_mean=float(image_luma.mean()),
        luma_mae=float(np.abs(delta).mean()),
        dark_luma_mae=float(np.abs(delta[dark_mask]).mean()) if dark_mask.any() else 0.0,
        rgb_mae=float(np.abs(image - clean).mean()),
        under_enhanced_pct=float((delta < -delta_threshold).mean() * 100.0),
        over_enhanced_pct=float((delta > delta_threshold).mean() * 100.0),
        black_clip_pct=float((image <= 0.02).mean() * 100.0),
        white_clip_pct=float((image >= 0.98).mean() * 100.0),
    )


def list_pairs(noisy_dir: Path, clean_dir: Path, max_images: int) -> list[tuple[Path, Path]]:
    noisy = {path.name: path for path in sorted(noisy_dir.glob("*.png"))}
    clean = {path.name: path for path in sorted(clean_dir.glob("*.png"))}
    names = sorted(set(noisy) & set(clean))[:max_images]
    if not names:
        raise FileNotFoundError(f"No paired PNGs found in {noisy_dir} and {clean_dir}")
    return [(noisy[name], clean[name]) for name in names]


def load_model(config_path: Path, checkpoint_path: Path) -> torch.nn.Module:
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model = build_model(config["model"])
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model


@torch.no_grad()
def infer(model: torch.nn.Module, low: np.ndarray) -> np.ndarray:
    tensor = to_tensor(low)
    output = torch.clamp(model(tensor), 0.0, 1.0)
    return output.squeeze(0).permute(1, 2, 0).cpu().numpy()


def mean_summary(name: str, rows: list[DiagnosticSummary]) -> DiagnosticSummary:
    return DiagnosticSummary(
        name=name,
        luma_mean=float(np.mean([row.luma_mean for row in rows])),
        luma_mae=float(np.mean([row.luma_mae for row in rows])),
        dark_luma_mae=float(np.mean([row.dark_luma_mae for row in rows])),
        rgb_mae=float(np.mean([row.rgb_mae for row in rows])),
        under_enhanced_pct=float(np.mean([row.under_enhanced_pct for row in rows])),
        over_enhanced_pct=float(np.mean([row.over_enhanced_pct for row in rows])),
        black_clip_pct=float(np.mean([row.black_clip_pct for row in rows])),
        white_clip_pct=float(np.mean([row.white_clip_pct for row in rows])),
    )


def write_csv(rows: list[DiagnosticSummary], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "name",
                "luma_mean",
                "luma_mae",
                "dark_luma_mae",
                "rgb_mae",
                "under_enhanced_pct",
                "over_enhanced_pct",
                "black_clip_pct",
                "white_clip_pct",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.name,
                    f"{row.luma_mean:.6f}",
                    f"{row.luma_mae:.6f}",
                    f"{row.dark_luma_mae:.6f}",
                    f"{row.rgb_mae:.6f}",
                    f"{row.under_enhanced_pct:.4f}",
                    f"{row.over_enhanced_pct:.4f}",
                    f"{row.black_clip_pct:.4f}",
                    f"{row.white_clip_pct:.4f}",
                ]
            )


def write_markdown(rows: list[DiagnosticSummary], path: Path, csv_path: Path, sample_count: int) -> None:
    input_row = next(row for row in rows if row.name == "low_light_input")
    output_row = next(row for row in rows if row.name == "model_output")
    clean_row = next(row for row in rows if row.name == "clean_target")

    luma_gain = input_row.luma_mae - output_row.luma_mae
    dark_gain = input_row.dark_luma_mae - output_row.dark_luma_mae
    rgb_gain = input_row.rgb_mae - output_row.rgb_mae

    lines = [
        "# Week 7 Low-Light Diagnostics",
        "",
        f"Samples: `{sample_count}` validation images.",
        f"CSV: `{csv_path.as_posix()}`",
        "",
        "| View | Mean Luma | Luma MAE | Dark Luma MAE | RGB MAE | Under % | Over % | Black Clip % | White Clip % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.name,
                    f"{row.luma_mean:.4f}",
                    f"{row.luma_mae:.4f}",
                    f"{row.dark_luma_mae:.4f}",
                    f"{row.rgb_mae:.4f}",
                    f"{row.under_enhanced_pct:.2f}",
                    f"{row.over_enhanced_pct:.2f}",
                    f"{row.black_clip_pct:.2f}",
                    f"{row.white_clip_pct:.2f}",
                ]
            )
            + " |"
        )

    lines += [
        "",
        "## Key Reading",
        "",
        f"- Luma MAE improves by `{luma_gain:.4f}` from input to model output.",
        f"- Dark-region luma MAE improves by `{dark_gain:.4f}`.",
        f"- RGB MAE improves by `{rgb_gain:.4f}`.",
        f"- The model output mean luma is `{output_row.luma_mean:.4f}`, while the clean target mean luma is `{clean_row.luma_mean:.4f}`.",
        f"- Under-enhanced pixels drop from `{input_row.under_enhanced_pct:.2f}%` to `{output_row.under_enhanced_pct:.2f}%`.",
        f"- Over-enhanced pixels are `{output_row.over_enhanced_pct:.2f}%`, so this run is still more under-enhanced than over-enhanced.",
        "",
        "## Interview Use",
        "",
        "These diagnostics explain low-light enhancement beyond PSNR/SSIM: the task must recover exposure, suppress dark-region noise, and preserve color. If PSNR improves but dark-region MAE or color MAE remains high, the next experiment should target exposure/noise modeling or color-aware losses rather than only changing the backbone.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    val_cfg = config["data"]["val"]
    pairs = list_pairs(Path("stage2_ai_isp") / val_cfg["noisy_dir"], Path("stage2_ai_isp") / val_cfg["clean_dir"], args.max_images)
    model = load_model(config_path, Path(args.checkpoint))

    input_rows: list[DiagnosticSummary] = []
    output_rows: list[DiagnosticSummary] = []
    clean_rows: list[DiagnosticSummary] = []

    for low_path, clean_path in pairs:
        low = load_rgb(low_path)
        clean = load_rgb(clean_path)
        output = infer(model, low)
        dark_mask = luma(clean) < args.dark_threshold
        input_rows.append(summarize("low_light_input", low, clean, dark_mask, args.delta_threshold))
        output_rows.append(summarize("model_output", output, clean, dark_mask, args.delta_threshold))
        clean_rows.append(summarize("clean_target", clean, clean, dark_mask, args.delta_threshold))

    rows = [
        mean_summary("low_light_input", input_rows),
        mean_summary("model_output", output_rows),
        mean_summary("clean_target", clean_rows),
    ]
    output_dir = Path(args.output_dir)
    csv_path = output_dir / "week7_low_light_diagnostics.csv"
    md_path = output_dir / "week7_low_light_diagnostics.md"
    write_csv(rows, csv_path)
    write_markdown(rows, md_path, csv_path, len(pairs))
    print(f"saved: {csv_path}")
    print(f"saved: {md_path}")


if __name__ == "__main__":
    main()
