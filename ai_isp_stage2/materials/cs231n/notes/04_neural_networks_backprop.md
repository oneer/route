# Lecture 4：神经网络与反向传播

## 这讲在讲什么

这讲是理解训练的关键：神经网络如何由多层函数组成，反向传播如何用链式法则计算每个参数对 loss 的影响。

## 核心概念

| 概念 | 解释 | 项目对应 |
|---|---|---|
| Neural network | 多层可学习函数组合 | TinyCNN / DnCNN |
| Activation | 非线性函数，让模型不只是线性变换 | ReLU |
| Forward pass | 从输入算输出 | `output = model(noisy)` |
| Backward pass | 从 loss 反推梯度 | `loss.backward()` |
| Computational graph | 记录计算依赖关系 | PyTorch 自动构建 |

## 为什么需要非线性

多层线性函数叠在一起，仍然等价于一个线性函数。ReLU 这类非线性让网络能表达复杂映射。

TinyCNN 里：

```text
Conv -> ReLU -> Conv -> ReLU -> Conv
```

ReLU 的作用是让中间特征具有非线性表达能力。没有它，模型表达能力会弱很多。

## Forward 是什么

Forward 就是模型做预测：

```text
noisy -> model -> output
```

在去噪任务里，output 是模型认为的 denoised image。

## Backward 是什么

Backward 不是“重新跑一遍模型”，而是计算：

```text
每个参数变化一点点，会让 loss 变大还是变小？
```

如果某个参数增加会让 loss 变大，optimizer 就倾向于把它减小。反之亦然。

## 链式法则的直觉

神经网络是很多函数的组合：

```text
x -> layer1 -> layer2 -> layer3 -> loss
```

loss 对前面参数的影响，需要沿着这条链一层层传回去。反向传播就是高效地做这件事。

## PyTorch 帮你做了什么

你不用手写每层梯度。PyTorch 会记录计算图：

```python
output = model(noisy)
loss = criterion(output, clean)
loss.backward()
optimizer.step()
```

但你必须理解这几行的意义，否则训练就会变成“会跑命令但不知道为什么”。

## 和 ISP 的类比

传统 ISP 调参可能是：

```text
图偏暗 -> 调 tone/gamma 参数
图偏绿 -> 调 AWB/CCM 参数
```

神经网络训练是：

```text
output 和 clean 有误差 -> backward 自动算参数该怎么调
```

人不再逐项手调每个卷积核，而是用 loss 统一给反馈。

## 回到项目

看：

- `ai_isp_stage2/ai_isp/engine/train.py`

重点定位：

```python
output = model(noisy)
loss = criterion(output, clean)
loss.backward()
optimizer.step()
```

问题：

1. 哪一行是 forward？
2. 哪一行计算 loss？
3. 哪一行计算梯度？
4. 哪一行真正更新参数？

