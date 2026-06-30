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
    SSIM 使用 11×11、sigma=1.5 的 Gaussian 窗口，按 RGB 通道计算后平均。
    该实现用于仓库内部统一评估；与外部 benchmark 对比时仍需确认颜色空间、
    border crop、量化方式和官方评测脚本完全一致。
"""
# 中文说明：实现批量 PSNR 与 SSIM，供验证和离线评估复用。

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
    # 中文说明：按 batch 计算 PSNR，数值越高表示预测图像越接近目标图像。
    # 逐样本、逐通道、逐像素的均方误差（dim=(1,2,3) 在 C/H/W 上平均）
    mse = torch.mean((pred - target) ** 2, dim=(1, 2, 3))

    # PSNR = 10 × log₁₀(1 / MSE)，MAX² = 1² = 1
    return 10.0 * torch.log10(1.0 / torch.clamp(mse, min=eps))


def _gaussian_window(
    channels: int,
    window_size: int,
    sigma: float,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """中文说明：实现 `_gaussian_window` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：channels、window_size、sigma、device、dtype。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    coordinates = torch.arange(window_size, device=device, dtype=dtype)
    coordinates = coordinates - (window_size - 1) / 2
    gaussian = torch.exp(-(coordinates * coordinates) / (2 * sigma * sigma))
    gaussian = gaussian / gaussian.sum()
    window_2d = gaussian[:, None] * gaussian[None, :]
    return window_2d.expand(channels, 1, window_size, window_size).contiguous()


def batch_ssim(
    pred: torch.Tensor,
    target: torch.Tensor,
    window_size: int = 11,
    sigma: float = 1.5,
) -> torch.Tensor:
    """计算 batch 内每个样本的标准窗口 SSIM。

    参数：
        pred:   预测图像，形状 (B, C, H, W)，值域 [0, 1]
        target: 目标图像，形状 (B, C, H, W)，值域 [0, 1]

    返回：
        SSIM 值，形状 (B,)，范围通常 [0, 1]（越高越好）

    实现细节：
        使用 11×11 Gaussian 核计算局部均值和方差，
        groups=channels 实现逐通道独立计算。卷积不做 padding，
        避免人工零边界影响统计。
        C₁=(0.01)², C₂=(0.03)² 参考 Wang et al. 2004 的默认参数。
    """
    # 中文说明：按 batch 计算 SSIM，关注结构相似度而不只是像素误差。
    # SSIM 稳定常数（参考原始论文的默认值）
    c1 = 0.01 ** 2
    c2 = 0.03 ** 2

    if pred.shape != target.shape:
        raise ValueError(
            f"SSIM expects identical shapes, got {tuple(pred.shape)} and {tuple(target.shape)}"
        )
    if pred.ndim != 4:
        raise ValueError(f"SSIM expects BCHW tensors, got shape {tuple(pred.shape)}")
    effective_size = min(window_size, pred.shape[-2], pred.shape[-1])
    if effective_size % 2 == 0:
        effective_size -= 1
    if effective_size < 1:
        raise ValueError("SSIM requires non-empty spatial dimensions.")
    kernel = _gaussian_window(
        pred.shape[1], effective_size, sigma, pred.device, pred.dtype
    )

    # --- 局部均值 ---
    # μₓ = conv(x, kernel)，groups=channels 使每个通道独立计算
    mu_x = F.conv2d(pred, kernel, groups=pred.shape[1])
    mu_y = F.conv2d(target, kernel, groups=target.shape[1])

    # --- 局部方差与协方差 ---
    # σₓ² = conv(x², kernel) - μₓ²（Var(X) = E[X²] - E[X]²）
    sigma_x = F.conv2d(pred * pred, kernel, groups=pred.shape[1]) - mu_x * mu_x
    sigma_y = F.conv2d(target * target, kernel, groups=target.shape[1]) - mu_y * mu_y
    # σₓᵧ = conv(xy, kernel) - μₓμᵧ
    sigma_xy = F.conv2d(pred * target, kernel, groups=pred.shape[1]) - mu_x * mu_y

    # --- SSIM 公式 ---
    # SSIM = (2μₓμᵧ + C₁)(2σₓᵧ + C₂) / ((μₓ² + μᵧ² + C₁)(σₓ² + σᵧ² + C₂))
    numerator = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    denominator = (mu_x * mu_x + mu_y * mu_y + c1) * (sigma_x + sigma_y + c2)

    # 在 C, H, W 维度取平均得到每个样本的 SSIM
    return torch.mean(numerator / torch.clamp(denominator, min=1e-8), dim=(1, 2, 3))
