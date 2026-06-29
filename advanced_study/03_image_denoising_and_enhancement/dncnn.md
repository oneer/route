# DnCNN: Beyond a Gaussian Denoiser

## 精读版学习目标

DnCNN 是学习深度去噪时最适合“打地基”的论文。你要掌握的不是某个 17 层 CNN，而是残差预测这个建模方式：恢复任务里，输入和目标往往非常接近，模型不必重新生成整张图，只需要学习应该删掉或修正的退化部分。

## 从传统去噪到残差学习

传统去噪常常依赖先验，比如相似 patch、平滑性、稀疏性。DnCNN 的思路更直接：用大量 noisy/clean 配对样本训练 CNN。但它没有让网络直接输出 clean image，而是输出 noise residual。

如果 noisy 图像是：

```text
y = x + n
```

直接预测是：

```text
F(y) = x
```

残差预测是：

```text
R(y) = n
x_hat = y - R(y)
```

这对训练更友好，因为噪声残差通常比自然图像结构简单。

## 为什么这对 AI-ISP 很重要

AI-ISP 里很多任务都可以写成“退化观测 = 干净图像 + 某种退化”。噪声、轻微模糊、压缩伪影、色偏都可以看成需要修正的残差。DnCNN 训练你用残差视角看恢复问题，这会影响后面理解 NAFNet、Restormer、低光增强和部署误差分析。

## BatchNorm 和 ReLU 要怎么理解

DnCNN 使用 Conv + BN + ReLU 堆叠。BN 在当时有助于训练较深 CNN，但真实图像恢复中 BN 也可能引入分布问题。比如训练数据噪声强度固定，测试时噪声分布变化，BN 统计可能不理想。读这篇时要知道它是经典 baseline，不是所有现代恢复网络都保留 BN。

## 和本项目的具体练习路线

1. 在 `stage2_ai_isp` 训练 direct 模型和 residual 模型，保持参数量接近，比较 loss 曲线。
2. 在合成高斯噪声上训练，再拿 SIDD tiny 测试，观察真实噪声泛化差距。
3. 在 `stage3_cpp_isp` 用 bilateral/NLM 跑同一批 crop，比较传统去噪和 DnCNN 的失败模式。
4. 在 `stage4_deploy_isp` 导出 DnCNN ONNX，记录 PyTorch/ORT/TensorRT 的最大误差、平均误差和视觉差异。

## 面试级复述

可以这样复述：DnCNN 的核心贡献是把图像去噪建模为残差学习，让 CNN 预测噪声而不是直接预测干净图像，再用输入减去噪声得到恢复结果。这个设计降低了学习难度，并成为很多恢复任务的基础思想。它适合作为 AI-ISP 去噪 baseline，但对真实 RAW 噪声、空间变化噪声和现代部署约束还需要进一步扩展。

## 论文信息
- 作者：Kai Zhang, Wangmeng Zuo, Yunjin Chen, Deyu Meng, Lei Zhang
- 会议/期刊：IEEE Transactions on Image Processing
- 年份：2017
- 论文链接：https://arxiv.org/abs/1608.03981
- 代码链接：https://github.com/cszn/DnCNN

## 为什么要读这篇

DnCNN 是深度学习去噪的基础论文之一。stage2 的早期 denoise 训练和 stage4 的 `dncnn_sidd_tiny.onnx` 都能从这篇找到思想来源：残差学习、批归一化、卷积堆叠、噪声预测。

## 背景问题：它解决了什么痛点

传统去噪方法如 NLM、BM3D 需要强先验和复杂参数。早期 CNN 直接预测干净图像时训练难度较高。DnCNN 改成预测噪声残差，再用输入减去残差得到干净图像，降低学习难度。

## 初学者预备知识

需要理解卷积、残差学习、MSE/L2 损失、高斯噪声、PSNR。可先读 `stage2_ai_isp/reports/week1_toy_rgb_denoise.md`。

## 核心思想一句话

让 CNN 学噪声，而不是直接学干净图像。

## 方法原理详解

如果输入是 `y = x + n`，传统监督学习可以训练网络 `F(y) = x`。DnCNN 让网络学习 `R(y) = n`，最后输出 `x_hat = y - R(y)`。这样做符合去噪任务的结构：噪声通常比图像内容更接近零均值残差，网络只需估计要删掉什么。

DnCNN 也展示了一个统一思路：同一个残差去噪网络可以扩展到 JPEG 去块、超分等恢复任务。这对 stage2 很重要，因为 AI-ISP 中很多任务本质上都是“从退化观测恢复干净图像”。

## 网络结构或算法流程

1. 输入 noisy RGB 或灰度图。
2. 多层卷积 + ReLU + BatchNorm 提取特征。
3. 输出预测噪声残差。
4. 用输入减去预测残差得到恢复图。

## 损失函数 / 数据集 / 训练方式

常用 L2/MSE 损失，让预测残差接近真实噪声。训练可用合成高斯噪声，也可扩展到真实噪声数据。stage2 若用 SIDD，小心真实噪声不再是简单高斯。

## 实验结果如何理解

PSNR 提升说明像素误差下降，但视觉上还要看纹理是否被抹平、边缘是否保留、暗部是否有彩噪残留。DnCNN 是强 baseline，不是最终答案。

## 优点

- 概念清楚，适合入门。
- 残差学习非常适合去噪。
- 容易导出 ONNX，适合 stage4 部署链路。

## 局限

- 对真实复杂噪声、空间变化噪声和 RAW 噪声建模有限。
- BatchNorm 在小 batch 或分布变化时可能有副作用。
- 视觉质量不如后续 NAFNet/Restormer 等现代恢复网络。

## 和当前项目 stage1-stage4 的对应关系

- stage1_soft_isp：可对比传统 NLM/bilateral 去噪。
- stage2_ai_isp：对应 toy denoise 和 SIDD tiny baseline。
- stage3_cpp_isp：可用传统 C++ 去噪作为非学习 baseline。
- stage4_deploy_isp：对应 ONNX Runtime C++ 和 TensorRT 推理 smoke test。

## 可以在本项目中复现或简化实现的练习

1. 在 stage2 训练 direct prediction 和 residual prediction 两个小模型，比较收敛曲线。
2. 导出 DnCNN 到 ONNX，并用 stage4 检查 PyTorch/ONNX 输出误差。
3. 用 stage3 的 bilateral/NLM 与 DnCNN 对同一 SIDD crop 做视觉对比。

## 阅读后应该掌握什么

你应该能解释：为什么“预测残差”是图像恢复中非常常见的建模方式。
