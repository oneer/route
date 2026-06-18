#!/usr/bin/env python3
"""Compare a quantized PNG backend output against a reference output PNG."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.metrics import batch_psnr, batch_ssim


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", default="opencv_dnn_cpp")
    return parser.parse_args()


def load(path: str) -> torch.Tensor:
    array = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(np.transpose(array, (2, 0, 1))[None].copy())


def main() -> None:
    args = parse_args()
    reference = load(args.reference)
    candidate = load(args.candidate)
    if reference.shape != candidate.shape:
        raise ValueError(
            f"Shape mismatch: {tuple(reference.shape)} vs {tuple(candidate.shape)}"
        )
    error = (reference - candidate).abs()
    result = {
        "backend": args.backend,
        "reference": args.reference,
        "candidate": args.candidate,
        "max_abs_error_after_png_quantization": error.max().item(),
        "mean_abs_error_after_png_quantization": error.mean().item(),
        "psnr_vs_reference": batch_psnr(candidate, reference).mean().item(),
        "ssim_vs_reference": batch_ssim(candidate, reference).mean().item(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
