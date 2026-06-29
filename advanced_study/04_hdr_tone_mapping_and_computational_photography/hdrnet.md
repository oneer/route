# Deep Bilateral Learning for Real-Time Image Enhancement (HDRNet)

## 精读版学习目标

HDRNet 要学的不是“又一个增强网络”，而是一种很工程化的思想：让神经网络预测低维、低分辨率的增强参数，再用传统快速算子作用到全分辨率图像。它对 ISP 工程特别有价值，因为相机系统常常不能承受逐像素大模型的延迟。

## 论文出现前的问题链条

高质量图像增强往往需要局部调整。比如天空要压高光，人脸要保肤色，阴影要提亮但不能放大噪声。传统全局 tone curve 太粗，逐像素复杂优化太慢，大 CNN 直接跑全分辨率又不适合移动端。HDRNet 试图在这三者之间找折中：复杂决策在低分辨率做，高分辨率只执行快速查表和仿射变换。

## bilateral grid 的直觉

普通 2D 网格只按空间位置变化，例如图像左上角一组参数、右下角一组参数。bilateral grid 多了一个维度，通常和亮度或 guide value 有关。也就是说，同一个空间位置里，暗像素和亮像素可以使用不同调整参数。

可以把它想成一个 3D 查表结构：

```text
grid[x, y, g] -> affine color transform

x, y: 低分辨率空间位置
g: guide map 值，通常和亮度相关
```

这样它比普通 2D 局部 LUT 更细，又比对每个像素跑大网络便宜。

## 局部仿射颜色变换是什么

HDRNet 不直接输出最终像素，而是输出仿射变换参数。对一个 RGB 像素，可以近似理解为：

```text
out_rgb = A(x, y, g) * in_rgb + b(x, y, g)
```

其中 `A` 是颜色变换矩阵，`b` 是偏置。不同位置、不同亮度的像素查到不同的 `A` 和 `b`，于是就能实现局部曝光、对比度和颜色调整。

## guide map 为什么重要

guide map 决定一个像素在 bilateral grid 的第三维上取哪里。如果 guide map 设计不好，边缘附近可能出现 halo 或颜色断层。传统 bilateral filter 之所以能保边，是因为它不仅看空间距离，也看像素值相似性。HDRNet 借用了这个思想：增强参数不要只按空间平滑，还要跟随图像内容变化。

## 为什么适合实时部署

真正昂贵的网络只在低分辨率输入上运行。全分辨率阶段主要是 slicing 和 affine transform，计算量接近线性，而且容易写成 C++/CUDA kernel。这和 stage4 的部署目标非常接近：不是把所有东西都交给神经网络，而是把网络放在最有价值的位置。

## 和本项目的具体练习路线

1. 在 `stage3_cpp_isp` 先实现一个 3D LUT：输入 luma，输出 tone-mapped luma，验证查表误差。
2. 再扩展成空间分块 LUT：不同 tile 使用不同 tone curve，观察块边界问题。
3. 加入 guide-based 插值，写报告解释它和 bilateral filter 的关系。
4. 在 `stage4_deploy_isp` 做延迟对比：全分辨率小 CNN vs 低分辨率参数预测 + C++ 后处理。

## 面试级复述

可以这样复述：HDRNet 的核心是让网络在低分辨率上预测 bilateral grid，grid 中存储局部仿射颜色变换参数。全分辨率图像通过 guide map 从 grid 中 slice 出每个像素的变换，再快速应用到原图。它把学习方法和传统 bilateral 思想结合起来，在质量和实时性之间取得平衡，适合移动端图像增强和 ISP 后段 tone/color 调整。

## 论文信息
- 作者：Michaël Gharbi, Jiawen Chen, Jonathan T. Barron, Samuel W. Hasinoff, Frédo Durand
- 会议/期刊：SIGGRAPH
- 年份：2017
- 论文链接：https://groups.csail.mit.edu/graphics/hdrnet/
- 代码链接：https://github.com/google/hdrnet

## 为什么要读这篇

HDRNet 是连接“图像增强质量”和“实时部署”的经典论文。它不是直接用大网络逐像素生成结果，而是学习一个低分辨率 bilateral grid，再用引导图对全分辨率图像做局部仿射变换。它非常适合连接 stage3 的 bilateral/local tone mapping 和 stage4 的部署思维。

## 背景问题：它解决了什么痛点

高质量图像增强常常需要复杂局部调整，但移动端实时处理高分辨率图像非常难。HDRNet 试图用低分辨率学习 + 高分辨率快速切片的方式，兼顾画质和速度。

## 初学者预备知识

需要理解 bilateral filter、局部 tone mapping、仿射颜色变换、低分辨率特征、上采样和实时推理约束。

## 核心思想一句话

网络不直接处理每个高分辨率像素，而是学习一个可快速查询的局部颜色变换网格。

## 方法原理详解

HDRNet 先在低分辨率图像上预测 bilateral grid。这个 grid 可以理解为空间位置和亮度维度上的一组局部仿射参数。随后对原图每个像素，根据位置和引导值从 grid 中切片，得到该像素对应的颜色变换参数。这样，复杂增强决策在低分辨率网络中完成，高分辨率应用阶段只做轻量查询和仿射变换。

这对 ISP 很有启发：很多显示域增强不一定要用昂贵逐像素大模型，可以用“学习参数 + 传统快速算子”的混合方式。

## 网络结构或算法流程

1. 输入低分辨率图像。
2. 网络预测 bilateral grid。
3. 预测或计算 guide map。
4. 对高分辨率输入进行 slicing。
5. 应用局部仿射颜色变换，得到增强结果。

## 损失函数 / 数据集 / 训练方式

通常使用成对增强数据，以像素损失训练输出接近目标修图结果。重点不是 RAW 恢复，而是实时图像增强和 tone/color adjustment。

## 实验结果如何理解

要同时看质量和速度。HDRNet 的贡献在于：在移动端约束下获得接近复杂增强算法的结果。阅读实验时关注分辨率、延迟、内存和视觉质量。

## 优点

- 把 bilateral 思想和神经网络结合得很优雅。
- 适合实时部署。
- 与 stage3 的局部 tone mapping、高性能实现强相关。

## 局限

- 更适合显示域增强，不是完整 RAW ISP。
- 对复杂语义修复和极端低光恢复能力有限。
- 实现 bilateral grid 和 slicing 需要额外工程细节。

## 和当前项目 stage1-stage4 的对应关系

- stage1_soft_isp：对应 tone mapping 和颜色增强后段。
- stage2_ai_isp：可作为轻量增强网络方向。
- stage3_cpp_isp：可实现简化 bilateral grid slicing。
- stage4_deploy_isp：适合研究端侧低延迟增强部署。

## 可以在本项目中复现或简化实现的练习

1. 在 stage3 用 C++ 实现一个简化 3D LUT 或 bilateral grid 查询。
2. 用 stage2 训练一个低分辨率网络预测 tone curve 参数。
3. 在 stage4 对比“全分辨率 CNN”和“低分辨率参数预测”的延迟。

## 阅读后应该掌握什么

你应该能解释：实时图像增强常常不是最大模型赢，而是好算法结构加好工程近似赢。
