#!/usr/bin/env python3
"""Fit a 3x3 CCM from measured/reference linear-RGB patch CSV data."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from soft_isp.calibration import evaluate_colorchecker, fit_ccm_least_squares


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch_csv", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "figures" / "camera_iq" / "ccm_calibration.json")
    parser.add_argument("--regularization", type=float, default=1.0e-6)
    args = parser.parse_args()
    with args.patch_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    measured = np.asarray([[row[f"measured_{c}"] for c in "rgb"] for row in rows], dtype=np.float64)
    reference = np.asarray([[row[f"reference_{c}"] for c in "rgb"] for row in rows], dtype=np.float64)
    ccm = fit_ccm_least_squares(measured, reference, args.regularization)
    result = {
        "patch_count": len(rows),
        "ccm": ccm.tolist(),
        "metrics": evaluate_colorchecker(measured, reference, ccm),
        "boundary": "Linear-RGB patch fit; chart capture/extraction quality must be validated separately.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ccm_calibration={args.output} patches={len(rows)}")


if __name__ == "__main__":
    main()
