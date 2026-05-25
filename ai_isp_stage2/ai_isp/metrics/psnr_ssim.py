"""
PSNR 与 SSIM 批量计算函数。

PSNR（峰值信噪比）：
    PSNR = 10 × log₁₀(MAX² / MSE)
    其中 MAX = 1.0（图像已归一化到 [0, 1]），MSE = 逐像素均方误差。
    值越高表示图像质量越好（典型范围：20~50 dB）。

SSIM（结构相似度）：
    SSIM(x, y) = (2μₓμᵧ + C₁)(2σₓᵧ + C₂) / ((μₓ² + μᵧ² + C₁)(σₓ² + σᵧ² + C₂))
    其中 μ 为局部均值，σ 为局部标准差/协方差，C₁=(0.01)², C₂=(0.03)² 为稳定常数。
    值越接近 1 表示结构越相似。

计算方式：
    两个函数都使用 3×3 平均池化核做局部统计（作为简化的 SSIM 实现），
    返回 batch 内每个样本的指标值（形状为 (B,)），外层再取 mean 得到标量。
"""

from __future__ import annotations

import torch
from torch.nn import functional as F


def batch_psnr(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """计算 batch 内每个样本的 PSNR。

    参数：
        pred:   预测图像，形状 (B, C, H, W)，值域 [0, 1]
        target: 目标图像，形状 (B, C, H, W)，值域 [0, 1]
        eps:    防止 log(0) 的极小值

    返回：
        PSNR 值，形状 (B,)，单位 dB
    """
    # 逐样本、逐通道、逐像素的均方误差（dim=(1,2,3) 在 C/H/W 上平均）
    mse = torch.mean((pred - target) ** 2, dim=(1, 2, 3))

    # PSNR = 10 × log₁₀(1 / MSE)，MAX² = 1² = 1
    return 10.0 * torch.log10(1.0 / torch.clamp(mse, min=eps))


def batch_ssim(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """计算 batch 内每个样本的 SSIM（简化实现，用于验证 sanity check）。

    参数：
        pred:   预测图像，形状 (B, C, H, W)，值域 [0, 1]
        target: 目标图像，形状 (B, C, H, W)，值域 [0, 1]

    返回：
        SSIM 值，形状 (B,)，范围通常 [0, 1]（越高越好）

    实现细节：
        使用 3×3 均匀卷积核计算局部均值和方差，
        groups=channels 实现逐通道独立计算。
        C₁=(0.01)², C₂=(0.03)² 参考 Wang et al. 2004 的默认参数。
    """
    # SSIM 稳定常数（参考原始论文的默认值）
    c1 = 0.01 ** 2
    c2 = 0.03 ** 2

    # 3×3 均匀平均核（权重 1/9），用于局部统计
    kernel = torch.ones((pred.shape[1], 1, 3, 3), device=pred.device, dtype=pred.dtype) / 9.0

    # --- 局部均值 ---
    # μₓ = conv(x, kernel)，groups=channels 使每个通道独立计算
    mu_x = F.conv2d(pred, kernel, padding=1, groups=pred.shape[1])
    mu_y = F.conv2d(target, kernel, padding=1, groups=target.shape[1])

    # --- 局部方差与协方差 ---
    # σₓ² = conv(x², kernel) - μₓ²（Var(X) = E[X²] - E[X]²）
    sigma_x = F.conv2d(pred * pred, kernel, padding=1, groups=pred.shape[1]) - mu_x * mu_x
    sigma_y = F.conv2d(target * target, kernel, padding=1, groups=target.shape[1]) - mu_y * mu_y
    # σₓᵧ = conv(xy, kernel) - μₓμᵧ
    sigma_xy = F.conv2d(pred * target, kernel, padding=1, groups=pred.shape[1]) - mu_x * mu_y

    # --- SSIM 公式 ---
    # SSIM = (2μₓμᵧ + C₁)(2σₓᵧ + C₂) / ((μₓ² + μᵧ² + C₁)(σₓ² + σᵧ² + C₂))
    numerator = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    denominator = (mu_x * mu_x + mu_y * mu_y + c1) * (sigma_x + sigma_y + c2)

    # 在 C, H, W 维度取平均得到每个样本的 SSIM
    return torch.mean(numerator / torch.clamp(denominator, min=1e-8), dim=(1, 2, 3))
