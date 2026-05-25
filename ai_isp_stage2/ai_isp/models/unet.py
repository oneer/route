"""
UNet — 紧凑型 Encoder-Decoder 去噪网络。

结构：
    Encoder（2 层下采样）:
        enc1: ConvBlock(in→base)         — 原始分辨率
        enc2: ConvBlock(base→base×2)     — 1/2 分辨率（AvgPool 下采样）
    Bottleneck:
        bottleneck: ConvBlock(base×2→base×4) — 1/4 分辨率
    Decoder（2 层上采样 + Skip Connection）:
        dec2: ConvBlock((base×4 + base×2)→base×2) — 1/2 分辨率
        dec1: ConvBlock((base×2 + base)→base)      — 原始分辨率
    Output:
        Conv2d(base→out, 1×1)

特点：
    - 使用 AvgPool2d 下采样（而非 stride=2 卷积），更平滑
    - 使用 bilinear interpolation 上采样（而非转置卷积），减少 checkerboard 伪影
    - Skip Connection 将 encoder 特征直接拼接到 decoder，保留细节信息
    - 无 Batch Normalization（UNet 结构中对小 batch 不太敏感）

ConvBlock 说明：
    每个 ConvBlock 包含两层 3×3 Conv + ReLU，用于局部非线性特征提取。
"""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class ConvBlock(nn.Module):
    """基础卷积模块：两层 3×3 Conv + ReLU。

    用于 UNet 的 encoder、bottleneck 和 decoder 各阶段。
    padding=1 保持空间尺寸不变。

    参数：
        in_channels:  输入通道数
        out_channels: 输出通道数
    """

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            # 第 1 层：输入 → 输出通道
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            # 第 2 层：输出通道 → 输出通道（进一步非线性变换）
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播：输入 → 两层卷积 + ReLU → 输出。"""
        return self.net(x)


class UNet(nn.Module):
    """紧凑型 UNet —— RGB 图像去噪 Baseline。

    结构概要：
        input (B, 3, H, W)
          → enc1     (B, c,   H,   W)
          → AvgPool  (B, c,   H/2, W/2)
          → enc2     (B, 2c,  H/2, W/2)
          → AvgPool  (B, 2c,  H/4, W/4)
          → bottleneck (B, 4c, H/4, W/4)
          → Upsample (B, 4c,  H/2, W/2) + concat(enc2) → dec2 (B, 2c, H/2, W/2)
          → Upsample (B, 2c,  H,   W)   + concat(enc1) → dec1 (B, c,  H,   W)
          → Conv1×1  (B, 3,  H,   W)

    参数：
        in_channels:   输入通道数，默认 3（RGB 噪声图）
        out_channels:  输出通道数，默认 3（RGB 去噪图）
        base_channels: 基础通道数 c，每层翻倍（c → 2c → 4c），默认 16
    """

    def __init__(self, in_channels: int = 3, out_channels: int = 3, base_channels: int = 16) -> None:
        super().__init__()
        c = int(base_channels)

        # Encoder（下采样路径）
        self.enc1 = ConvBlock(in_channels, c)      # 原始分辨率
        self.enc2 = ConvBlock(c, c * 2)            # 1/2 分辨率

        # Bottleneck（最低分辨率）
        self.bottleneck = ConvBlock(c * 2, c * 4)   # 1/4 分辨率

        # Decoder（上采样路径 + Skip Connection）
        # dec2 输入 = bottleneck 上采样后的 4c + enc2 的 skip 2c = 6c
        self.dec2 = ConvBlock(c * 4 + c * 2, c * 2)
        # dec1 输入 = dec2 上采样后的 2c + enc1 的 skip c = 3c
        self.dec1 = ConvBlock(c * 2 + c, c)

        # 输出层：1×1 卷积将特征映射到输出通道
        self.out = nn.Conv2d(c, out_channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播：Encoder → Bottleneck → Decoder（含 Skip Connection）。

        参数：
            x: 输入噪声图像，形状 (B, in_channels, H, W)

        返回：
            去噪图像，形状 (B, out_channels, H, W)
        """
        # --- Encoder ---
        e1 = self.enc1(x)                                      # (B, c,   H,   W)
        e2 = self.enc2(F.avg_pool2d(e1, 2))                    # (B, 2c,  H/2, W/2) — 2× 下采样

        # --- Bottleneck ---
        b = self.bottleneck(F.avg_pool2d(e2, 2))               # (B, 4c,  H/4, W/4) — 4× 下采样

        # --- Decoder（上采样 + Skip Connection）---
        # 上采样 bottleneck 并与 enc2 拼接
        d2 = F.interpolate(b, size=e2.shape[-2:], mode="bilinear", align_corners=False)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))             # (B, 2c,  H/2, W/2)

        # 上采样 dec2 并与 enc1 拼接
        d1 = F.interpolate(d2, size=e1.shape[-2:], mode="bilinear", align_corners=False)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))             # (B, c,   H,   W)

        # --- 输出 ---
        return self.out(d1)                                    # (B, out_channels, H, W)
