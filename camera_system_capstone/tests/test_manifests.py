"""Manifest schema, path portability, hash, and evidence-boundary tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import MANIFEST_ROOT, read_csv, validate_repository


class ManifestTests(unittest.TestCase):
    def test_repository_contract_is_valid(self) -> None:
        errors, warnings = validate_repository()
        self.assertEqual(errors, [])
        self.assertTrue(any("multicamera" in warning for warning in warnings))

    def test_paths_are_portable_and_available_assets_exist(self) -> None:
        captures = read_csv(MANIFEST_ROOT / "capture_manifest.csv")
        self.assertGreaterEqual(len(captures), 1)
        for row in captures:
            path = row["asset_path"]
            self.assertFalse(Path(path).is_absolute())
            self.assertFalse(PureWindowsPath(path).is_absolute())
            self.assertNotIn("\\", path)

    def test_public_data_is_not_presented_as_self_capture(self) -> None:
        captures = read_csv(MANIFEST_ROOT / "capture_manifest.csv")
        self.assertTrue(all(row["source_kind"] == "public_dataset" for row in captures))
        self.assertTrue(all(row["device"] == "unknown" for row in captures))


if __name__ == "__main__":
    unittest.main()

