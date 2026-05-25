"""
图像退化（degradation）模块 —— 对干净图像施加各种质量退化。

当前实现：
    - add_gaussian_noise: 添加与信号无关的高斯噪声（sigma 在指定范围内随机采样）

设计意图：
    在 AI-ISP 训练中，退化模型定义了"输入"是什么。
    这里从最简单的加性高斯白噪声开始，后续可以扩展为更复杂的退化管线：
        clean → blur → downsample → noise → JPEG → noisy
    模拟真实 ISP 输入端常见的多重退化叠加。

注意：
    所有退化操作要求输入张量的值域为 [0, 1]，输出也保持在 [0, 1] 内。
"""

from __future__ import annotations

import torch


def add_gaussian_noise(
    clean: torch.Tensor,
    sigma_min: float,
    sigma_max: float,
    generator: torch.Generator | None = None,
) -> tuple[torch.Tensor, float]:
    """对 [0, 1] 范围的干净图像添加高斯噪声。

    噪声标准差 sigma 在 [sigma_min, sigma_max] 内均匀随机采样，
    模拟不同 ISO 感光度下的噪声水平。

    参数：
        clean:      干净图像张量，形状为 (C, H, W)，值域 [0, 1]
        sigma_min:  噪声标准差最小值
        sigma_max:  噪声标准差最大值
        generator:  PyTorch 随机数生成器，用于保证可复现性

    返回：
        (noisy, sigma): 加噪后的图像张量（clamp 到 [0, 1]）与实际使用的 sigma 值
    """
    # 在 [sigma_min, sigma_max] 区间均匀随机采样一个 sigma
    sigma = (
        torch.rand((), generator=generator, dtype=clean.dtype)
        .mul_(sigma_max - sigma_min)  # 缩放到区间宽度
        .add_(sigma_min)              # 平移到 sigma_min
        .item()
    )

    # 生成高斯噪声并叠加
    noise = torch.randn(clean.shape, generator=generator, dtype=clean.dtype) * sigma

    # clamp 到 [0, 1] 防止像素值越界
    return torch.clamp(clean + noise, 0.0, 1.0), sigma
