#!/usr/bin/env python3
"""Convert an RGB image to the simple NCHW float tensor format used by C++."""

from __future__ import annotations

import argparse
from pathlib import Path
import struct

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rgb = np.asarray(Image.open(args.input).convert("RGB"), dtype=np.float32) / 255.0
    tensor = np.transpose(rgb, (2, 0, 1))[None].copy()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file:
        file.write(struct.pack("<4i", *tensor.shape))
        file.write(tensor.astype("<f4", copy=False).tobytes())
    print(f"saved: {output} shape={tensor.shape}")


if __name__ == "__main__":
    main()
