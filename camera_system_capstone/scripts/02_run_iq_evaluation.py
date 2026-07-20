#!/usr/bin/env python3
"""Normalize Stage 1 IQ evidence declared by the Capstone manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import generate_iq_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "iq_summary.csv")
    args = parser.parse_args()
    rows = generate_iq_summary(args.output)
    print(f"iq_summary={args.output} rows={len(rows)}")


if __name__ == "__main__":
    main()

