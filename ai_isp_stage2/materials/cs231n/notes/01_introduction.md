# Lecture 1：导论

## 这讲在讲什么

导论负责回答三个问题：计算机视觉为什么难、深度学习为什么成为主流方法、这门课后面会如何从图像分类一路走到更复杂的视觉任务。

对我们 Stage 2 来说，这讲不是为了记住所有视觉任务，而是建立大图景：AI-ISP / 图像恢复也是计算机视觉的一部分，只不过它的输出不是类别标签，而是一张更好的图像。

## 核心概念

| 概念 | 解释 | 和 AI-ISP 的关系 |
|---|---|---|
| Computer Vision | 让机器从图像或视频中提取有用信息 | ISP 输出的图像质量会影响下游视觉系统 |
| Deep Learning | 用多层可学习函数从数据中学习表示 | Stage 2 用网络学习 noisy -> clean 的映射 |
| Data-driven approach | 不手写完整规则，而从样本中学习规律 | 从传统 ISP 规则过渡到 learned ISP |
| Representation | 图像经过模型后形成的中间特征 | CNN 的 feature map 是对局部纹理/边缘的表达 |

## 为什么视觉难

图像里的同一个物体可能因为光照、角度、遮挡、尺度、背景、相机噪声而变化巨大。传统规则很难覆盖所有情况。

对于 AI-ISP，也有类似困难：

- 同样的暗部噪声，在不同 ISO / 曝光 / sensor 上分布不同。
- 同样的边缘，在去噪时既可能是真实纹理，也可能是噪声。
- 同样的颜色偏差，可能来自 AWB、CCM、光源，也可能来自数据标注。

因此深度学习的吸引力在于：它不是手写所有条件，而是通过大量样本拟合一个复杂映射。

## 和传统 ISP 的连接

传统 ISP 是模块化规则：

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone -> sRGB
```

AI 图像恢复则把其中某些映射交给模型：

```text
noisy RGB -> network -> clean RGB
low-light RAW -> network -> enhanced RGB
```

关键不是“AI 替代所有规则”，而是知道哪些问题适合学习、哪些约束仍需要 ISP 物理知识。

## 本讲要带走的判断

1. 深度学习不是魔法，而是一种数据驱动函数拟合。
2. 图像任务的输入输出必须定义清楚。
3. AI-ISP 不是脱离传统 ISP，而是在传统图像链路上引入可学习模块。
4. 后面学分类、CNN、优化，是为了理解这个可学习模块怎么训练。

## 回到项目

读完本讲后，看：

- `ai_isp_stage2/reports/week0_6_neural_network_foundation.md`
- `ai_isp_stage2/README.md`

问题：你能不能用一句话说清 Stage 2 和 Stage 1 的区别？

