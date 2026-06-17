"""
可视化工具 —— 张量转 uint8 图像与去噪结果三联图保存。

函数列表：
    - tensor_to_uint8: 将 PyTorch 张量转换为 numpy uint8 数组（H, W, 3）
    - save_triplet:    保存 noisy / output / clean 三栏并排对比图
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image


def tensor_to_uint8(image: torch.Tensor) -> np.ndarray:
    """将 PyTorch 张量转换为 uint8 numpy 数组（用于 PIL 保存）。

    处理流程：
        1. detach + cpu：从计算图中分离并移回 CPU
        2. clamp 到 [0, 1]：防止越界值
        3. 如果是 4D batch 张量（B, C, H, W），取第一个样本
        4. permute (C, H, W) → (H, W, C)：适配 numpy/PIL 的 HWC 格式
        5. 缩放到 [0, 255] 并四舍五入为 uint8

    参数：
        image: 输入张量，支持 (C, H, W) 或 (B, C, H, W)

    返回：
        numpy uint8 数组，形状 (H, W, 3)
    """
    # 从计算图分离并移回 CPU，clamp 到合法范围
    image = image.detach().cpu().clamp(0.0, 1.0)

    # 如果是 4D batch 张量，取第一个样本
    if image.ndim == 4:
        image = image[0]

    # (C, H, W) → (H, W, C)：PyTorch 用 CHW，PIL/numpy 用 HWC
    array = image.permute(1, 2, 0).numpy()

    # [0, 1] → [0, 255] uint8（+0.5 做四舍五入）
    return (array * 255.0 + 0.5).astype(np.uint8)


def save_triplet(noisy: torch.Tensor, output: torch.Tensor, target: torch.Tensor, path: str | Path) -> None:
    """保存 noisy / output / clean 三栏水平拼接对比图。

    生成的图片从左到右依次为：加噪输入 → 模型输出 → 干净目标。
    用于可视化训练过程中模型去噪效果的变化。

    参数：
        noisy:  加噪输入图像，形状 (B, C, H, W) 或 (C, H, W)
        output: 模型输出图像，形状同上
        target: 干净目标图像，形状同上
        path:   输出 PNG 文件路径（自动创建父目录）
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 分别转换三张图为 uint8 numpy 数组
    panels = [tensor_to_uint8(noisy), tensor_to_uint8(output), tensor_to_uint8(target)]

    # 沿宽度方向（axis=1）水平拼接
    grid = np.concatenate(panels, axis=1)

    # 保存为 PNG
    Image.fromarray(grid).save(path)
