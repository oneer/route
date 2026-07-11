#!/usr/bin/env python3
"""Generate and validate the Stage 1 real-RAW metadata contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from soft_isp.raw_contract import build_manifest, validate_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--output", default="data/raw_metadata_manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = ROOT / args.raw_dir
    paths = sorted(raw_dir.glob("*.dng"))
    if not paths:
        raise SystemExit(f"No DNG files found in {raw_dir}; run git lfs pull or provide --raw-dir")
    manifest = build_manifest(paths, ROOT)
    errors = validate_manifest(manifest)
    if errors:
        raise SystemExit("RAW contract validation failed:\n- " + "\n- ".join(errors))
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"raw_contract=pass samples={manifest['source_count']} output={output}")


if __name__ == "__main__":
    main()
