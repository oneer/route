from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import rawpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.stats import describe_array, split_bayer


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect RAW/DNG metadata and basic Bayer statistics.")
    parser.add_argument("raw_path", type=Path, help="Path to a RAW/DNG file.")
    parser.add_argument("--pattern", default="RGGB", help="Bayer pattern used for channel statistics.")
    args = parser.parse_args()

    with rawpy.imread(str(args.raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        result = {
            "file": str(args.raw_path),
            "raw": describe_array(raw_visible),
            "black_level_per_channel": list(raw.black_level_per_channel),
            "camera_white_level_per_channel": list(raw.camera_white_level_per_channel or []),
            "white_level": raw.white_level,
            "color_desc": raw.color_desc.decode(errors="replace"),
            "raw_pattern": raw.raw_pattern.tolist(),
            "channels": {
                name: describe_array(channel)
                for name, channel in split_bayer(raw_visible, args.pattern).items()
            },
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
