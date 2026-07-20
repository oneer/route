"""Cross-stage config and normalized-output tests."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import generate_iq_summary, generate_system_profile_summary, load_config


class StageContractTests(unittest.TestCase):
    def test_data_spaces_define_layout_range_and_color_boundary(self) -> None:
        contract = load_config("data_contract.yaml")
        self.assertEqual(set(contract["image_spaces"]), {"bayer_raw", "linear_rgb", "srgb"})
        for definition in contract["image_spaces"].values():
            self.assertIn("layout", definition)
            self.assertIn("value_range", definition)
            self.assertIn("color_boundary", definition)

    def test_iq_normalization_preserves_proxy_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rows = generate_iq_summary(Path(directory) / "iq.csv")
        self.assertEqual(len(rows), 14)
        self.assertEqual(rows[0]["status"], "verified_proxy")
        self.assertIn("not self-captured", rows[0]["boundary"])

    def test_system_profile_preserves_measured_and_unmeasured_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "system.csv"
            rows = generate_system_profile_summary(path)
            with path.open("r", encoding="utf-8", newline="") as handle:
                written = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(all(row["status"] == "verified_partial" for row in rows))
        self.assertTrue(all(not row["peak_vram_mib"] for row in written))
        device = next(row for row in written if row["backend"] == "ORT CUDA IOBinding")
        self.assertEqual(device["peak_ram_mib"], "614.609375")
        self.assertEqual(device["h2d_d2h_count"], "1 H2D / 0 intermediate D2H / 1 final D2H")
        historical = [row for row in written if row["backend"] != "ORT CUDA IOBinding"]
        self.assertTrue(all(not row["peak_ram_mib"] for row in historical))
        self.assertTrue(all(not row["h2d_d2h_count"] for row in historical))


if __name__ == "__main__":
    unittest.main()
