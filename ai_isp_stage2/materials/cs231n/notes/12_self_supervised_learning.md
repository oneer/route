# Lecture 12：自监督学习

## 这讲在讲什么

这讲讲 pretext tasks、contrastive learning、多模态监督、自监督视觉表征。它的核心是：没有人工标签时，如何从数据本身构造学习信号。

## 核心概念

| 概念 | 解释 | 和图像恢复的关系 |
|---|---|---|
| Self-supervised learning | 从数据自身构造监督信号 | 无 GT 去噪/预训练 |
| Pretext task | 人为设计的辅助任务 | 预测旋转、拼图、mask 区域 |
| Contrastive learning | 拉近正样本、推远负样本 | 学通用图像表示 |
| Multisensory supervision | 用不同模态互相监督 | 视频/声音/图像可能相关 |

## 和 supervised denoise 的区别

当前 toy denoise 是有 clean target 的监督学习：

```text
noisy -> clean
```

自监督则可能没有 clean，只能构造间接目标：

```text
masked image -> missing pixels
two noisy views -> consistent clean estimate
```

## AI-ISP 中为什么重要

真实 clean GT 很难获得。尤其真实噪声、低光 RAW、手机 ISP 输出，很难有完美标签。

自监督思想可能用于：

- Noise2Noise
- Noise2Void
- masked image modeling
- RAW 数据预训练
- 无配对低光增强

## 当前不急的原因

如果还没理解 supervised training，自监督会更抽象。建议先学稳：

```text
noisy / clean paired data + L1 loss
```

再学无 GT 情况。

## 最小带走

1. 自监督用于标签难获取的场景。
2. 它不是“不需要监督”，而是监督信号来自数据结构本身。
3. AI-ISP 真实数据很可能需要自监督或弱监督思想。

