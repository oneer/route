# Lecture 16：视觉与语言

## 这讲在讲什么

这讲讨论视觉和语言的结合，例如图像-文本表示、captioning、CLIP 类模型、多模态理解。

## 核心概念

| 概念 | 解释 | 当前关系 |
|---|---|---|
| Vision-language model | 同时处理图像和文本 | 非当前主线 |
| Contrastive image-text learning | 图像和文本配对对齐 | 语义表示学习 |
| Captioning / VQA | 图像生成文字或回答问题 | 下游任务 |
| Multimodal representation | 多模态共同特征空间 | 后续可了解 |

## 为什么当前先跳过

我们当前输出是图像，不是文本：

```text
noisy RGB -> clean RGB
```

视觉语言任务输出通常是：

```text
image -> text
image + question -> answer
```

所以它和 AI-ISP 入门关系较远。

## 间接关系

未来可以用多模态模型辅助：

- 图像质量主观评价。
- 语义区域识别，比如 skin / sky / text。
- 自动生成 failure case 标签。

但这不是训练 denoise baseline 的必要前置。

## 最小带走

1. 视觉语言是现代 CV 大方向。
2. 当前不影响 TinyCNN / DnCNN / SIDD 学习。
3. 等图像恢复主线稳定后再看更合适。

