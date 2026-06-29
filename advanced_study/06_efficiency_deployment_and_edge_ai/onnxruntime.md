# ONNX Runtime

## 深度学习目标

阅读 ONNX Runtime 不是为了把整个仓库读完，而是为了理解 stage4 的部署链路为什么会出错、为什么会变快或变慢。你要掌握四个词：Session、Graph Optimization、Execution Provider、IO Binding。

## 从训练到部署会发生什么变化

PyTorch 训练时是动态图，很多操作由 Python 调度。ONNX 导出后，模型变成静态计算图。ONNX Runtime 再对图做优化，并把不同算子分配给不同后端。部署问题通常出在这些地方：

```text
输入归一化不一致
NCHW/NHWC 搞反
动态 shape 未配置
某些算子不被目标 EP 支持
FP16/INT8 导致数值误差
后处理没有和训练保持一致
```

这些问题都不是模型结构本身，却会直接毁掉画质。

## Execution Provider 怎么理解

Execution Provider 可以理解为“算子执行后端”。同一张 ONNX 图中，有的算子可能跑 CPU，有的跑 CUDA，有的跑 TensorRT。如果某个算子 TensorRT 不支持，就可能 fallback 到 CUDA 或 CPU，导致延迟异常。

因此 stage4 不应该只记录总延迟，还要记录后端分配和 fallback 情况。

## 和本项目的具体练习路线

1. 在 `stage4_deploy_isp` 为每次 ONNX 导出保存：opset、输入 shape、输出 shape、归一化范围。
2. 记录 PyTorch vs ORT 的 `max_abs_error`、`mean_abs_error` 和可视化 error map。
3. 如果启用 CUDA/TensorRT EP，记录哪些算子被哪个 EP 接管。
4. 给部署报告加一节“非模型错误检查”：输入 layout、dtype、range、color order、后处理。

## 面试级复述

可以这样复述：ONNX Runtime 是生产推理运行时，不只是“加载 ONNX”。它负责模型图优化、算子执行后端分配和跨平台推理。AI-ISP 部署时，ORT 的关键风险在于输入输出契约、后端 fallback 和数值精度对齐，必须用 PyTorch/ORT 误差和视觉结果双重验证。

## 项目信息
- 项目名称：ONNX Runtime
- GitHub：https://github.com/microsoft/onnxruntime
- Star 数或活跃度：GitHub 大型活跃项目，长期维护，支持多执行后端；具体 Star 数建议阅读时以 GitHub 页面为准。
- 主要语言：C++、C、Python

## 项目解决什么问题

ONNX Runtime 解决的是“把训练框架里的模型稳定、高效地放到生产推理环境”的问题。它支持 CPU、CUDA、TensorRT、DirectML 等后端，是 stage4 中 PyTorch -> ONNX -> C++ 推理链路的核心基础。

## 项目目录结构解读

初学者不需要一开始读完整仓库。建议先理解这些层次：

- `onnxruntime/core/`：推理核心，包括 session、graph、kernel、execution provider。
- `onnxruntime/python/`：Python API 封装。
- `onnxruntime/test/`：大量模型、算子和后端测试。
- `docs/`：构建、部署、性能调优文档。

## 核心模块说明

最重要的概念是 Session、Graph Optimization、Execution Provider 和 Kernel。Session 管理模型加载和推理生命周期；图优化会融合算子、消除冗余；Execution Provider 决定算子跑在 CPU、CUDA 还是 TensorRT；Kernel 是具体算子实现。

## 如何和当前项目关联

stage4 已经有 ONNX 导出、ONNX Runtime Python/C++ 对齐和 CPU 推理 smoke test。阅读 ONNX Runtime 可以帮助你把“能跑”升级到“知道为什么对齐、为什么快或慢、为什么某个算子落回 CPU”。

## 值得学习的工程设计

- 后端抽象：同一张图可以分配给不同 EP。
- 图优化：部署不是简单加载模型，还要改写计算图。
- 测试矩阵：跨平台、跨后端、跨精度验证。
- C API 稳定性：生产部署常依赖稳定 ABI。

## 初学者阅读顺序

1. 先读官方 docs 中模型加载和 inference 示例。
2. 再读 Execution Provider 文档，理解 CPU/CUDA/TensorRT 的差异。
3. 回到 stage4 的 C++ runner，对照 session 创建、输入输出绑定和 tensor shape。
4. 最后看 graph optimization 相关文档。

## 可迁移到当前项目的功能点

1. 给 stage4 增加执行后端报告：模型哪些算子跑在哪个 EP。
2. 增加动态 shape 或固定 shape 的对比实验。
3. 把 PyTorch/ONNX/ORT 的误差阈值写成部署契约。

## 阅读后应该掌握什么

你应该能解释：ONNX Runtime 不只是“跑 ONNX 的库”，而是一套围绕图优化、后端调度和生产推理稳定性的系统。
