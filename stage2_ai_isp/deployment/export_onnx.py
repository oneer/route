#!/usr/bin/env python3
"""Export a Stage 2 checkpoint to ONNX for C++ inference experiments."""
# 中文说明：部署验证脚本代码，用于导出 ONNX、准备 C++ 对齐张量、比较不同后端输出。

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_isp.models import build_model


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Export a Stage 2 model to ONNX.")
    parser.add_argument("--config", required=True, help="Training config YAML.")
    parser.add_argument("--checkpoint", required=True, help="Checkpoint path.")
    parser.add_argument("--output", required=True, help="Output ONNX path.")
    parser.add_argument("--height", type=int, default=128, help="Input height.")
    parser.add_argument("--width", type=int, default=128, help="Input width.")
    parser.add_argument("--opset", type=int, default=17)
    return parser.parse_args()


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    model = build_model(config["model"]).eval()
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    state_dict = checkpoint["model"] if "model" in checkpoint else checkpoint
    model.load_state_dict(state_dict)

    in_channels = int(config["model"].get("in_channels", 3))
    dummy = torch.randn(1, in_channels, args.height, args.width)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy,
        output,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch", 2: "height", 3: "width"},
            "output": {0: "batch", 2: "height", 3: "width"},
        },
        opset_version=args.opset,
        dynamo=False,
    )
    try:
        import onnx

        exported = onnx.load(str(output))
        onnx.checker.check_model(exported)
    except ImportError:
        print("warning: onnx is not installed; skipped onnx.checker validation")
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
