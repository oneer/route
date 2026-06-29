# PromptIR: Prompting for All-in-One Image Restoration

## 精读版学习目标

PromptIR 要学习的是“退化自适应”。真实 ISP/AI-ISP 场景里，很少有图像只含一种退化。低光往往伴随噪声、色偏、运动模糊和压缩；手机夜景还可能有多帧融合伪影。PromptIR 的价值在于把单任务恢复推进到 all-in-one restoration：同一个模型根据输入退化状态调整处理策略。

## prompt 在这里不是文字提示

这里的 prompt 更像可学习的条件向量或特征调制信号。它不是输入一句“please denoise”，而是模型从图像中估计当前退化类型或强度，再用这个提示控制恢复网络。

可以这样理解：

```text
degraded image -> prompt module -> degradation-aware prompt
degraded image + prompt -> restoration network -> restored image
```

prompt 的作用类似传统 ISP 里的场景检测和参数选择：夜景、逆光、人像、室内灯光，处理参数本来就不应相同。

## 为什么 all-in-one 很难

去噪希望抹掉随机扰动，去模糊希望恢复边缘，低光增强希望提亮暗部，去雨/去雾又有不同结构。一个模型如果没有条件控制，很可能学到平均策略：什么都能处理一点，但什么都不够好。PromptIR 通过 prompt 给模型一个“当前该偏向哪种恢复”的内部控制。

## 和本项目的具体练习路线

1. 在 `stage2_ai_isp` 先做显式 prompt：把噪声 sigma 或低光倍率作为额外通道输入。
2. 训练同一模型处理轻噪声、重噪声、低光三种退化，比较无 prompt 和有 prompt。
3. 把 prompt 值可视化，看它是否随退化强度变化。
4. 在 `stage4_deploy_isp` 评估 prompt 输入是否增加部署复杂度：输入 tensor 数量、shape、前处理逻辑。

## 面试级复述

可以这样复述：PromptIR 用可学习 prompt 引导同一个恢复网络处理多种图像退化。它解决的是单任务模型在真实混合退化中不够灵活的问题。对 AI-ISP 来说，它对应场景自适应处理思想，但训练数据组织、prompt 可解释性和端侧部署仍然是挑战。

## 论文信息
- 作者：Vaishnav Potlapalli, Syed Waqas Zamir, Salman Khan, Fahad Shahbaz Khan
- 会议/期刊：NeurIPS
- 年份：2023
- 论文链接：https://arxiv.org/abs/2306.13090
- 代码链接：https://github.com/va1shn9v/PromptIR

## 为什么要读这篇

PromptIR 代表“一个模型处理多种退化”的方向。对 AI-ISP 很重要，因为真实相机问题很少只有单一噪声，往往同时有噪声、模糊、压缩、低光、色偏和 tone mapping 问题。

## 背景问题：它解决了什么痛点

传统恢复网络通常按任务训练：去噪一个模型，去雨一个模型，去模糊一个模型。真实应用中退化类型混合，部署多个模型成本高。PromptIR 尝试用 prompt 引导同一模型适应不同退化。

## 初学者预备知识

需要理解 image restoration、Transformer/attention 基础、condition/prompt 思想、多任务学习和退化建模。

## 核心思想一句话

让网络学习一组可调 prompt，用来告诉恢复模型当前图像更像哪种退化。

## 方法原理详解

PromptIR 的关键不是文字 prompt，而是可学习的视觉 prompt。模型根据输入图像特征选择或生成 prompt，再把 prompt 融入恢复网络，使同一个主干能对不同退化采取不同处理策略。可以把它理解为“任务自适应控制信号”。

对 ISP 来说，这很像真实相机里的场景自适应：低光、逆光、人像、夜景需要不同处理强度。PromptIR 提供了一个学习化的思路。

## 网络结构或算法流程

1. 输入退化图像。
2. 主干网络提取多尺度特征。
3. prompt 模块估计退化相关提示。
4. 将 prompt 注入恢复模块。
5. 输出恢复图像。

## 损失函数 / 数据集 / 训练方式

通常在多任务恢复数据集上训练，使用监督像素损失。训练重点是混合多种退化，让 prompt 学到区分和调节能力。

## 实验结果如何理解

要看 all-in-one 能否接近单任务模型。如果多任务模型平均指标高，但某个关键任务明显退化，实际工程中仍需谨慎。

## 优点

- 面向真实混合退化。
- 比为每个任务部署一个模型更统一。
- 启发 AI-ISP 场景自适应设计。

## 局限

- 多任务训练数据组织复杂。
- prompt 可解释性有限。
- 不一定直接适合 RAW 域和严格端侧部署。

## 和当前项目 stage1-stage4 的对应关系

- stage1_soft_isp：可类比不同场景下 ISP 参数调节。
- stage2_ai_isp：可扩展 denoise/low-light/deblur 多任务训练。
- stage3_cpp_isp：传统模块参数可作为显式 prompt 的对照。
- stage4_deploy_isp：一个多任务模型可能降低模型管理成本，但需评估延迟。

## 可以在本项目中复现或简化实现的练习

1. 在 stage2 构造“噪声强度 prompt”，把噪声 sigma 作为条件输入。
2. 训练同一小模型处理轻噪声和重噪声，比较无 prompt/有 prompt。
3. 把 prompt 输出可视化，分析它是否和退化强度相关。

## 阅读后应该掌握什么

你应该能解释：foundation/restoration 方向的一个核心趋势，是从单任务模型走向退化自适应模型。
