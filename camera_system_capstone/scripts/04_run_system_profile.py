#!/usr/bin/env python3
"""Normalize existing Stage 4 measurements and expose missing system metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import generate_system_profile_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "system_profile_summary.csv")
    args = parser.parse_args()
    rows = generate_system_profile_summary(args.output)
    print(f"system_profile_summary={args.output} rows={len(rows)}")


if __name__ == "__main__":
    main()

