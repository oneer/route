# Lecture 6：CNN 架构

## 这讲在讲什么

这讲从单个 CNN 层推进到完整网络结构，讨论 BatchNorm、transfer learning、AlexNet、VGG、GoogLeNet、ResNet 等经典架构。

对我们来说，重点不是背模型历史，而是理解：结构设计会影响训练难度、表达能力和部署成本。

## 核心概念

| 概念 | 解释 | 和项目的关系 |
|---|---|---|
| Depth | 网络层数 | DnCNN 比 TinyCNN 更深 |
| BatchNorm | 稳定训练的归一化层 | 小 batch 图像恢复里需谨慎 |
| Transfer learning | 用预训练模型迁移到新任务 | 后续真实数据少时有用 |
| Residual connection | 学残差而非完整映射 | DnCNN residual / ResNet 思想相关 |
| Architecture tradeoff | 精度、速度、参数量之间取舍 | Stage 3/4 部署会用到 |

## 从 TinyCNN 到 DnCNN

TinyCNN 只有 3 层，适合看训练闭环。DnCNN 更深，能看更大邻域，也能表达更复杂去噪规则。

```text
TinyCNN: 简单、快、易懂
DnCNN: 更深、更适合 denoise baseline
UNet: 下采样/上采样 + skip connection，适合恢复多尺度细节
```

不要一开始就问“哪个最强”。先问：

```text
这个结构为什么适合当前任务？
```

## Residual 的重要性

ResNet 的核心思想是让网络学习残差，缓解深层网络训练困难。DnCNN denoise 里的 residual learning 也有类似直觉：不直接预测 clean，而预测 noise。

```text
direct: denoised = net(noisy)
residual: denoised = noisy - net(noisy)
```

这让模型主要学习输入和目标之间的差值。对去噪来说，这个差值就是噪声。

## BatchNorm 要谨慎理解

BatchNorm 在分类网络里非常重要，能稳定训练。但在图像恢复里，尤其 batch 小、输入分布变化大时，BatchNorm 可能带来亮度/颜色偏移或训练/推理不一致。

所以本项目的小型 DnCNN 没有使用 BN，先保持实验简单。

## Transfer learning 和 AI-ISP

分类模型常用 ImageNet 预训练。但图像恢复任务输出是图像，任务域和分类不同，不是所有预训练都直接适用。

后续可以考虑：

- 用自监督预训练学图像表示。
- 用已有去噪模型初始化。
- 用合成数据预训练，再用真实数据微调。

## 架构不是越大越好

AI-ISP 最终常要部署到端侧。模型要考虑：

- 参数量
- FLOPs
- 显存
- latency
- patch 推理边界
- 量化损失

所以 Stage 2 学模型效果，Stage 3/4 会继续学工程部署。

## 回到项目

看：

- `ai_isp_stage2/reports/week1_rgb_denoise_baseline.md`
- `ai_isp_stage2/ai_isp/models/dncnn.py`
- `ai_isp_stage2/ai_isp/models/unet.py`

问题：

1. 为什么 DnCNN residual 比 direct clean 更容易学？
2. 为什么 UNet 可能适合多尺度细节恢复？
3. 为什么当前阶段不急着上 NAFNet？

