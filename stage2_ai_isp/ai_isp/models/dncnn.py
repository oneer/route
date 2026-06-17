"""
DnCNN — 小型 DnCNN 风格图像去噪网络。

参考论文：
    Zhang et al., "Beyond a Gaussian Denoiser: Residual Learning of Deep CNN
    for Image Denoising", IEEE TIP 2017.

核心思想（Residual Learning）：
    不直接预测干净图像，而是预测噪声分量：
        output = input - noise_prediction

    这样做的好处：
        - 当输入噪声很弱时，网络只需要输出接近零的残差
        - 恒等映射（identity mapping）变得容易学习
        - Batch Normalization 在小 batch 下不稳定，本实现不包含 BN

结构：
    Conv2d(in→features, 3×3) + ReLU
    → (depth-2) × [Conv2d(features→features, 3×3) + ReLU]
    → Conv2d(features→out, 3×3)
    → 可选残差连接: output = x - pred

参数说明：
    - depth:   总卷积层数（含首尾），depth=5 时有效感受野 ≈ (2×depth+1)×(2×depth+1)
    - features: 中间层通道数
    - residual: 是否启用残差学习（True = 预测噪声，False = 直接预测干净图像）
"""

from __future__ import annotations

import torch
from torch import nn


class DnCNN(nn.Module):
    """小型 DnCNN 风格去噪器。

    当 residual=True（默认）时，网络预测噪声分量，forward 返回 x - noise_pred。
    当 residual=False 时，网络直接预测干净图像。

    参数：
        in_channels:  输入通道数，默认 3
        out_channels: 输出通道数，默认 3
        features:     中间特征通道数，默认 32
        depth:        卷积层总数，默认 5
        residual:     是否使用残差学习，默认 True
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        features: int = 32,
        depth: int = 5,
        residual: bool = True,
    ) -> None:
        super().__init__()
        self.residual = bool(residual)

        # 构建卷积层列表
        layers: list[nn.Module] = [
            # 第 1 层：输入 → 特征空间（无 BN，用 ReLU）
            nn.Conv2d(in_channels, features, 3, padding=1),
            nn.ReLU(inplace=True),
        ]

        # 中间层：共 depth-2 层 Conv + ReLU
        for _ in range(max(0, depth - 2)):
            layers += [
                nn.Conv2d(features, features, 3, padding=1),
                nn.ReLU(inplace=True),
            ]

        # 最后一层：特征 → 输出（无激活函数，输出噪声/干净图的残差）
        layers.append(nn.Conv2d(features, out_channels, 3, padding=1))

        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播。

        参数：
            x: 输入噪声图像，形状 (B, in_channels, H, W)

        返回：
            - residual=True:  去噪图像 = x - net(x)（从输入中减去预测的噪声）
            - residual=False: 去噪图像 = net(x)（直接预测干净图像）
        """
        pred = self.net(x)
        out = x - pred if self.residual else pred
        return out
