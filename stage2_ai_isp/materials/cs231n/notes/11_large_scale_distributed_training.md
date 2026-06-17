# Lecture 11：大规模分布式训练

## 这讲在讲什么

这讲讨论大规模训练中的 GPU 利用率、数据并行、模型并行、激活检查点、通信开销等。

## 核心概念

| 概念 | 解释 | 当前是否需要 |
|---|---|---|
| Data parallel | 多卡复制模型，切分 batch | 当前不需要 |
| Model parallel | 模型太大，拆到多卡 | 当前不需要 |
| Pipeline parallel | 不同层放不同设备流水执行 | 当前不需要 |
| Activation checkpointing | 用重算换显存 | 后面大模型可能需要 |
| Utilization | GPU 是否忙起来 | 训练变大后重要 |

## 为什么当前先跳过

现在我们训练 TinyCNN / DnCNN，规模很小，核心瓶颈不是分布式，而是理解训练过程。

提前学习分布式容易偏离主线：

```text
当前目标：看懂一个模型怎么训练
不是目标：把大模型跑满多卡
```

## 后续什么时候有用

当你进入：

- 大规模 SIDD / SID 训练。
- NAFNet / Restormer 这类较大模型。
- 高分辨率 patch。
- 多 GPU 实验。

这讲会变得重要。

## 和端侧部署的区别

分布式训练关注训练效率；端侧部署关注推理效率。

```text
training: 多卡、更快收敛、更大 batch
deployment: latency、memory、quantization、throughput
```

不要把两者混在一起。

## 当前记住

1. 小模型阶段不需要分布式。
2. 显存不够时可以先减 batch / patch size。
3. 大模型训练才考虑 checkpointing 和多卡。

