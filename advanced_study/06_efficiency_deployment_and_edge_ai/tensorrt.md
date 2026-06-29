# NVIDIA TensorRT

## 深度学习目标

TensorRT 要学的是“编译型推理优化”的思维。它不是普通库调用，而是把 ONNX 网络、输入 shape、精度策略和 GPU 硬件约束一起编译成 engine。读它时要不断联系 stage4：为什么 FP16 快、为什么 INT8 会损画质、为什么 engine 和具体 GPU/shape 绑定。

## TensorRT 的核心流程

典型流程是：

```text
ONNX model
-> parse network
-> set optimization profile
-> choose precision FP32/FP16/INT8
-> build engine
-> create execution context
-> enqueue inference
```

和 ONNX Runtime 不同，TensorRT 很强调 build 阶段。很多优化在 build engine 时已经决定，包括 layer fusion、kernel selection、memory plan 和 precision tactic。

## FP16 和 INT8 怎么理解

FP16 通常是较安全的加速方式，误差一般较小，但仍需检查暗部、边缘和颜色。INT8 速度和吞吐可能更好，但需要 calibration 或 QDQ 图。图像恢复模型对量化比较敏感，因为输出每个像素都要保真，暗部小误差会被视觉放大。

对 AI-ISP 来说，INT8 不能只看分类准确率式指标，而要看 PSNR、SSIM、error map、暗部彩噪和色偏。

## 和本项目的具体练习路线

1. 用 `trtexec` 对 stage4 的 ONNX 记录 FP32/FP16 延迟、显存和 layer profile。
2. 对 INT8 输出做 failure case crop，不只看平均 PSNR。
3. 建立精度决策表：FP32 作为参考，FP16 是否可接受，INT8 哪些场景不可接受。
4. 如果某个算子性能差，记录是否需要 CUDA preprocess 或 TensorRT plugin。

## 面试级复述

可以这样复述：TensorRT 通过构建针对 NVIDIA GPU 的优化 engine 来加速推理，核心包括图融合、kernel tactic、FP16/INT8 和 optimization profile。AI-ISP 模型部署时，它的价值是低延迟高吞吐，风险是精度损失、动态 shape 复杂和不支持算子，需要用画质指标、误差图和真实延迟共同评估。

## 项目信息
- 项目名称：NVIDIA TensorRT
- GitHub：https://github.com/NVIDIA/TensorRT
- Star 数或活跃度：NVIDIA 官方高性能推理项目，持续发布，与 CUDA/GPU 架构强绑定；具体 Star 数建议阅读时以 GitHub 页面为准。
- 主要语言：C++、CUDA、Python

## 项目解决什么问题

TensorRT 解决的是 NVIDIA GPU 上的高性能深度学习推理问题。它通过图优化、层融合、kernel 选择、FP16/INT8、engine 构建和 profiling，把通用模型变成适合具体 GPU 的推理引擎。

## 项目目录结构解读

建议初学者先看：

- `samples/`：最适合入门，展示 ONNX parser、engine build、推理和 INT8。
- `tools/`：包括 `trtexec` 等性能测试工具。
- `demo/` 或文档示例：帮助理解 engine、builder、runtime。
- `plugin/`：自定义算子和插件机制，高阶再读。

## 核心模块说明

核心概念包括 Builder、Network、Engine、Execution Context、Optimization Profile 和 Calibration。Builder 负责把网络编译成 engine；Engine 是针对硬件优化后的推理计划；Execution Context 执行推理；INT8 calibration 决定量化尺度。

## 如何和当前项目关联

stage4 已经有 TensorRT backend、FP16 engine、INT8 QDQ 和 profiling 产物。阅读 TensorRT 可以帮助你理解为什么同一 ONNX 模型在 ORT CPU、ORT CUDA、TensorRT FP16、TensorRT INT8 下质量和速度不同。

## 值得学习的工程设计

- 构建期优化和运行期执行分离。
- 精度策略显式化：FP32、FP16、INT8 都需要验证。
- profiling 工具链完整：不是只看总耗时，还要看 layer time。
- 插件机制允许补齐不支持或低效算子。

## 初学者阅读顺序

1. 先用 `trtexec` 跑一个现有 ONNX，理解输入 shape、FP16、workspace。
2. 再读 sampleONNXMNIST 或类似 sample，理解 C++ build/infer 流程。
3. 对照 stage4 的 `week3_tensorrt_fp16.md` 和 `week4_int8_quantization.md`。
4. 最后再看 plugin 和 dynamic shape。

## 可迁移到当前项目的功能点

1. 给 stage4 增加 layer-wise profiling 摘要。
2. 把 FP16/INT8 的画质损失整理成模型卡。
3. 为不支持的预处理算子规划 CUDA kernel 或 TensorRT plugin。

## 阅读后应该掌握什么

你应该能解释：TensorRT 的核心不是“换个后端”，而是把模型、精度、shape 和硬件约束一起编译优化。
