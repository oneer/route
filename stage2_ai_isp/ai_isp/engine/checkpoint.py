"""
Checkpoint 管理 —— 保存并恢复训练状态。

保存内容：
    - model:     模型权重（state_dict）
    - optimizer: 优化器状态（state_dict，含动量等）
    - step:      当前训练步数
    - best_psnr: 历史最佳 PSNR 值
    - config:    完整配置字典（用于追溯训练超参数）

保存策略：
    - last.pth:     每个 val_every 步都更新（最新状态）
    - best_psnr.pth: 仅当验证 PSNR 超过历史最佳时更新
"""

from __future__ import annotations

from pathlib import Path

import torch


def save_checkpoint(
    path: str | Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    step: int,
    best_psnr: float,
    config: dict,
) -> None:
    """保存训练 checkpoint 到指定路径。

    参数：
        path:       输出文件路径（自动创建父目录）
        model:      待保存的模型
        optimizer:  待保存的优化器
        step:       当前训练步数
        best_psnr:  历史最佳验证 PSNR
        config:     完整配置字典
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model": model.state_dict(),          # 模型权重
            "optimizer": optimizer.state_dict(),  # 优化器状态
            "step": step,                         # 当前步数
            "best_psnr": best_psnr,               # 历史最佳 PSNR
            "config": config,                     # 训练配置（完整追溯）
        },
        path,
    )


def load_checkpoint(
    path: str | Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    map_location: str | torch.device = "cpu",
) -> dict:
    """恢复模型以及可选的优化器状态，并返回完整 checkpoint。"""
    checkpoint = torch.load(Path(path), map_location=map_location)
    state_dict = checkpoint["model"] if "model" in checkpoint else checkpoint
    model.load_state_dict(state_dict)
    if optimizer is not None and "optimizer" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer"])
    return checkpoint
