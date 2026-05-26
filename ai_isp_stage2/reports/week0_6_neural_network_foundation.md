# Week 0.6：神经网络图像恢复基础

这份笔记专门补一个地基：如果还没有很多机器学习 / 神经网络基础，应该怎么理解 Stage 2 的训练实验。

先不要急着记 DnCNN、UNet、NAFNet 这些模型名。阶段二的第一件事，是把神经网络从“黑盒模型”理解成：

```text
一个可以通过数据自动调参数的图像处理函数
```

## 1. 为什么图像问题可以交给神经网络

阶段一的传统 ISP 是人写规则：

```text
BLC: raw_corrected = raw - black_level
AWB: rgb_balanced = rgb * gain
Gamma: display = rgb ** (1 / gamma)
```

这些规则清楚、可解释，但也有局限：当问题变复杂，比如真实噪声、低光、纹理、边缘、颜色混在一起时，很难手写一套规则覆盖所有场景。

神经网络换了一种方式：不手写完整规则，而是给它很多输入和目标，让它自己学习一个函数：

```text
noisy image -> neural network -> clean image
```

这不等于模型真的“理解照片”。更朴素地说，它是在学一组卷积参数，让输出图更接近训练目标。

## 2. 本阶段先学什么，不学什么

这一周先学最小闭环：

```text
输入 noisy patch
  -> TinyCNN
  -> 输出 denoised patch
  -> 和 clean patch 比较
  -> 根据错误更新参数
```

暂时不重点学：

- 大模型结构。
- 真实手机噪声。
- RAW low-light。
- 论文 SOTA。
- 部署优化。

这些都放后面。现在只回答一个问题：

```text
模型为什么会因为训练而变好？
```

## 3. TinyCNN 是什么

TinyCNN 是本项目里最小的 CNN baseline。它只有 3 层卷积：

```text
noisy RGB
  -> Conv 3x3 + ReLU
  -> Conv 3x3 + ReLU
  -> Conv 3x3
  -> denoised RGB
```

卷积可以理解成“看局部邻域的可学习滤波器”。传统滤波器比如均值滤波、中值滤波，规则是人写死的；CNN 的卷积核参数则会在训练中自动调整。

一开始，TinyCNN 的卷积参数是随机的，所以输出也不可靠。训练的目的，就是把这些随机参数一步步调成更适合去噪的参数。

## 4. 一次训练 step 到底发生了什么

每个 step 都在做同一件事：

```text
1. Dataset 生成 clean patch
2. 给 clean 加 Gaussian noise，得到 noisy patch
3. Model 读取 noisy，输出 denoised
4. Loss 比较 denoised 和 clean
5. Backward 计算每个参数该往哪里改
6. Optimizer 更新参数
```

对应代码里的概念：

| 概念 | 人话解释 | 本项目里是什么 |
|---|---|---|
| Dataset | 出题器 | 生成 clean / noisy 成对 patch |
| Model | 做题的人 | TinyCNN / DnCNN / UNet |
| Output | 模型答案 | denoised patch |
| Target | 标准答案 | clean patch |
| Loss | 错误分数 | `mean(abs(output - clean))` |
| Backward | 算每个参数怎么改 | `loss.backward()` |
| Optimizer | 真正改参数 | AdamW |
| Step | 做一轮题并改一次参数 | 一次训练迭代 |

最重要的是：模型不是听懂了“去噪”这个词，而是通过 loss 得到反馈。输出错得多，loss 就大；参数更新后，如果输出更接近 clean，loss 就会下降。

## 5. 为什么要有验证集

训练集参与参数更新，验证集不参与参数更新。

验证集的作用是检查：

```text
模型是否学到了通用规律，而不是只记住训练样本
```

本项目每隔一段 step 会在验证集上算 PSNR / SSIM，并保存 noisy / output / clean 三联图。

- PSNR 越高，通常说明像素误差越小。
- SSIM 越高，通常说明结构相似度越好。
- 三联图用来看主观效果，避免只信数字。

## 6. 小实验：10 / 50 / 100 step 发生了什么

为了看清训练过程，跑了三份 TinyCNN probe：

