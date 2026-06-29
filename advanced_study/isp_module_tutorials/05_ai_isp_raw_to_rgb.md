# AI-ISP RAW 到 RGB：从 SID、DeepISP 到 Learned Smartphone ISP

## 模块定位

AI-ISP RAW2RGB 试图学习更大范围的映射：

```text
RAW / packed RAW / sensor features
-> neural reconstruction/enhancement
-> linear RGB or sRGB
```

它可能替代传统 ISP 的一部分，也可能替代从 demosaic 到 tone mapping 的大段流程。

## 传统做法

传统 RAW2RGB 是模块串行：

```text
BLC -> Demosaic -> AWB -> CCM -> Denoise -> Tone -> Gamma
```

优点是可解释，缺点是每个模块的误差累积，并且很难端到端优化最终视觉效果。

## 当前先进做法

### SID：低光 RAW 到 sRGB

Learning to See in the Dark 用短曝光 RAW 和长曝光参考训练 U-Net。重点是 RAW pack、曝光倍率、黑电平和低光噪声。它说明 AI-ISP 在极低光下优先从 RAW 域学习。

### DeepISP：端到端图像处理

DeepISP 探索用网络学习图像处理管线，强调局部恢复和全局颜色/曝光调整共同存在。它启发我们：AI-ISP 不只是 denoise，而是局部和全局共同建模。

### Learned Smartphone ISP

Mobile AI Learned Smartphone ISP Challenge 这类任务更贴近手机 RAW 到高质量 RGB 的学习。常见重点包括轻量模型、真实 RAW、颜色稳定、边缘纹理、部署速度。

### RAW-aware 结构

较新的 RAW2RGB 方法会显式考虑 CFA、black level、曝光不均、Retinex、Mamba/Transformer 等结构。趋势不是盲目大模型，而是让网络更懂 RAW 数据结构。

## AI-ISP 的关键设计问题

### 输入是 RAW 还是 RGB

RGB 输入更容易训练，但已经丢失很多 RAW 信息。RAW 输入更有潜力，但需要处理 black level、CFA、曝光、噪声和颜色空间。

### 输出是 linear RGB 还是 sRGB

输出 sRGB 视觉直观，但把 tone、gamma、颜色风格混在一起。输出 linear RGB 更适合接传统 tone/color，但训练目标更难准备。

### Loss 怎么选

L1/L2 稳定但可能平滑；perceptual/GAN/diffusion 可能更好看但有 hallucination 风险。ISP 工程通常不能只追“锐”。

## 工程注意点

- 必须固定 RAW pack 顺序。
- 训练和部署的 black/white level 必须一致。
- 需要按相机/ISO/曝光拆分测试集，防止数据泄漏。
- 评估要包含颜色、暗部、边缘、纹理和失败案例。
- 轻量化不是最后一步，而应从模型设计开始考虑。

## 和本项目对应

- stage1：提供传统 pipeline baseline 和 RAW 契约。
- stage2：训练 AI-ISP/denoise/low-light 模型。
- stage3：提供传统 C++ baseline 和部分前后处理。
- stage4：负责 ONNX/TensorRT/INT8 和 CUDA preprocess。

## 练习

1. 用 stage1 输出构造一个 paired toy：简化 pipeline 输出 -> rawpy 参考输出。
2. 在 stage2 训练小 U-Net 或 NAFNet，比较 RGB 输入和 pseudo RAW 输入。
3. 在 stage4 写 AI-ISP 输入契约检查脚本。
4. 做一份失败案例 taxonomy：色偏、过平滑、伪纹理、暗部彩噪、高光 clipping。

## 你应该掌握

AI-ISP 不是把传统 ISP 全部扔掉，而是在 RAW 契约、数据监督、网络结构、颜色稳定和部署约束之间重新分配模块职责。

