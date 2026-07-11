from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from soft_isp.raw_contract import validate_manifest


ROOT = Path(__file__).resolve().parents[1]


class RawContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((ROOT / "data/raw_metadata_manifest.json").read_text(encoding="utf-8"))

    def test_tracked_manifest_is_valid(self) -> None:
        self.assertEqual(self.manifest["source_count"], 14)
        self.assertEqual(validate_manifest(self.manifest), [])

    def test_duplicate_source_is_rejected(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["samples"].append(deepcopy(manifest["samples"][0]))
        manifest["source_count"] += 1
        self.assertIn("duplicate source_file", "\n".join(validate_manifest(manifest)))

    def test_signal_bit_claim_is_checked(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["samples"][0]["inferred_signal_bits"] += 1
        self.assertIn("inferred_signal_bits mismatch", "\n".join(validate_manifest(manifest)))
