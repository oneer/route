#!/usr/bin/env python3
"""Audit paired train/val/test folders and source-scene leakage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_isp.data.split_audit import audit_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", default="stage2_ai_isp/datasets/sidd_tiny")
    parser.add_argument("--output", default="stage2_ai_isp/reports/dataset_split_audit.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = audit_dataset(Path(args.dataset_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
