"""练习：不查看正式实现，补全 paired RGB Dataset。"""
# 中文说明：练习骨架代码，保留关键 TODO，帮助逐步实现数据集、训练循环和指标。

from __future__ import annotations

from pathlib import Path

import torch
from torch.utils.data import Dataset


class PairedDatasetExercise(Dataset):
    """中文说明：配对数据集练习骨架，留给学习者补齐读取和裁剪逻辑。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    def __init__(
        self,
        noisy_dir: str | Path,
        clean_dir: str | Path,
        patch_size: int,
        seed: int = 42,
    ) -> None:
        # TODO:
        # 1. 只接受常见图像扩展名。
        # 2. 按文件名求 noisy/clean 交集。
        # 3. 没有 pair 时抛出明确异常。
        # 4. 保存确定性 crop 所需信息。
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：noisy_dir、clean_dir、patch_size、seed。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """中文说明：返回数据集中可采样样本数量，供 DataLoader 计算 epoch 长度。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        raise NotImplementedError

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        # TODO:
        # 1. 读取为 RGB float32 CHW [0,1]。
        # 2. 检查 shape。
        # 3. noisy/clean 使用完全相同的 crop 坐标。
        # 4. 返回 noisy、clean。
        """中文说明：按索引读取一个样本，并返回训练/验证所需的张量字典。
        
        输入：index。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        raise NotImplementedError


# 验收：
# - 同一个 seed/index 两次结果完全相同。
# - noisy==clean 的输入经过 crop 后仍完全相同。
# - 错配文件、过小图像和 shape mismatch 都有测试。

