#!/usr/bin/env python3
"""Export failure counts from Stage 2 per-sample Camera scene metrics."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("stage2_ai_isp/reports/figures/camera_scene_evaluation/failure_matrix.csv"))
    args = parser.parse_args()
    with args.metrics_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    counts = Counter((row["scene_group"], row["method"], row["failure_type"]) for row in rows)
    output = [
        {"scene_group": key[0], "method": key[1], "failure_type": key[2], "count": count}
        for key, count in sorted(counts.items())
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scene_group", "method", "failure_type", "count"])
        writer.writeheader()
        writer.writerows(output)
    print(f"failure_matrix={args.output} rows={len(output)}")


if __name__ == "__main__":
    main()
