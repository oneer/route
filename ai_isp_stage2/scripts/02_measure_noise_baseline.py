#!/usr/bin/env python3
"""Measure noisy-input quality for one or more RGB denoise configs."""

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
    parser = argparse.ArgumentParser(description="Measure clean/noisy baseline metrics.")
    parser.add_argument("--config", action="append", required=True, help="Path to YAML config.")
    return parser.parse_args()


def resolve_project_path(path: str | Path) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else ROOT / resolved


def build_val_dataset(config: dict):
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
