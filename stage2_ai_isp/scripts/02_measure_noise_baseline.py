#!/usr/bin/env python3
"""Measure noisy-input quality for one or more RGB denoise configs."""
# 中文说明：直接评估 noisy 输入相对 clean 目标的基线质量。

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import torch
from torch.utils.data import DataLoader
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.data.paired_image_dataset import PairedImageDenoiseDataset
from ai_isp.data.toy_rgb_dataset import ToyRGBDenoiseDataset
from ai_isp.metrics.psnr_ssim import batch_psnr, batch_ssim


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Measure clean/noisy baseline metrics.")
    parser.add_argument("--config", action="append", required=True, help="Path to YAML config.")
    return parser.parse_args()


def resolve_project_path(path: str | Path) -> Path:
    """中文说明：把配置中的相对路径解析到项目根目录下，避免从不同工作目录运行时路径漂移。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    resolved = Path(path)
    return resolved if resolved.is_absolute() else ROOT / resolved


def build_val_dataset(config: dict):
    """中文说明：构造后续流程需要的对象或可视化产物，把零散配置集中成可复用结果。
    
    输入：config。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    if config["data"].get("dataset", "toy_rgb") == "paired_image":
        val_cfg = config["data"]["val"]
        return PairedImageDenoiseDataset(
            noisy_dir=resolve_project_path(val_cfg["noisy_dir"]),
            clean_dir=resolve_project_path(val_cfg["clean_dir"]),
            patch_size=config["data"]["patch_size"],
            size=config["data"]["val_size"],
            seed=config["experiment"].get("seed", 42) + 10000,
        )

    noise_cfg = config["data"]["noise"]
    return ToyRGBDenoiseDataset(
        size=config["data"]["val_size"],
        patch_size=config["data"]["patch_size"],
        sigma_min=noise_cfg.get("sigma_min", 0.0),
        sigma_max=noise_cfg.get("sigma_max", 0.0),
        seed=config["experiment"].get("seed", 42) + 10000,
        noise_type=noise_cfg.get("type", "gaussian"),
        shot_min=noise_cfg.get("shot_min", 0.0),
        shot_max=noise_cfg.get("shot_max", 0.0),
        read_min=noise_cfg.get("read_min", 0.0),
        read_max=noise_cfg.get("read_max", 0.0),
    )


def measure(config_path: Path) -> dict[str, float | str]:
    """中文说明：实现 `measure` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：config_path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    dataset = build_val_dataset(config)
    loader = DataLoader(dataset, batch_size=config["train"]["batch_size"], shuffle=False)

    psnr_values = []
    ssim_values = []
    for batch in loader:
        noisy = batch["noisy"]
        clean = batch["clean"]
        psnr_values.append(batch_psnr(noisy, clean))
        ssim_values.append(batch_ssim(noisy, clean))

    psnr = torch.cat(psnr_values).mean().item()
    ssim = torch.cat(ssim_values).mean().item()
    return {
        "config": str(config_path),
        "noise": config["data"]["noise"].get("type", "gaussian"),
        "patch_size": config["data"]["patch_size"],
        "val_size": config["data"]["val_size"],
        "input_psnr": psnr,
        "input_ssim": ssim,
    }


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    print("config,noise,patch_size,val_size,input_psnr,input_ssim")
    for config in args.config:
        row = measure(Path(config))
        print(
            f"{row['config']},{row['noise']},{row['patch_size']},{row['val_size']},"
            f"{row['input_psnr']:.4f},{row['input_ssim']:.5f}"
        )


if __name__ == "__main__":
    main()
