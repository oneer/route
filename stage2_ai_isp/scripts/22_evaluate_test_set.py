#!/usr/bin/env python3
"""Evaluate one checkpoint on a held-out paired RGB test set."""
# 中文说明：在固定测试集上评估指定 run 的模型。

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import time

import torch
from torch.utils.data import DataLoader
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.data.paired_image_dataset import PairedImageDenoiseDataset
from ai_isp.engine.checkpoint import load_checkpoint
from ai_isp.metrics import batch_psnr, batch_ssim
from ai_isp.models import build_model


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument(
        "--noisy-dir", default="stage2_ai_isp/datasets/sidd_tiny/test/noisy"
    )
    parser.add_argument(
        "--clean-dir", default="stage2_ai_isp/datasets/sidd_tiny/test/clean"
    )
    parser.add_argument(
        "--output", default="stage2_ai_isp/reports/test_set_metrics.json"
    )
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument(
        "--patch-size",
        type=int,
        default=0,
        help="0 evaluates full images; a positive value uses deterministic crops.",
    )
    return parser.parse_args()


@torch.no_grad()
def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    with Path(args.config).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    model = build_model(config["model"]).eval()
    load_checkpoint(args.checkpoint, model)
    dataset = PairedImageDenoiseDataset(
        args.noisy_dir,
        args.clean_dir,
        patch_size=args.patch_size or None,
        size=None,
        seed=2026,
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)

    psnr_values: list[torch.Tensor] = []
    ssim_values: list[torch.Tensor] = []
    latencies_ms: list[float] = []
    for batch in loader:
        noisy = batch["noisy"]
        clean = batch["clean"]
        start = time.perf_counter()
        output = model(noisy).clamp(0.0, 1.0)
        latencies_ms.append((time.perf_counter() - start) * 1000.0)
        psnr_values.append(batch_psnr(output, clean))
        ssim_values.append(batch_ssim(output, clean))

    result = {
        "split": "held_out_test",
        "samples": len(dataset),
        "psnr": torch.cat(psnr_values).mean().item(),
        "ssim": torch.cat(ssim_values).mean().item(),
        "mean_latency_ms_cpu": sum(latencies_ms) / len(latencies_ms),
        "config": str(args.config),
        "checkpoint": str(args.checkpoint),
        "metric_protocol": "RGB float [0,1], full image by default, Gaussian SSIM",
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    csv_path = output_path.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=result.keys())
        writer.writeheader()
        writer.writerow(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
