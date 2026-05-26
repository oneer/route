# Lecture 5：基于 CNN 的图像分类

## 这讲在讲什么

这讲解释 CNN 为什么适合图像：卷积、局部感受野、参数共享、feature map、pooling。它直接对应 TinyCNN 和 DnCNN。

## 核心概念

| 概念 | 解释 | 项目对应 |
|---|---|---|
| Convolution | 用小卷积核在图像上滑动 | `nn.Conv2d` |
| Kernel / filter | 可学习的局部滤波器 | TinyCNN 的卷积权重 |
| Feature map | 卷积输出的特征图 | 中间层 tensor |
| Channel | 图像或特征的通道维度 | RGB 3 通道、features 32 通道 |
| Receptive field | 一个输出像素能看到的输入范围 | 多层 3x3 看到更大邻域 |

## 为什么 CNN 适合图像

图像有空间结构。相邻像素通常相关，边缘、纹理、噪声也都是局部模式。

CNN 利用两个假设：

1. 局部连接：先看附近像素。
2. 参数共享：同一个卷积核可以在整张图上检测相似模式。

这比把整张图摊平成一个超大向量再全连接更高效。

## 3x3 卷积的直觉

一个 3x3 卷积会看当前像素周围的小邻域。对去噪来说，这很自然：

- 如果某个像素和周围差异特别大，可能是噪声。
- 如果一串像素形成连续边缘，可能是真实结构。
- 多层卷积可以从简单局部模式组合出更复杂判断。

## Channel 和 feature map

RGB 输入有 3 个 channel。TinyCNN 的第一层把它变成 32 个 feature channel。

可以粗略理解为：模型把原始 RGB 转换成多种局部特征，例如边缘、亮度变化、颜色差异、纹理响应等。具体每个通道不一定能人工命名，但它们共同帮助模型做去噪。

## Padding / stride / pooling

本项目 TinyCNN 使用 `padding=1`，让 3x3 卷积后图像尺寸保持不变。这样输入 64x64，输出仍是 64x64。

去噪任务通常需要输出和输入同尺寸，所以保持空间尺寸很重要。

Pooling 常用于分类，因为分类只需要最后类别，不要求像素级输出。图像恢复任务更谨慎使用下采样，因为要保留细节。

## TinyCNN 对应结构

```text
noisy RGB
  -> Conv2d(3 -> 32, 3x3)
  -> ReLU
  -> Conv2d(32 -> 32, 3x3)
  -> ReLU
  -> Conv2d(32 -> 3, 3x3)
  -> denoised RGB
```

这就是最小可学习滤波器组。

## 回到项目

看：

- `ai_isp_stage2/ai_isp/models/tiny_cnn.py`
- `ai_isp_stage2/ai_isp/models/dncnn.py`

问题：

1. TinyCNN 有几层卷积？
2. 为什么第一层是 `3 -> features`？
3. 为什么最后一层是 `features -> 3`？
4. 为什么去噪输出也要是 3 通道？

