#!/usr/bin/env python3
"""Compare PyTorch and ONNX Runtime outputs on one fixed RGB image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

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
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--output-dir", default="stage2_ai_isp/deployment/outputs/onnx_alignment"
    )
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=30)
    return parser.parse_args()


def load_input(path: str) -> tuple[np.ndarray, torch.Tensor]:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    nchw = np.transpose(rgb, (2, 0, 1))[None].copy()
    return rgb, torch.from_numpy(nchw)


def save_rgb(path: Path, nchw: np.ndarray) -> None:
    rgb = np.transpose(np.clip(nchw[0], 0.0, 1.0), (1, 2, 0))
    Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8)).save(path)


def main() -> None:
    args = parse_args()
    import onnxruntime as ort

    with Path(args.config).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    model = build_model(config["model"]).eval()
    load_checkpoint(args.checkpoint, model)
    _, tensor = load_input(args.input)

    with torch.no_grad():
        pytorch_output = model(tensor).clamp(0.0, 1.0)

    session = ort.InferenceSession(
        args.onnx, providers=["CPUExecutionProvider"]
    )
    input_name = session.get_inputs()[0].name
    array = tensor.numpy()
    for _ in range(args.warmup):
        session.run(None, {input_name: array})
    latencies = []
    onnx_output = None
    for _ in range(args.repeats):
        start = time.perf_counter()
        onnx_output = session.run(None, {input_name: array})[0]
        latencies.append((time.perf_counter() - start) * 1000.0)
    assert onnx_output is not None

    onnx_tensor = torch.from_numpy(onnx_output).clamp(0.0, 1.0)
    difference = (pytorch_output - onnx_tensor).abs()
    result = {
        "input": args.input,
        "shape": list(array.shape),
        "max_abs_error": difference.max().item(),
        "mean_abs_error": difference.mean().item(),
        "pytorch_vs_onnx_psnr": batch_psnr(
            onnx_tensor, pytorch_output
        ).mean().item(),
        "pytorch_vs_onnx_ssim": batch_ssim(
            onnx_tensor, pytorch_output
        ).mean().item(),
        "onnx_cpu_latency_mean_ms": float(np.mean(latencies)),
        "onnx_cpu_latency_p50_ms": float(np.percentile(latencies, 50)),
        "onnx_cpu_latency_p95_ms": float(np.percentile(latencies, 95)),
        "warmup": args.warmup,
        "repeats": args.repeats,
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_rgb(output_dir / "pytorch_output.png", pytorch_output.numpy())
    save_rgb(output_dir / "onnx_output.png", onnx_output)
    (output_dir / "alignment.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
