"""Paired-image split integrity and source-scene leakage audit."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image


SPLITS = ("train", "val", "test")
REQUIRED_MANIFEST_FIELDS = {"split", "name", "source_scene"}


def image_names(path: Path) -> set[str]:
    return {item.name for item in path.glob("*.png") if item.is_file()}


def read_manifest(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], ["missing manifest.csv"]
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_MANIFEST_FIELDS - fields)
        if missing:
            return [], [f"manifest missing columns: {', '.join(missing)}"]
        return list(reader), []


def audit_dataset(root: Path, check_shapes: bool = True) -> dict[str, object]:
    root = root.resolve()
    manifest, manifest_errors = read_manifest(root / "manifest.csv")
    result: dict[str, object] = {
        "dataset_root": root.as_posix(),
        "manifest_errors": manifest_errors,
        "splits": {},
    }

    rows_by_split: dict[str, list[dict[str, str]]] = {split: [] for split in SPLITS}
    seen_rows: set[tuple[str, str]] = set()
    for row in manifest:
        split = row["split"].strip()
        name = row["name"].strip()
        source_scene = row["source_scene"].strip()
        if split not in rows_by_split:
            manifest_errors.append(f"unknown split: {split}")
            continue
        if not name:
            manifest_errors.append(f"empty name in split {split}")
            continue
        if not source_scene:
            manifest_errors.append(f"empty source_scene for {split}/{name}")
        key = (split, name)
        if key in seen_rows:
            manifest_errors.append(f"duplicate manifest row: {split}/{name}")
            continue
        seen_rows.add(key)
        rows_by_split[split].append(row)

    split_sources: dict[str, set[str]] = {}
    for split in SPLITS:
        noisy = image_names(root / split / "noisy")
        clean = image_names(root / split / "clean")
        paired = noisy & clean
        manifest_names = {row["name"].strip() for row in rows_by_split[split]}
        split_result = {
            "noisy_count": len(noisy),
            "clean_count": len(clean),
            "paired_count": len(paired),
            "unmatched_noisy": sorted(noisy - clean),
            "unmatched_clean": sorted(clean - noisy),
            "unmanifested_pairs": sorted(paired - manifest_names),
            "manifest_rows_without_pair": sorted(manifest_names - paired),
        }
        result["splits"][split] = split_result
        split_sources[split] = {
            row["source_scene"].strip()
            for row in rows_by_split[split]
            if row["source_scene"].strip()
        }

        if check_shapes:
            for name in paired:
                with Image.open(root / split / "noisy" / name) as noisy_image:
                    noisy_size = noisy_image.size
                with Image.open(root / split / "clean" / name) as clean_image:
                    clean_size = clean_image.size
                if noisy_size != clean_size:
                    raise ValueError(f"Shape mismatch in {split}/{name}: {noisy_size} != {clean_size}")

    leakage: dict[str, list[str]] = {}
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        leakage[f"{left}_vs_{right}"] = sorted(split_sources[left] & split_sources[right])
    result["source_scene_leakage"] = leakage

    splits = result["splits"]
    result["passed"] = (
        not manifest_errors
        and all(not values for values in leakage.values())
        and all(
            split_result["paired_count"] > 0
            and not split_result["unmatched_noisy"]
            and not split_result["unmatched_clean"]
            and not split_result["unmanifested_pairs"]
            and not split_result["manifest_rows_without_pair"]
            for split_result in splits.values()
        )
    )
    return result
