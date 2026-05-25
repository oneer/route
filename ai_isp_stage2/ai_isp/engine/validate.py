"""
验证循环 —— 在验证集上评估模型性能。

函数 validate(model, loader, device):
    1. 切换模型到 eval 模式（禁用 dropout/BN 训练行为）
    2. 遍历验证集，计算每个 batch 的 PSNR 和 SSIM
    3. 收集首个 batch 的 noisy/output/clean 三元组（供可视化）
    4. 恢复模型到 train 模式
    5. 返回聚合指标和首帧数据

使用 @torch.no_grad() 装饰器禁用梯度计算，节省显存和加速推理。
"""

from __future__ import annotations

import torch
from torch.utils.data import DataLoader

from ai_isp.metrics import batch_psnr, batch_ssim


@torch.no_grad()
def validate(model: torch.nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float | torch.Tensor]:
    """在验证集上评估模型性能。

    参数：
        model:  待评估的模型
        loader: 验证集 DataLoader
        device: 计算设备（cuda / cpu）

    返回：
        字典包含以下键：
            - "psnr":       平均 PSNR（float，dB）
            - "ssim":       平均 SSIM（float）
            - "first_batch": 首个 batch 的 {"noisy", "output", "clean"} 张量字典
                            （仅第一个样本，已 detach 到 CPU，供可视化保存）
    """
    # 切换到评估模式（禁用 dropout、BN 统计更新等）
    model.eval()

    psnr_values = []   # 收集所有 batch 的 PSNR
    ssim_values = []   # 收集所有 batch 的 SSIM
    first_batch = None  # 首个 batch 的数据（用于可视化）

    for batch in loader:
        # 数据移入计算设备
        noisy = batch["noisy"].to(device)
        clean = batch["clean"].to(device)

        # 模型推理并 clamp 到 [0, 1]（模型输出可能超出合法值域）
        output = torch.clamp(model(noisy), 0.0, 1.0)

        # 计算指标并移回 CPU（detach 切断梯度图）
        psnr_values.append(batch_psnr(output, clean).detach().cpu())
        ssim_values.append(batch_ssim(output, clean).detach().cpu())

        # 保存首个 batch 的第一个样本用于可视化
        if first_batch is None:
            first_batch = {
                "noisy": noisy[:1].detach().cpu(),     # (1, C, H, W)
                "output": output[:1].detach().cpu(),   # (1, C, H, W)
                "clean": clean[:1].detach().cpu(),     # (1, C, H, W)
            }

    # 恢复训练模式
    model.train()

    return {
        "psnr": torch.cat(psnr_values).mean().item(),   # 所有 batch PSNR 的平均
        "ssim": torch.cat(ssim_values).mean().item(),   # 所有 batch SSIM 的平均
        "first_batch": first_batch,                      # 首帧数据供可视化
    }
