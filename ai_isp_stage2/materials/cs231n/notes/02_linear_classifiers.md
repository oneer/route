# Lecture 2：线性分类器进行图像分类

## 这讲在讲什么

这讲从图像分类入手，介绍 data-driven approach、kNN、线性分类器、Softmax loss。虽然它讲的是分类，不是去噪，但它是理解“模型 = 可学习函数”的入口。

## 核心概念

| 概念 | 解释 | 和本项目的关系 |
|---|---|---|
| Image as tensor | 图像可以表示成 H x W x C 的数字数组 | noisy / clean patch 都是 tensor |
| kNN | 记住训练样本，按距离找最像的样本 | 说明只记忆不是好泛化 |
| Linear classifier | 用 `Wx + b` 从输入算输出 | 神经网络也是很多可学习层组合 |
| Score function | 模型把输入映射成输出分数 | 去噪模型把 noisy 映射成 denoised |
| Softmax loss | 分类任务常用损失 | 类比去噪里的 L1 / L2 loss |

## 从分类到图像恢复

分类模型学习的是：

```text
image -> class score
```

去噪模型学习的是：

```text
noisy image -> clean image
```

两者形式不同，但训练逻辑相同：

```text
输入 -> 模型 -> 输出 -> loss -> 参数更新
```

所以先学分类，是因为分类任务更容易说明 loss、参数、优化这些基础概念。

## 线性模型的意义

线性分类器可以写成：

```text
score = W x + b
```

这里的 `W` 和 `b` 是参数。训练就是调整它们，让正确类别得分更高。

TinyCNN / DnCNN 也有参数，只不过参数不是一个大矩阵，而是一组卷积核：

```text
output = conv(noisy, weights)
```

因此你可以把神经网络先理解成“比线性模型更复杂的可学习函数”。

## Loss 的第一层直觉

Loss 是模型输出和目标之间的错误分数。

分类里，loss 惩罚错误类别得分太高。去噪里，loss 惩罚 output 和 clean 像素差距太大。

```text
classification: output score vs label
denoise: output image vs clean image
```

## 本讲易混点

- kNN 没有真正学习参数，只是存数据。
- 线性分类器有学习参数，但表达能力有限。
- Softmax loss 是分类 loss，不是图像恢复 loss。
- 学分类不是偏离主线，而是在学训练框架的最简单例子。

## 回到项目

看：

- `ai_isp_stage2/ai_isp/data/toy_rgb_dataset.py`
- `ai_isp_stage2/ai_isp/models/tiny_cnn.py`

问题：

1. noisy / clean 在代码里是什么 shape？
2. TinyCNN 里的可学习参数在哪里？
3. 去噪任务里的 output 和 target 分别是什么？

