#!/usr/bin/env python3
"""Audit paired train/val/test folders and source-scene leakage."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root", default="stage2_ai_isp/datasets/sidd_tiny"
    )
    parser.add_argument(
        "--output", default="stage2_ai_isp/reports/dataset_split_audit.json"
    )
    return parser.parse_args()


def names(path: Path) -> set[str]:
    return {item.name for item in path.glob("*.png")}


def main() -> None:
    args = parse_args()
    root = Path(args.dataset_root)
    manifest_path = root / "manifest.csv"
    manifest = []
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8", newline="") as file:
            manifest = list(csv.DictReader(file))

    result: dict[str, object] = {"dataset_root": str(root), "splits": {}}
    split_sources: dict[str, set[str]] = {}
    for split in ("train", "val", "test"):
        noisy = names(root / split / "noisy")
        clean = names(root / split / "clean")
        result["splits"][split] = {
            "noisy_count": len(noisy),
            "clean_count": len(clean),
            "paired_count": len(noisy & clean),
            "unmatched_noisy": sorted(noisy - clean),
            "unmatched_clean": sorted(clean - noisy),
        }
        split_sources[split] = {
            row["source_scene"] for row in manifest if row.get("split") == split
        }
        for name in noisy & clean:
            noisy_image = Image.open(root / split / "noisy" / name)
            clean_image = Image.open(root / split / "clean" / name)
            if noisy_image.size != clean_image.size:
                raise ValueError(f"Shape mismatch in {split}/{name}")

    leakage = {}
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = sorted(split_sources[left] & split_sources[right])
        leakage[f"{left}_vs_{right}"] = overlap
    result["source_scene_leakage"] = leakage
    result["passed"] = (
        all(not values for values in leakage.values())
        and all(
            not split["unmatched_noisy"] and not split["unmatched_clean"]
            for split in result["splits"].values()
        )
        and all(
            split["paired_count"] > 0 for split in result["splits"].values()
        )
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
