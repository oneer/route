#!/usr/bin/env python3
"""Publish multicamera readiness without fabricating unavailable measurements."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import generate_multicamera_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "multicamera_summary.csv")
    args = parser.parse_args()
    rows = generate_multicamera_summary(args.output)
    print(f"multicamera_summary={args.output} rows={len(rows)} status={rows[0]['status']}")


if __name__ == "__main__":
    main()

