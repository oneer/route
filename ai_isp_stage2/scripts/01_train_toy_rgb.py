#!/usr/bin/env python3
"""
01_train_toy_rgb.py — Stage 2 训练入口脚本。

用法:
    python scripts/01_train_toy_rgb.py --config configs/toy_rgb_tiny.yaml

功能:
    读取 YAML 配置文件，调用 ai_isp.engine.train.train_from_config() 执行完整的
    深度学习训练流程。这是 Stage 2 所有实验的统一启动入口。

配置驱动设计:
    所有超参数（模型选择、数据参数、训练步数、学习率等）都在 YAML 配置文件中定义，
    脚本本身只负责解析命令行参数和加载配置，不包含任何硬编码的超参数。
    这样不同实验之间只需切换配置文件，无需修改代码。

典型配置文件结构:
    experiment:
      seed: 42
      output_dir: output/toy_rgb_tiny
    data:
      train_size: 1000
      val_size: 100
      patch_size: 64
      noise:
        sigma_min: 0.0
        sigma_max: 0.2
    model:
      name: tiny_cnn
      in_channels: 3
      out_channels: 3
      features: 32
    train:
      steps: 1000
      batch_size: 8
      learning_rate: 0.001
      loss: l1
      device: auto
      log_every: 25
      val_every: 50
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

# 将项目根目录（ai_isp_stage2/）加入 sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.engine.train import train_from_config


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    返回:
        argparse.Namespace，包含:
            --config: YAML 配置文件路径（必需）
    """
    parser = argparse.ArgumentParser(description="Train toy RGB denoise baseline.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    return parser.parse_args()


def main() -> None:
    """加载 YAML 配置并启动训练。"""
    args = parse_args()

    # 读取 YAML 配置文件
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 启动配置驱动的训练流程
    train_from_config(config)


if __name__ == "__main__":
    main()
