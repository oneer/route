# Lecture 8：注意力机制与 Transformer

## 这讲在讲什么

这讲介绍 self-attention、Transformer，以及它们如何从 NLP 扩展到视觉任务。对图像恢复来说，后续 Restormer、SwinIR、Uformer 等都会用到这类思想。

## 核心概念

| 概念 | 解释 | 和图像恢复的关系 |
|---|---|---|
| Attention | 让一个位置根据相关性聚合其他位置的信息 | 建模长距离依赖 |
| Query / Key / Value | 计算注意力权重的三组向量 | Transformer 基础 |
| Self-attention | 同一输入内部位置互相看 | 图像 patch 之间交互 |
| Transformer | 堆叠 attention 和 MLP 的结构 | ViT / Restormer 等 |
| Positional encoding | 提供位置信息 | 图像空间结构需要位置 |

## 和 CNN 的区别

CNN 强在局部：

```text
3x3 卷积看附近像素
```

Attention 强在全局：

```text
一个位置可以直接参考远处位置
```

图像恢复里，局部纹理和全局结构都重要。低光增强、去模糊、大面积噪声建模可能受益于更大上下文。

## 为什么现在不急着学深

Transformer 需要先理解：

- tensor shape
- linear layer
- loss / optimizer
- CNN / feature map

如果这些还不稳，直接看 attention 会很抽象。

当前只要知道：后面很多现代图像恢复模型不是纯 CNN，而是把 attention 引入恢复任务。

## 和 AI-ISP 的可能关系

可能用在：

- RAW denoise 中建模非局部相似性。
- 去模糊中建模长距离运动轨迹。
- 低光增强中保持全局亮度一致。
- learned ISP 中融合多尺度信息。

## 本讲最小检查点

1. Attention 是根据相关性加权汇聚信息。
2. CNN 偏局部，Transformer 更擅长全局依赖。
3. 图像恢复中可以混合 CNN 和 attention。
4. 当前先学 CNN，后续再学 Restormer / SwinIR。

## 延伸阅读

- Attention Is All You Need
- The Illustrated Transformer
- Vision Transformer
- Restormer: Efficient Transformer for High-Resolution Image Restoration

