"""
随机种子统一设置工具。

在深度学习实验中，可复现性是基本要求。本模块提供 seed_everything 函数，
同时设置 Python random、NumPy、PyTorch CPU 和 CUDA 的随机种子。

注意：
    - CUDA 的确定性操作（如 cudnn.deterministic）会降低性能，此处未强制开启
    - DataLoader 的多进程数据加载仍需额外设置 worker_init_fn 才能完全确定
"""

from __future__ import annotations

import random

import numpy as np
import torch


def seed_everything(seed: int) -> None:
    """统一设置所有随机数生成器的种子。

    参数：
        seed: 随机种子整数

    影响范围：
        - Python 内置 random 模块
        - NumPy 随机数生成器
        - PyTorch CPU 随机数生成器
        - PyTorch CUDA 随机数生成器（如果可用）
    """
    # Python 内置随机
    random.seed(seed)

    # NumPy 随机
    np.random.seed(seed)

    # PyTorch CPU 随机
    torch.manual_seed(seed)

    # PyTorch CUDA 随机（如果 GPU 可用）
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
