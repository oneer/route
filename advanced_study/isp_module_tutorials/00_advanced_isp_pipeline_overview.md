# 先进 ISP Pipeline 总览：从传统串行管线到 Hybrid ISP / Neural ISP

## 模块定位

传统 ISP 通常是串行管线：

```text
RAW
-> BLC / DPC / LSC
-> Demosaic
-> AWB / CCM
-> Denoise / Sharpen
-> Gamma / Tone Mapping
-> sRGB / YUV / JPEG
```

这个结构清晰、可调、可部署，但也有问题：每个模块都基于局部假设，前面模块的错误会传给后面模块；极低光、HDR、多帧、复杂色彩和真实噪声场景下，手工规则很难覆盖。

当前更先进的 ISP 不是简单把所有模块都换成大模型，而是出现三类融合形态：

1. **传统 ISP 增强版**：保留模块边界，但使用更好的噪声模型、局部 tone、鲁棒 HDR merge、场景自适应参数。
2. **Hybrid ISP**：传统模块和神经网络混合，例如传统 RAW 前处理 + 神经网络去噪/增强 + 传统颜色管理。
3. **Neural ISP**：用网络学习 RAW 到 RGB 或 RAW 到 enhanced RGB 的较大映射，但仍需要严格输入契约和部署约束。

## 为什么不能只学传统模块

传统模块的优点是可解释，但很多真实问题不是单模块能解决的。比如低光场景下，Demosaic 会把噪声插值成彩色伪影；Tone Mapping 会放大暗部噪声；AWB 在暗部信噪比低时会估错色温。串行管线中，一个模块单独最优，不代表整体最优。

先进 ISP 的核心趋势是：把强耦合的模块联合起来优化。例如：

- Demosaic + Denoise 联合建模。
- HDR Tone Mapping + Denoise 联合建模。
- RAW 前处理 + Low-light Enhancement 联合训练。
- 低分辨率神经网络预测参数，高分辨率传统算子执行。

## 为什么也不能全靠端到端大模型

端到端模型有吸引力，但 ISP 工程有强约束：

- 输入来自不同 sensor，black level、white level、CFA、噪声分布不同。
- 输出需要颜色稳定，不只是“看起来清楚”。
- 手机/车载/安防要求低延迟、低功耗、可验证。
- 不能随意 hallucinate 不存在的细节。
- 部署要面对 ONNX、TensorRT、NPU、ISP 硬件和内存带宽。

所以更现实的方向通常是 Hybrid：传统模块负责物理一致性和稳定性，神经网络负责传统规则难以处理的复杂映射。

## 当前先进 ISP 的模块地图

```text
RAW Frontend:
  black level / bad pixel / lens shading / noise model
  -> 趋势：显式校正 + 隐式学习校正

Joint Reconstruction:
  demosaic + denoise + sometimes super-resolution
  -> 趋势：不要过早把 RAW 错误插值成 RGB

Color:
  AWB / CCM / color space / color constancy
  -> 趋势：统计先验 + 学习式全局/局部颜色估计

HDR and Tone:
  burst merge / exposure fusion / global-local tone mapping
  -> 趋势：多帧鲁棒融合 + tone/denoise 联合

AI-ISP:
  RAW2RGB / low-light / learned smartphone ISP
  -> 趋势：RAW-aware 网络、相机元数据、轻量化

Deployment:
  ONNX / TensorRT / CUDA preprocess / INT8
  -> 趋势：模型和前后处理一起优化
```

## 和本项目对应

- `stage1_soft_isp`：传统模块白盒实现，负责建立输入输出契约。
- `stage2_ai_isp`：学习型图像恢复，负责掌握训练、数据、loss、评估。
- `stage3_cpp_isp`：C++ 高性能传统/混合模块，负责算法落地和 benchmark。
- `stage4_deploy_isp`：模型部署，负责 ONNX、TensorRT、量化、前后处理对齐。

## 练习

1. 画出当前 stage1 pipeline，并标出哪些模块适合传统实现，哪些适合 AI 替代。
2. 选择低光场景，说明 Demosaic、Denoise、Tone Mapping 三个模块为什么会互相影响。
3. 设计一个 Hybrid ISP：传统 BLC/LSC + AI denoise + 传统 CCM/tone，写出输入输出契约。

