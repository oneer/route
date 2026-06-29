# 实时端侧 ISP：HDRNet、ONNX Runtime、TensorRT 与 CUDA 前后处理

## 模块定位

端侧 ISP 关注的是：

```text
模型/算法是否能在真实设备上按时跑完
```

画质再好，如果延迟、功耗、内存、带宽不满足，工程上就不可用。

## 传统做法

传统 ISP 硬件模块非常快，因为它们通常是流式、定点、低内存访问、专用电路或高度优化的 C/C++/SIMD/CUDA。AI 模型加入后，会带来额外算力和内存压力。

## 当前先进做法

### 低分辨率预测参数，高分辨率快速执行

HDRNet 是典型代表。网络不直接处理全分辨率每个像素，而是预测 bilateral grid 或增强参数，再用快速算子应用到原图。

### 模型轻量化

常见方式包括：

- 小通道数和小 block。
- depthwise convolution。
- low-resolution branch。
- FP16。
- INT8 QDQ。
- 剪枝或蒸馏。

### 前后处理上 GPU

很多部署慢不是模型慢，而是 CPU/GPU 数据搬运和前后处理慢。RAW pack、normalize、resize、color convert 如果在 CPU 做，可能抵消 TensorRT 加速收益。

## ONNX Runtime 和 TensorRT 的角色

ONNX Runtime 更像跨平台推理运行时，支持不同 Execution Provider。TensorRT 更像 NVIDIA GPU 上的深度优化 engine builder。两者都不是“点一下导出就完事”，都需要检查输入契约、shape、dtype、精度和后端支持。

## 工程注意点

- 端到端 latency 要包含 preprocess、inference、postprocess、copy。
- FP16 要看暗部误差和颜色误差。
- INT8 要看 error map，不只看平均指标。
- 动态 shape 方便但可能降低优化空间。
- 输出图像任务比分类任务更怕量化误差。

## 和本项目对应

- stage4：ONNX、ORT C++、TensorRT、INT8、CUDA preprocess。
- stage3：C++/CUDA 传统算子可做模型前后处理。
- stage2：训练模型时就要考虑可导出和可量化。
- stage1：保证图像域和颜色契约不乱。

## 练习

1. 在 stage4 统计完整端到端 latency：读图、预处理、推理、后处理、保存。
2. 比较 PyTorch、ORT CPU、ORT CUDA、TensorRT FP16 的输出误差。
3. 对 INT8 输出做暗部 crop error map。
4. 把 normalize 或 pack raw 从 Python/CPU 改成 CUDA kernel，并比较耗时。

## 你应该掌握

先进端侧 ISP 的关键是画质和系统约束共同设计。模型结构、输入 shape、精度、前后处理和内存搬运都属于 ISP 部署的一部分。

