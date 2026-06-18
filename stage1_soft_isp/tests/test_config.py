from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from soft_isp.pipeline import load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_has_required_sections(self) -> None:
        config = load_config(Path(__file__).parents[1] / "configs" / "default.yaml")
        self.assertIn("pipeline", config)
        self.assertIn("parameters", config)
        self.assertIn("output", config)

    def test_non_mapping_config_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.yaml"
            path.write_text("- one\n- two\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
