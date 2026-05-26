# Lecture 7：循环神经网络

## 这讲在讲什么

这讲介绍 RNN、LSTM、GRU、语言模型、序列到序列和图像描述。它处理的是序列数据，不是当前 RGB denoise 主线。

## 核心概念

| 概念 | 解释 | 和 AI-ISP 的关系 |
|---|---|---|
| Sequence | 有时间或顺序的数据 | 视频帧、burst RAW、有时序关系 |
| RNN | 当前状态依赖过去状态 | 可用于视频/时序建模 |
| LSTM / GRU | 缓解长序列梯度问题 | 老一代序列模型 |
| Image captioning | 图像编码 + 语言解码 | 不是当前主线 |

## 为什么当前可以跳过

我们现在的任务是单张图像去噪：

```text
single noisy RGB -> clean RGB
```

RNN 更适合：

```text
frame sequence -> temporal output
image -> caption words
```

所以这讲不是当前刚需。

## 什么时候会用到

在 AI-ISP 中，序列建模可能出现在：

- 视频降噪。
- 多帧 burst denoise。
- 时序 AWB / AE / tone 稳定。
- 连续帧低光增强。

这些属于后续方向，不是 Stage 2 Week 0/1 的重点。

## 最小理解

RNN 的核心是：

```text
h_t = f(x_t, h_{t-1})
```

当前输出不仅看当前输入，也看过去状态。

## 回到项目

当前不用改代码。只需记住：

```text
单帧图像恢复先学 CNN；多帧/视频再考虑时序模型。
```

