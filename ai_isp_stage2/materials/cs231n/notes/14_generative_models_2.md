# Lecture 14：生成模型（二）

## 这讲在讲什么

这讲重点是 diffusion models。扩散模型通过逐步加噪和逐步去噪来学习生成数据。

## 核心概念

| 概念 | 解释 | 和图像恢复的关系 |
|---|---|---|
| Forward diffusion | 逐步给数据加噪 | 和噪声建模有关 |
| Reverse process | 学会从噪声还原数据 | 类似学习去噪步骤 |
| Score / noise prediction | 预测噪声或分数函数 | 和 residual denoise 有直觉联系 |
| Conditional diffusion | 在条件输入下生成结果 | 可用于超分、去噪、修复 |

## 和 DnCNN residual 的直觉联系

DnCNN residual 学的是：

```text
noisy -> noise
clean = noisy - noise
```

Diffusion 中很多模型也学习预测噪声，只是它们在多级噪声时间步上训练，目标是建模完整数据分布。

所以 residual denoise 是理解 diffusion 的一个小入口，但 diffusion 复杂得多。

## 图像恢复中的 diffusion

可用于：

- super-resolution
- deblurring
- inpainting
- low-light enhancement
- perceptual restoration

优点是感知质量强，缺点是推理慢、可能生成不忠实细节。

## AI-ISP 中的谨慎点

相机 pipeline 通常要求：

- 稳定
- 快
- 忠实
- 可控
- 低延迟

Diffusion 未必适合端侧实时 ISP，但它的去噪思想和图像先验值得了解。

## 当前最小带走

1. Diffusion 是多步生成模型。
2. 它常学习预测噪声。
3. 和 denoise 有概念联系，但不是当前入门主线。
4. 先学 CNN denoise，再理解 diffusion 会轻松很多。

