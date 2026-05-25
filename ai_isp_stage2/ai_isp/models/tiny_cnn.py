"""
TinyCNN — 最简 3 层卷积 Baseline。

结构：
    Conv2d(3→features, 3×3) → ReLU →
    Conv2d(features→features, 3×3) → ReLU →
    Conv2d(features→3, 3×3)

特点：
    - 仅 3 层卷积，无下采样、无 skip connection、无 BN
    - 参数量极少，训练极快
    - 感受野 = 5×5（两层 3×3 卷积的有效感受野）
    - 适合作为"训练管线是否跑通"的最简验证模型

用途：
    Week 0.5 训练管线检查 —— 确保数据流动、loss 下降、checkpoint 保存等
    基础设施正常工作，再切换到更复杂的模型。
"""

from __future__ import annotations

import torch
from torch import nn


class TinyCNN(nn.Module):
    """3 层纯卷积去噪网络 —— Week 0.5 训练管线检查用 Baseline。

    参数：
        in_channels:  输入通道数，默认 3（RGB 噪声图）
        out_channels: 输出通道数，默认 3（RGB 去噪图）
        features:     中间层特征通道数，默认 32
    """

    def __init__(self, in_channels: int = 3, out_channels: int = 3, features: int = 32) -> None:
        super().__init__()

        # Sequential 堆叠 3 层卷积 + 2 层 ReLU
        # padding=1 保持空间尺寸不变
        self.net = nn.Sequential(
            # 第 1 层：输入 → 特征空间
            nn.Conv2d(in_channels, features, 3, padding=1),
            nn.ReLU(inplace=True),

            # 第 2 层：特征 → 特征（非线性变换）
            nn.Conv2d(features, features, 3, padding=1),
            nn.ReLU(inplace=True),

            # 第 3 层：特征 → 输出（直接预测干净图像）
            nn.Conv2d(features, out_channels, 3, padding=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播：噪声图 → 去噪图。

        参数：
            x: 输入张量，形状 (B, in_channels, H, W)

        返回：
            输出去噪后张量，形状 (B, out_channels, H, W)
        """
        return self.net(x)
