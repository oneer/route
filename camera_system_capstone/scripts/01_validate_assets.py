#!/usr/bin/env python3
"""Validate Capstone configs, manifests, hashes, and stage-output references."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import validate_repository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "asset_validation.json")
    args = parser.parse_args()
    errors, warnings = validate_repository()
    result = {"status": "pass" if not errors else "fail", "errors": errors, "warnings": warnings}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"asset_validation={result['status']} errors={len(errors)} warnings={len(warnings)}")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()