| 配置 | 作用 |
|---|---|
| `toy_rgb_denoise_tiny_10.yaml` | 看几乎刚开始训练时的效果 |
| `toy_rgb_denoise_tiny_50.yaml` | 看模型开始学到映射时的效果 |
| `toy_rgb_denoise_tiny_100_probe.yaml` | 看最小 baseline 训练到 100 step 的效果 |

三份配置使用相同数据规模、相同模型、相同 seed，只改变训练步数和验证频率。

| step | train loss | val PSNR | val SSIM | 怎么理解 |
|---:|---:|---:|---:|---|
| 10 | 0.170468 | 13.49 | 0.6601 | 模型刚开始学，输出还比较粗糙 |
| 20 | 0.167046 | 14.47 | 0.6774 | 有一点改善，但还不稳定 |
| 30 | 0.113202 | 16.18 | 0.6966 | loss 明显下降，说明参数更新有效 |
| 40 | 0.108696 | 17.37 | 0.7162 | 输出继续接近 clean |
| 50 | 0.083647 | 18.19 | 0.7377 | 已经学到基础映射，但效果还一般 |
| 60 | 0.075990 | 20.36 | 0.7680 | PSNR 开始明显提升 |
| 70 | 0.056118 | 22.72 | 0.8054 | 模型开始更像一个去噪器 |
| 80 | 0.040939 | 24.18 | 0.8203 | 输出和 clean 更接近 |
| 90 | 0.043818 | 25.34 | 0.8409 | 指标继续变好，loss 有小波动正常 |
| 100 | 0.034625 | 26.73 | 0.8526 | 最小训练闭环成立 |

这张表比单个最终分数更重要。它说明训练不是魔法，而是一个逐步修正参数的过程：

```text
step 增加 -> 参数被反复更新 -> loss 总体下降 -> PSNR/SSIM 总体上升
```

中间 loss 有小波动是正常的。每个 batch 的样本不同，当前 batch 可能更难，loss 不会每一步都严格下降。我们看的是整体趋势。

## 7. 为什么不是一上来就 DnCNN / UNet

如果没有这层基础，直接看 DnCNN 会很容易变成：

```text
我知道命令怎么跑，但不知道为什么要这么做
```

更合理的顺序是：

```text
TinyCNN: 先理解训练闭环
DnCNN: 再理解 residual learning 为什么适合去噪
UNet: 再理解 encoder-decoder / skip connection 为什么适合恢复细节
SIDD/SID: 最后进入真实数据和 RAW 域
```

所以 TinyCNN 的价值不是效果强，而是让你知道神经网络训练的每个零件在做什么。

## 8. 和传统 ISP 怎么类比

| 传统 ISP | 神经网络图像恢复 |
|---|---|
| 人写公式和参数 | 模型从数据中学习参数 |
| 模块输入输出明确 | 也要定义输入域和输出域 |
| 调参看 before / after | 训练看 output / clean / loss |
| 用指标和主观图判断画质 | 也用 PSNR / SSIM / 三联图 |
| 出问题要定位模块 | 出问题要定位数据、loss、模型、学习率 |

你已有的 ISP 经验不是浪费。阶段二只是把“人手写规则”换成了“用数据调函数”，但工程判断仍然类似：输入是什么、目标是什么、指标可信吗、失败案例在哪里。

## 9. 现在应该真正掌握什么

学完 Week 0.6，不要求你会设计新网络。只要能说清下面这些，就够了：

1. 神经网络是可训练的图像处理函数。
2. Dataset 负责提供 noisy / clean 成对数据。
3. Model 输入 noisy，输出 denoised。
4. Loss 衡量 output 和 clean 的差距。
5. Backward 和 optimizer 根据 loss 更新参数。
6. Step 越多，模型有更多机会修正参数，但不代表无限变好。
7. PSNR / SSIM 是验证指标，不能替代看图。
8. TinyCNN 是地基，DnCNN / UNet 是后续在这个地基上增加结构设计。

一句话总结：

```text
Stage 2 不是先背模型名字，而是先理解训练如何把一个随机函数变成可用的图像恢复函数。
```
