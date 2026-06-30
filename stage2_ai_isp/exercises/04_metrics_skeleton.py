"""练习：独立实现 PSNR，并解释 SSIM 为什么不能只写一个全局公式。"""
# 中文说明：练习骨架代码，保留关键 TODO，帮助逐步实现数据集、训练循环和指标。

from __future__ import annotations

import torch


def batch_psnr_exercise(
    prediction: torch.Tensor,
    target: torch.Tensor,
    eps: float = 1e-8,
) -> torch.Tensor:
    # TODO: 返回每个 batch 样本一个 PSNR 值。
    """中文说明：实现 `batch_psnr_exercise` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：prediction、target、eps。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    raise NotImplementedError


# 验收：
# - prediction==target 时结果由 eps 决定，当前应接近 80 dB。
# - 已知 MSE=0.01 时 PSNR=20 dB。
# - shape 不一致时主动报错。
# - 写一段说明：RGB/Y、border crop、量化方式为何会改变 benchmark 数值。

