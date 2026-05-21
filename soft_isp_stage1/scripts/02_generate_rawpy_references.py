from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v3 as iio
import rawpy


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rawpy sRGB reference outputs for DNG files.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/references"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for raw_path in sorted(args.raw_dir.glob("*.dng")):
        out_path = args.out_dir / f"{raw_path.stem}_rawpy_srgb.png"
        with rawpy.imread(str(raw_path)) as raw:
            rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
        iio.imwrite(out_path, rgb)
        print(out_path)


if __name__ == "__main__":
    main()

