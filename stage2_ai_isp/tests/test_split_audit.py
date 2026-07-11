from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ai_isp.data.split_audit import SPLITS, audit_dataset


class SplitAuditTests(unittest.TestCase):
    def make_dataset(self, root: Path, scenes: dict[str, str]) -> None:
        rows = []
        for index, split in enumerate(SPLITS, start=1):
            name = f"pair_{index:05d}.png"
            for kind in ("noisy", "clean"):
                folder = root / split / kind
                folder.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (8, 8), color=(index, index, index)).save(folder / name)
            rows.append(
                {
                    "split": split,
                    "name": name,
                    "source_scene": scenes[split],
                    "source_noisy": f"source/{split}/noisy.png",
                    "source_clean": f"source/{split}/clean.png",
                }
            )
        with (root / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_valid_dataset_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_dataset(root, {"train": "scene-a", "val": "scene-b", "test": "scene-c"})
            result = audit_dataset(root)
            self.assertTrue(result["passed"])

    def test_source_scene_overlap_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_dataset(root, {"train": "scene-a", "val": "scene-a", "test": "scene-c"})
            result = audit_dataset(root)
            self.assertFalse(result["passed"])
            self.assertEqual(result["source_scene_leakage"]["train_vs_val"], ["scene-a"])

    def test_unmatched_or_unmanifested_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_dataset(root, {"train": "scene-a", "val": "scene-b", "test": "scene-c"})
            Image.new("RGB", (8, 8)).save(root / "train/noisy/untracked.png")
            result = audit_dataset(root)
            self.assertFalse(result["passed"])
            self.assertEqual(result["splits"]["train"]["unmatched_noisy"], ["untracked.png"])

    def test_shape_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_dataset(root, {"train": "scene-a", "val": "scene-b", "test": "scene-c"})
            Image.new("RGB", (4, 4)).save(root / "test/clean/pair_00003.png")
            with self.assertRaisesRegex(ValueError, "Shape mismatch"):
                audit_dataset(root)
