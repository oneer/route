#!/usr/bin/env python3
"""Compare a quantized PNG backend output against a reference output PNG."""
# 中文说明：部署验证脚本代码，用于导出 ONNX、准备 C++ 对齐张量、比较不同后端输出。

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
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", default="opencv_dnn_cpp")
    return parser.parse_args()


def load(path: str) -> torch.Tensor:
    """中文说明：实现 `load` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    array = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(np.transpose(array, (2, 0, 1))[None].copy())


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
