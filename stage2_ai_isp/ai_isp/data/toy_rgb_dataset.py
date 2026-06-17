"""
Toy RGB 去噪数据集 —— 用程序化生成的合成图像构造 clean/noisy 配对数据。

用途：
    这是一个受控的 sanity-check 数据集，不是真实照片数据集。
    它的目的是以最低的成本验证训练管线（数据加载、前向/反向传播、
    验证循环、checkpoint 保存等）是否能正常运行。

数据生成方式：
    每张 clean patch 由以下元素合成：
        1. 水平/垂直渐变（gradient）：模拟缓慢变化的亮度过渡
        2. 正弦波纹理（wave）：模拟规则性纹理
        3. 基础颜色（base_color）：随机底色
        4. 随机半透明矩形块（alpha-blended rectangles）：模拟局部遮挡或物体

    然后通过 add_gaussian_noise 加噪得到 noisy 版本。

关键设计决定：
    - 使用确定性随机种子（seed + index）使每次生成的同一索引数据一致
    - patch 尺寸、sigma 范围等超参数可在构造时配置
    - 返回字典格式：{"noisy", "clean", "sigma"}，兼容通用训练循环
"""

from __future__ import annotations

import math

import torch
from torch.utils.data import Dataset

from ai_isp.data.degradations import add_gaussian_noise, add_shot_read_noise


class ToyRGBDenoiseDataset(Dataset):
    """确定性的合成 RGB clean/noisy patch 数据集。

    Clean patch 包含渐变纹理、正弦波、矩形色块和柔和色彩背景。
    这不是真实照片数据集，而是受控的训练管线正确性验证工具。

    参数：
        size:       数据集总样本数
        patch_size: 每个 patch 的像素尺寸（正方形，patch_size × patch_size）
        sigma_min:  加噪时 sigma 的最小值
        sigma_max:  加噪时 sigma 的最大值
        seed:       随机种子（同一 seed + index 每次生成相同数据）
    """

    def __init__(
        self,
        size: int,
        patch_size: int,
        sigma_min: float,
        sigma_max: float,
        seed: int,
        noise_type: str = "gaussian",
        shot_min: float = 0.0,
        shot_max: float = 0.0,
        read_min: float = 0.0,
        read_max: float = 0.0,
    ) -> None:
        self.size = int(size)
        self.patch_size = int(patch_size)
        self.sigma_min = float(sigma_min)
        self.sigma_max = float(sigma_max)
        self.seed = int(seed)
        self.noise_type = str(noise_type)
        self.shot_min = float(shot_min)
        self.shot_max = float(shot_max)
        self.read_min = float(read_min)
        self.read_max = float(read_max)

    def __len__(self) -> int:
        """返回数据集总样本数。"""
        return self.size

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        """获取第 index 个样本。

        使用 seed + index 作为确定性随机种子，保证可复现性。

        返回：
            {"noisy": Tensor, "clean": Tensor, "sigma": Tensor}
            noisy/clean 的形状均为 (3, patch_size, patch_size)，值域 [0, 1]
        """
        # 用确定性种子创建随机数生成器（seed + index 保证每个样本独立但可复现）
        generator = torch.Generator().manual_seed(self.seed + int(index))

        # 生成干净图像
        clean = self._make_clean_patch(generator)

        # 加噪（sigma 在 [sigma_min, sigma_max] 内随机采样）
        if self.noise_type == "shot_read":
            noisy, noise_meta = add_shot_read_noise(
                clean,
                self.shot_min,
                self.shot_max,
                self.read_min,
                self.read_max,
                generator=generator,
            )
            sigma = noise_meta["read"]
        else:
            noisy, sigma = add_gaussian_noise(
                clean, self.sigma_min, self.sigma_max, generator=generator
            )

        return {
            "noisy": noisy,                                       # 加噪后的输入图像
            "clean": clean,                                       # 原始的干净图像（监督信号）
            "sigma": torch.tensor(sigma, dtype=torch.float32),   # 实际使用的噪声水平
        }

    def _make_clean_patch(self, generator: torch.Generator) -> torch.Tensor:
        """生成一张程序化合成的 RGB clean patch。

        生成步骤：
            1. 创建像素坐标网格 (yy, xx)，范围 [0, 1]
            2. 对三个通道分别生成：
               - 随机相位/频率的正弦波纹理
               - 水平+垂直渐变
               - 随机基础底色
            3. 叠加 3 个随机半透明矩形块（模拟物体遮挡）

        参数：
            generator: PyTorch 随机数生成器

        返回：
            形状为 (3, patch_size, patch_size) 的 RGB 张量，值域 [0, 1]
        """
        h = w = self.patch_size

        # 创建 [0, 1] 范围的像素坐标网格（indexing="ij" 表示矩阵坐标）
        yy, xx = torch.meshgrid(
            torch.linspace(0.0, 1.0, h),
            torch.linspace(0.0, 1.0, w),
            indexing="ij",
        )

        # 随机参数：相位（[0, 2π]）、频率（1~4）、基础底色（0.25~0.7）
        phase = torch.rand(3, generator=generator) * math.tau  # tau = 2π
        freq = torch.randint(1, 5, (3,), generator=generator).float()
        base_color = torch.rand(3, 1, 1, generator=generator) * 0.45 + 0.25

        # 逐通道构建：渐变 + 正弦纹理
        channels = []
        for c in range(3):
            # 水平+垂直渐变（占总亮度的 ~80%）
            gradient = 0.45 * xx + 0.35 * yy
            # 正弦波纹理（振幅 0.12，约占总亮度的 ~12%）
            wave = 0.12 * torch.sin((xx * freq[c] + yy * (freq[c] + 1)) * math.tau + phase[c])
            # 叠加：底色 + 渐变 + 纹理
            channels.append(base_color[c] + gradient + wave)

        # (3, H, W) 形状的 RGB 张量
        clean = torch.stack(channels, dim=0)

        # 叠加 3 个随机半透明矩形块
        for _ in range(3):
            # 随机矩形位置和尺寸
            x0 = int(torch.randint(0, max(1, w - 8), (1,), generator=generator).item())
            y0 = int(torch.randint(0, max(1, h - 8), (1,), generator=generator).item())
            rw = int(torch.randint(6, max(7, w // 2), (1,), generator=generator).item())
            rh = int(torch.randint(6, max(7, h // 2), (1,), generator=generator).item())

            # 随机矩形颜色和透明度（alpha 0.25~0.75）
            color = torch.rand(3, 1, 1, generator=generator)
            alpha = torch.rand((), generator=generator).item() * 0.5 + 0.25

            # Alpha 混合：new = old × (1-alpha) + color × alpha
            clean[:, y0 : min(h, y0 + rh), x0 : min(w, x0 + rw)] = (
                clean[:, y0 : min(h, y0 + rh), x0 : min(w, x0 + rw)] * (1.0 - alpha)
                + color * alpha
            )

        # 最终 clamp 到 [0, 1]
        return torch.clamp(clean, 0.0, 1.0)
