# Lecture 3：正则化与优化

## 这讲在讲什么

这讲解释模型如何通过优化让 loss 下降，以及为什么正则化能减少过拟合。它直接对应训练代码里的 optimizer、learning rate、weight decay 和训练曲线。

## 核心概念

| 概念 | 解释 | 项目对应 |
|---|---|---|
| Optimization | 找到让 loss 更小的参数 | `optimizer.step()` |
| Gradient descent | 沿着 loss 下降方向更新参数 | `loss.backward()` 后更新 |
| Learning rate | 每次参数更新走多大步 | YAML 里的 `learning_rate` |
| SGD / Adam | 不同参数更新算法 | 本项目用 AdamW |
| Regularization | 限制模型不要过度记忆训练集 | `weight_decay` |

## 为什么训练会变好

训练不是模型自己突然开窍，而是每一步都在做：

```text
当前参数 -> 算 output -> 算 loss -> 算梯度 -> 更新参数
```

如果 learning rate 合适，参数会逐渐移动到 loss 更低的位置。于是你看到：

```text
train loss 下降
val PSNR / SSIM 上升
```

## Learning rate 的直觉

Learning rate 太大：

- loss 可能震荡。
- 训练可能发散。
- 输出图可能突然变差。

Learning rate 太小：

- 训练很慢。
- 100 step 内看不到明显改善。

本项目入门配置用 `0.001`，是为了让 TinyCNN 在几十到一百步内能稳定看到趋势。

## Adam / AdamW 的直觉

SGD 是基础梯度下降。Adam 会根据梯度的一阶和二阶统计自适应调整每个参数的更新幅度。AdamW 把权重衰减和 Adam 更新解耦，工程里更常用。

对你当前阶段，不需要先推公式，先理解：

```text
optimizer 决定参数怎么根据梯度更新
```

## 正则化和过拟合

过拟合是模型在训练集上很好，在验证集上不好。正则化是减少过拟合的一类方法。

常见正则化：

- weight decay
- dropout
- data augmentation
- early stopping

在 toy denoise 里，数据是程序生成的，先不强调正则化；真实 SIDD / SID 里会更重要。

## 读训练曲线

不要只看最终分数。要看趋势：

```text
train loss 是否总体下降？
val PSNR 是否总体上升？
val 指标是否开始平台化？
中间是否有明显震荡？
```

Week 0.6 的 TinyCNN 10/50/100 step 就是在训练你读曲线。

## 回到项目

看：

- `ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml`
- `ai_isp_stage2/ai_isp/engine/train.py`

问题：

1. learning rate 在哪里配置？
2. optimizer 是在哪里创建的？
3. `weight_decay` 当前为什么设为 0？
4. 100 step 曲线里 loss 是否严格每步下降？为什么不用要求严格下降？

