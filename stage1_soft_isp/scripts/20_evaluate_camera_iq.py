#!/usr/bin/env python3
"""Run manifest-driven RAW exposure/noise/sharpness IQ diagnostics."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import rawpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from soft_isp.iq_metrics import (
    approximate_dynamic_range_db,
    edge_mtf50_proxy,
    exposure_statistics,
    roi_snr_db,
    strongest_edge_roi,
)


FIELDS = [
    "sample_id", "scene_group", "source_kind", "split",
    "mean_code_value", "p01_code_value", "p50_code_value", "p99_code_value",
    "mean_normalized", "p01_normalized", "p50_normalized", "p99_normalized",
    "near_black_fraction", "near_white_fraction", "flat_roi_snr_db_proxy",
    "approx_dynamic_range_db_proxy", "mtf50_proxy_cyc_per_px", "status", "boundary",
]


def _center_roi(shape: tuple[int, int], size: int) -> tuple[int, int, int, int]:
    height, width = shape
    size = min(size, height, width)
    return ((width - size) // 2, (height - size) // 2, size, size)


def evaluate_row(row: dict[str, str], roi_size: int) -> dict[str, str | float]:
    raw_path = ROOT / row["input_path"]
    with rawpy.imread(str(raw_path)) as raw:
        data = raw.raw_image_visible.copy()
        black_level = float(min(raw.black_level_per_channel))
        white_level = float(raw.white_level)
    exposure = exposure_statistics(data, black_level, white_level)
    flat_roi = _center_roi(data.shape, roi_size)
    x, y, w, h = flat_roi
    snr = roi_snr_db(data[y : y + h, x : x + w], black_level)
    edge_roi = strongest_edge_roi(data, min(roi_size, min(data.shape)), stride=roi_size)
    sharpness = edge_mtf50_proxy(data, edge_roi)
    return {
        "sample_id": row["sample_id"],
        "scene_group": row["scene_group"],
        "source_kind": row["source_kind"],
        "split": row["split"],
        **exposure,
        "flat_roi_snr_db_proxy": snr["snr_db"],
        "approx_dynamic_range_db_proxy": approximate_dynamic_range_db(
            white_level, black_level, snr["noise_std"]
        ),
        "mtf50_proxy_cyc_per_px": sharpness["mtf50_proxy_cyc_per_px"],
        "status": "verified_proxy",
        "boundary": "Natural-image center/edge ROI proxies; not flat-field SNR or chart MTF.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "camera_iq_manifest.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "figures" / "camera_iq" / "iq_summary.csv")
    parser.add_argument("--roi-size", type=int, default=256)
    args = parser.parse_args()
    with args.manifest.open("r", encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    rows = [evaluate_row(row, args.roi_size) for row in manifest if row["status"] == "available"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"camera_iq={args.output} rows={len(rows)}")


if __name__ == "__main__":
    main()
