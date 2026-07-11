"""Stage 3 C++ ISP 与 Stage 4 ONNX Runtime 之间的桥接工具。

Stage 3 使用 HWC 排列的 CPF32 浮点图像，Stage 4 模型使用 NCHW 排列的
四维张量。本模块集中处理文件读写、布局转换和桥接结果的 PSNR 计算，避免
桥接脚本中重复实现二进制协议。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def write_cpf32(path: Path, array: np.ndarray) -> None:
    """把 HWC 浮点图像写成 Stage 3 约定的 CPF32 小端二进制文件。"""
    array = np.asarray(array, dtype=np.float32)
    if array.ndim != 3:
        raise ValueError(f"CPF32 bridge expects HWC, got {array.shape}")
    height, width, channels = array.shape
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        # 文件头保存魔数和逻辑尺寸；像素区按 HWC/C 顺序连续存放 float32。
        handle.write(f"CPF32\n{width} {height} {channels}\n".encode("ascii"))
        handle.write(array.astype("<f4", copy=False).tobytes(order="C"))


def read_cpf32(path: Path) -> np.ndarray:
    """读取 CPF32 文件，并校验魔数及像素数量是否与文件头一致。"""
    with path.open("rb") as handle:
        if handle.readline().strip() != b"CPF32":
            raise ValueError(f"Invalid CPF32 magic: {path}")
        width, height, channels = map(int, handle.readline().split())
        payload = np.frombuffer(handle.read(), dtype="<f4")
    expected = width * height * channels
    if payload.size != expected:
        raise ValueError(f"CPF32 payload mismatch: {payload.size} != {expected}")
    return payload.reshape(height, width, channels)


def hwc_to_nchw(array: np.ndarray) -> np.ndarray:
    """将单张 HWC RGB 图像转换为模型要求的 1x3xHxW 张量。"""
    array = np.asarray(array, dtype=np.float32)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Expected HWC RGB, got {array.shape}")
    return np.transpose(array, (2, 0, 1))[None].astype(np.float32, copy=False)


def psnr(prediction: np.ndarray, target: np.ndarray, eps: float = 1e-8) -> float:
    """按峰值 1.0 计算 PSNR；eps 用于避免完全一致时除零。"""
    if prediction.shape != target.shape:
        raise ValueError(f"PSNR shape mismatch: {prediction.shape} != {target.shape}")
    mse = float(np.mean((prediction.astype(np.float64) - target.astype(np.float64)) ** 2))
    return float(10.0 * np.log10(1.0 / max(mse, eps)))
