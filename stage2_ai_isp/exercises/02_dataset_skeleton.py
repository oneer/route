"""练习：不查看正式实现，补全 paired RGB Dataset。"""

from __future__ import annotations

from pathlib import Path

import torch
from torch.utils.data import Dataset


class PairedDatasetExercise(Dataset):
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
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        # TODO:
        # 1. 读取为 RGB float32 CHW [0,1]。
        # 2. 检查 shape。
        # 3. noisy/clean 使用完全相同的 crop 坐标。
        # 4. 返回 noisy、clean。
        raise NotImplementedError


# 验收：
# - 同一个 seed/index 两次结果完全相同。
# - noisy==clean 的输入经过 crop 后仍完全相同。
# - 错配文件、过小图像和 shape mismatch 都有测试。

