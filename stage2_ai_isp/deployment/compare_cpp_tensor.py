#!/usr/bin/env python3
"""Compare C++ ORT float output against PyTorch and save a PNG preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.engine.checkpoint import load_checkpoint
from ai_isp.metrics import batch_psnr, batch_ssim
from ai_isp.models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--input-image", required=True)
    parser.add_argument("--cpp-output", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def read_tensor(path: str) -> np.ndarray:
    with Path(path).open("rb") as file:
        shape = struct.unpack("<4i", file.read(16))
        array = np.frombuffer(file.read(), dtype="<f4").copy()
    expected = int(np.prod(shape))
    if array.size != expected:
        raise ValueError(f"Expected {expected} floats, found {array.size}")
    return array.reshape(shape)


def main() -> None:
    args = parse_args()
    with Path(args.config).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    model = build_model(config["model"]).eval()
    load_checkpoint(args.checkpoint, model)
    rgb = np.asarray(
        Image.open(args.input_image).convert("RGB"), dtype=np.float32
    ) / 255.0
    input_tensor = torch.from_numpy(
        np.transpose(rgb, (2, 0, 1))[None].copy()
    )
    with torch.no_grad():
        reference = model(input_tensor).clamp(0.0, 1.0)
    candidate = torch.from_numpy(read_tensor(args.cpp_output)).clamp(0.0, 1.0)
    if candidate.shape != reference.shape:
        raise ValueError(
            f"Shape mismatch: {tuple(candidate.shape)} vs {tuple(reference.shape)}"
        )
    error = (candidate - reference).abs()
    result = {
        "max_abs_error": error.max().item(),
        "mean_abs_error": error.mean().item(),
        "psnr_vs_pytorch": batch_psnr(candidate, reference).mean().item(),
        "ssim_vs_pytorch": batch_ssim(candidate, reference).mean().item(),
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    preview = np.transpose(candidate.numpy()[0], (1, 2, 0))
    Image.fromarray((preview * 255.0 + 0.5).astype(np.uint8)).save(
        output_dir / "cpp_ort_output.png"
    )
    (output_dir / "cpp_ort_alignment.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
