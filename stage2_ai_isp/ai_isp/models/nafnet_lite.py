"""NAFNet-lite blocks for small image restoration experiments."""
# 中文说明：实现轻量 NAFNet 风格网络，使用门控和残差缩放提升图像复原能力。

from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


class SimpleGate(nn.Module):
    """Split channels into two halves and multiply them elementwise."""
    # 中文说明：NAFNet 的简化门控单元，把通道一分为二后相乘形成非线性。

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """中文说明：定义前向传播：输入张量如何经过当前模块得到输出张量。
        
        输入：x。
        输出：返回同尺寸空间分辨率的门控特征张量。
        """
        x1, x2 = x.chunk(2, dim=1)
        return x1 * x2


class LayerNorm2d(nn.Module):
    """Channel-wise LayerNorm for NCHW tensors."""
    # 中文说明：面向 NCHW 图像张量的 LayerNorm，按通道做归一化。

    def __init__(self, channels: int, eps: float = 1e-6) -> None:
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：channels、eps。
        输出：构造函数不返回业务数据，只完成成员变量和子模块初始化。
        """
        super().__init__()
        self.weight = nn.Parameter(torch.ones(1, channels, 1, 1))
        self.bias = nn.Parameter(torch.zeros(1, channels, 1, 1))
        self.eps = float(eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """中文说明：定义前向传播：输入张量如何经过当前模块得到输出张量。
        
        输入：x。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        mean = x.mean(dim=1, keepdim=True)
        var = (x - mean).pow(2).mean(dim=1, keepdim=True)
        return (x - mean) / torch.sqrt(var + self.eps) * self.weight + self.bias


class NAFBlock(nn.Module):
    """Small NAFNet-style restoration block.

    This block keeps input/output shape unchanged. It uses SimpleGate for
    nonlinearity and a lightweight channel attention branch.
    """
    # 中文说明：NAFNet 基础残差块，结合归一化、门控、通道注意力和可学习残差缩放。

    def __init__(self, channels: int, expansion: int = 2) -> None:
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：channels、expansion。
        输出：构造函数不返回业务数据，只完成成员变量和子模块初始化。
        """
        super().__init__()
        hidden = channels * expansion
        if hidden % 2 != 0:
            hidden += 1
        gated = hidden // 2

        self.norm1 = LayerNorm2d(channels)
        self.expand = nn.Conv2d(channels, hidden, 1)
        self.depthwise = nn.Conv2d(hidden, hidden, 3, padding=1, groups=hidden)
        self.gate = SimpleGate()
        self.channel_attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(gated, gated, 1),
            nn.Sigmoid(),
        )
        self.project = nn.Conv2d(gated, channels, 1)

        self.norm2 = LayerNorm2d(channels)
        ffn_hidden = channels * expansion
        if ffn_hidden % 2 != 0:
            ffn_hidden += 1
        self.ffn_expand = nn.Conv2d(channels, ffn_hidden, 1)
        self.ffn_gate = SimpleGate()
        self.ffn_project = nn.Conv2d(ffn_hidden // 2, channels, 1)

        self.beta = nn.Parameter(torch.zeros(1, channels, 1, 1))
        self.gamma = nn.Parameter(torch.zeros(1, channels, 1, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """中文说明：定义前向传播：输入张量如何经过当前模块得到输出张量。
        
        输入：x。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        y = self.norm1(x)
        y = self.expand(y)
        y = self.depthwise(y)
        y = self.gate(y)
        y = y * self.channel_attention(y)
        y = self.project(y)
        x = x + self.beta * y

        y = self.norm2(x)
        y = self.ffn_expand(y)
        y = self.ffn_gate(y)
        y = self.ffn_project(y)
        return x + self.gamma * y


class NAFNetLite(nn.Module):
    """Compact U-shaped NAFNet-style model for paired RGB denoise."""
    # 中文说明：轻量版 NAFNet，保留核心残差/门控思想以控制参数量。

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        width: int = 16,
        middle_blocks: int = 2,
        encoder_blocks: tuple[int, ...] = (1, 1),
        decoder_blocks: tuple[int, ...] = (1, 1),
        residual: bool = False,
    ) -> None:
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：in_channels、out_channels、width、middle_blocks、encoder_blocks、decoder_blocks、residual。
        输出：构造函数不返回业务数据，只完成成员变量和子模块初始化。
        """
        super().__init__()
        if len(encoder_blocks) != len(decoder_blocks):
            raise ValueError("encoder_blocks and decoder_blocks must have the same length.")

        self.residual = bool(residual)
        self.intro = nn.Conv2d(in_channels, width, 3, padding=1)
        self.ending = nn.Conv2d(width, out_channels, 3, padding=1)

        self.encoders = nn.ModuleList()
        self.downs = nn.ModuleList()
        self.decoders = nn.ModuleList()
        self.ups = nn.ModuleList()

        channels = width
        for num_blocks in encoder_blocks:
            self.encoders.append(nn.Sequential(*[NAFBlock(channels) for _ in range(num_blocks)]))
            self.downs.append(nn.Conv2d(channels, channels * 2, 2, stride=2))
            channels *= 2

        self.middle = nn.Sequential(*[NAFBlock(channels) for _ in range(middle_blocks)])

        for num_blocks in decoder_blocks:
            self.ups.append(
                nn.Sequential(
                    nn.Conv2d(channels, channels * 2, 1),
                    nn.PixelShuffle(2),
                )
            )
            channels //= 2
            self.decoders.append(nn.Sequential(*[NAFBlock(channels) for _ in range(num_blocks)]))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """中文说明：定义前向传播：输入张量如何经过当前模块得到输出张量。
        
        输入：x。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        original_h, original_w = x.shape[-2:]
        padded = self._pad_to_multiple(x, 2 ** len(self.encoders))

        y = self.intro(padded)
        skips: list[torch.Tensor] = []
        for encoder, down in zip(self.encoders, self.downs):
            y = encoder(y)
            skips.append(y)
            y = down(y)

        y = self.middle(y)

        for decoder, up, skip in zip(self.decoders, self.ups, reversed(skips)):
            y = up(y)
            y = y + skip
            y = decoder(y)

        pred = self.ending(y)[..., :original_h, :original_w]
        return x - pred if self.residual else pred

    @staticmethod
    def _pad_to_multiple(x: torch.Tensor, multiple: int) -> torch.Tensor:
        """中文说明：实现 `_pad_to_multiple` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：x、multiple。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        h, w = x.shape[-2:]
        pad_h = (multiple - h % multiple) % multiple
        pad_w = (multiple - w % multiple) % multiple
        if pad_h == 0 and pad_w == 0:
            return x
        return F.pad(x, (0, pad_w, 0, pad_h), mode="reflect")
