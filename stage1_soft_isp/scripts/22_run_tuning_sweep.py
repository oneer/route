#!/usr/bin/env python3
"""Run three controlled Stage 1 IQ tuning sweeps and export decisions.

The source image is a public-DNG rawpy sRGB rendering. Deterministic warm-cast,
noise, and exposure perturbations create controlled inputs with a known
reference. This validates the tuning loop; it is not self-captured lab IQ.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import imageio.v3 as iio
import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from soft_isp.awb import apply_awb, gray_world_gains
from soft_isp.denoise import bilateral_denoise_rgb
from soft_isp.tone import apply_gamma, normalize_by_percentile, reinhard_tone_map


FIELDS = [
    "case_id", "problem", "hypothesis", "module", "parameter", "value",
    "psnr", "ssim", "mean_delta_e_2000_proxy", "texture_retention",
    "highlight_clip_fraction", "score", "selected", "failure_reason",
    "tradeoff", "boundary",
]


def _load_rgb(path: Path, max_size: int) -> np.ndarray:
    image = iio.imread(path)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError(f"expected RGB image: {path}")
    image = image[:, :, :3]
    height, width = image.shape[:2]
    scale = min(1.0, max_size / max(height, width))
    if scale < 1.0:
        import cv2

        image = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    return image.astype(np.float32) / 255.0


def _gradient_energy(image: np.ndarray) -> float:
    return float(np.mean(np.abs(np.diff(image, axis=0))) + np.mean(np.abs(np.diff(image, axis=1))))


def _metrics(candidate: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    candidate = np.clip(candidate, 0.0, 1.0)
    reference = np.clip(reference, 0.0, 1.0)
    stride = max(1, min(reference.shape[:2]) // 256)
    delta_e = deltaE_ciede2000(rgb2lab(reference[::stride, ::stride]), rgb2lab(candidate[::stride, ::stride]))
    reference_texture = max(_gradient_energy(reference), 1.0e-8)
    return {
        "psnr": float(peak_signal_noise_ratio(reference, candidate, data_range=1.0)),
        "ssim": float(structural_similarity(reference, candidate, channel_axis=2, data_range=1.0)),
        "mean_delta_e_2000_proxy": float(np.mean(delta_e)),
        "texture_retention": _gradient_energy(candidate) / reference_texture,
        "highlight_clip_fraction": float(np.mean(np.max(candidate, axis=2) >= 0.995)),
    }


def _row(case: dict[str, str], parameter: str, value: str, candidate: np.ndarray, reference: np.ndarray) -> dict:
    metrics = _metrics(candidate, reference)
    score = metrics["ssim"] - 0.002 * metrics["mean_delta_e_2000_proxy"]
    return {
        **case,
        "parameter": parameter,
        "value": value,
        **metrics,
        "score": score,
        "selected": "false",
        "failure_reason": "",
        "tradeoff": "",
        "boundary": "Controlled perturbation of public-DNG sRGB rendering; not self-captured lab tuning.",
        "_candidate": candidate,
    }


def run_sweeps(reference: np.ndarray, seed: int = 3083325) -> list[dict]:
    rows: list[dict] = []

    warm = np.clip(reference * np.array([1.18, 1.0, 0.72], dtype=np.float32), 0.0, 1.0)
    case = {
        "case_id": "awb_filter", "problem": "Injected warm cast",
        "hypothesis": "Dark/highlight rejection stabilizes Gray-World gains",
        "module": "AWB",
    }
    for low, high in ((0.0, 100.0), (2.0, 98.0), (5.0, 95.0), (10.0, 90.0)):
        gains = gray_world_gains(warm, low_percentile=low, high_percentile=high)
        rows.append(_row(case, "low_high_percentile", f"{low:g}/{high:g}", apply_awb(warm, gains, 1.0), reference))

    rng = np.random.default_rng(seed)
    noisy = np.clip(reference + rng.normal(0.0, 0.035, reference.shape).astype(np.float32), 0.0, 1.0)
    case = {
        "case_id": "bilateral_sigma", "problem": "Injected Gaussian RGB noise",
        "hypothesis": "Moderate range sigma removes noise without excessive texture loss",
        "module": "traditional_denoise",
    }
    for sigma in (0.02, 0.04, 0.07, 0.10):
        rows.append(_row(case, "sigma_range", f"{sigma:.3f}", bilateral_denoise_rgb(noisy, sigma), reference))

    linear = np.power(reference, 2.2)
    # Clipping makes the perturbation irreversible, so percentile normalization
    # cannot trivially recover the reference by cancelling one scalar gain.
    overexposed = np.clip(linear * 1.6, 0.0, 1.0)
    case = {
        "case_id": "tone_highlight", "problem": "Injected 1.6x linear exposure",
        "hypothesis": "A lower white percentile plus Reinhard reduces highlight clipping",
        "module": "tone_mapping",
    }
    for method, percentile in (("percentile", 99.0), ("percentile", 99.9), ("reinhard", 99.0), ("reinhard", 99.9)):
        mapped = (
            normalize_by_percentile(overexposed, percentile)
            if method == "percentile"
            else reinhard_tone_map(overexposed, percentile)
        )
        rows.append(_row(case, "method_percentile", f"{method}/{percentile:g}", apply_gamma(mapped), reference))

    for case_id in sorted({str(row["case_id"]) for row in rows}):
        items = [row for row in rows if row["case_id"] == case_id]
        selected = max(items, key=lambda item: float(item["score"]))
        selected["selected"] = "true"
        selected["tradeoff"] = "Best composite SSIM/color score; inspect texture and clipping before product use."
        for item in items:
            if item is selected:
                continue
            if float(item["texture_retention"]) < 0.80:
                item["failure_reason"] = "over_smoothing"
            elif float(item["highlight_clip_fraction"]) > float(selected["highlight_clip_fraction"]) + 0.02:
                item["failure_reason"] = "highlight_clipping"
            else:
                item["failure_reason"] = "lower_reference_similarity"
            item["tradeoff"] = "Rejected by the declared composite score or a stronger visible artifact proxy."
    return rows


def _write_report(rows: list[dict], report_path: Path, source: Path) -> None:
    selected = [row for row in rows if row["selected"] == "true"]
    lines = [
        "# Stage 1 controlled IQ tuning sweep",
        "",
        f"Source: `{source.as_posix()}` (public DNG rawpy sRGB rendering).",
        "",
        "This experiment closes the reproducible tuning-loop gap with known synthetic perturbations. It does not replace self-captured scenes, a ColorChecker, a flat field, or a slanted-edge chart.",
        "",
        "| Case | Selected parameter | PSNR | SSIM | Delta E 2000 proxy | Texture retention | Highlight clip |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in selected:
        lines.append(
            f"| {row['case_id']} | {row['value']} | {float(row['psnr']):.3f} | "
            f"{float(row['ssim']):.4f} | {float(row['mean_delta_e_2000_proxy']):.3f} | "
            f"{float(row['texture_retention']):.3f} | {float(row['highlight_clip_fraction']):.4f} |"
        )
    lines.extend([
        "", "## Decision loop", "",
        "Each case records problem -> hypothesis -> module -> parameter sweep -> metrics -> failure reason -> selected setting. The full machine-readable table is `figures/camera_iq/tuning_sweep.csv`.",
        "", "## Boundary", "",
        "Delta E is full-image reference difference, not ColorChecker accuracy. Noise is injected Gaussian RGB noise, not a calibrated sensor noise model. Decisions must be re-tuned on captured Camera scenes.",
    ])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_failures(rows: list[dict], path: Path) -> None:
    failures = []
    for case_id in sorted({str(row["case_id"]) for row in rows}):
        rejected = [row for row in rows if row["case_id"] == case_id and row["selected"] != "true"]
        failures.append(min(rejected, key=lambda item: float(item["score"])))
    lines = [
        "# Stage 1 tuning failure cases", "",
        "| Case | Rejected setting | Failure classification | Evidence |",
        "|---|---|---|---|",
    ]
    for row in failures:
        lines.append(
            f"| {row['case_id']} | {row['value']} | {row['failure_reason']} | "
            f"SSIM={float(row['ssim']):.4f}, texture={float(row['texture_retention']):.3f}, clip={float(row['highlight_clip_fraction']):.4f} |"
        )
    lines.extend(["", "These are controlled failures, not claims about an actual phone ISP.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=ROOT / "data" / "references" / "T01_a0006-IMG_2787_rawpy_srgb.png")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "figures" / "camera_iq")
    parser.add_argument("--max-size", type=int, default=768)
    args = parser.parse_args()
    reference = _load_rgb(args.reference, args.max_size)
    rows = run_sweeps(reference)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "tuning_sweep.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    _write_report(rows, ROOT / "reports" / "real_camera_iq_evaluation.md", args.reference.relative_to(ROOT))
    _write_failures(rows, ROOT / "reports" / "tuning_failure_cases.md")
    print(f"tuning_sweep={args.output_dir / 'tuning_sweep.csv'} rows={len(rows)} selected=3")


if __name__ == "__main__":
    main()
