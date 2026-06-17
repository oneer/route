# Lecture 13：生成模型（一）

## 这讲在讲什么

这讲介绍生成模型的第一部分：VAE、GAN、autoregressive models。生成模型的目标不是只判断图像，而是建模数据分布并生成样本。

## 核心概念

| 概念 | 解释 | 和图像恢复的关系 |
|---|---|---|
| Generative model | 学习数据分布并生成样本 | 可用于图像先验 |
| Autoregressive model | 按顺序预测像素/ token | 生成质量高但慢 |
| VAE | 编码到潜变量，再解码生成 | 学连续 latent 表示 |
| GAN | 生成器和判别器对抗训练 | 可提升感知真实感 |

## 和图像恢复的区别

图像恢复不是从零生成图像，而是条件生成：

```text
condition: noisy / low-light image
output: restored image
```

所以恢复任务要平衡：

- 忠实输入内容。
- 去除退化。
- 不制造虚假细节。

这和纯生成不同。

## GAN 在图像恢复中的风险

GAN loss 可能让图像看起来更锐，但也可能 hallucinate 细节。AI-ISP 里这很敏感：

- 纹理可能是假的。
- 人脸细节可能被改。
- 色彩可能主观好但不忠实。

所以产品画质不能只追求“看起来锐”。

## 当前为什么先不学深

你现在需要先理解 supervised CNN denoise。生成模型会引入概率分布、latent variable、adversarial training，复杂度更高。

## 最小带走

1. 生成模型学习图像分布。
2. 图像恢复是条件生成/条件恢复问题。
3. 感知质量和忠实度之间有 tradeoff。
4. 后续学 diffusion / GAN 前，先把 L1/PSNR baseline 学稳。

