"""练习：补全一个最小但正确的训练 step。"""
# 中文说明：练习骨架代码，保留关键 TODO，帮助逐步实现数据集、训练循环和指标。

from __future__ import annotations

import torch


def train_step(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    criterion: torch.nn.Module,
    noisy: torch.Tensor,
    clean: torch.Tensor,
) -> float:
    # TODO: 按正确顺序完成：
    # zero_grad -> forward -> loss -> backward -> optimizer step
    # 返回 Python float。
    """中文说明：实现 `train_step` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：model、optimizer、criterion、noisy、clean。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    raise NotImplementedError


def validate_step(
    model: torch.nn.Module,
    noisy: torch.Tensor,
) -> torch.Tensor:
    # TODO:
    # - 不记录梯度；
    # - 临时切到 eval；
    # - 推理并 clamp；
    # - 恢复调用前的 train/eval 状态。
    """中文说明：实现 `validate_step` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：model、noisy。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    raise NotImplementedError


# 验收：
# - train_step 后至少一个参数发生变化。
# - validate_step 不产生 parameter.grad。
# - 输入输出 shape 相同。

