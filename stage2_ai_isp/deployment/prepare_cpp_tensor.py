#!/usr/bin/env python3
"""Convert an RGB image to the simple NCHW float tensor format used by C++."""
# 中文说明：部署验证脚本代码，用于导出 ONNX、准备 C++ 对齐张量、比较不同后端输出。

from __future__ import annotations

import argparse
from pathlib import Path
import struct

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
