# Week 12：ONNX / C++ 部署验证

状态：ONNX Runtime Python/C++ 核心推理已实测完成；OpenCV DNN 图片 I/O 样例因本机
未安装 OpenCV C++ SDK，保留为可选验证。

本周解决的问题是：冻结后的 PyTorch 模型能否在 ONNX Runtime Python/C++ 中接收相同
张量并产生数值一致的输出。它验证部署接口，不评价模型是否适合量产端侧。

## 输入输出协议

```text
layout: NCHW
input : float32, RGB, [0,1], [1,3,H,W]
output: float32, RGB, [0,1], [1,3,H,W]
mode  : model.eval() + no_grad/inference mode
```

图片解码、HWC→CHW、uint8→float32、RGB 顺序和输出 clamp 必须在所有 backend 中一致。
ONNX 的 opset、静态/动态 shape 以实际导出命令和模型检查结果为准，不从文件名猜测。

## 环境

- CPU：本机 x64 CPU（CPU inference）
- OS：Windows 10 10.0.19045
- PyTorch：2.12.0+cpu
- ONNX Runtime Python：1.27.0
- ONNX Runtime C++ SDK：1.26.0
- 编译器：MSVC 19.51.36248 x64
- 输入图像 I/O：Python Pillow；C++ latency 只统计 ORT `Session::Run`

## 固定输入

- 图片：`datasets/sidd_tiny/test/noisy/pair_00001.png`
- shape：`1×3×512×512`
- checkpoint：`paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth`
- ONNX：`deployment/onnx/dncnn_sidd_tiny.onnx`，119,763 bytes

## 输出对齐

| Backend | Max abs error vs PyTorch | Mean abs error | PSNR vs PyTorch | SSIM vs PyTorch |
|---|---:|---:|---:|---:|
| ONNX Runtime Python CPU | 2.38419e-7 | 2.98436e-8 | 80.0 | 1.0 |
| ONNX Runtime C++ CPU | 2.38419e-7 | 2.98436e-8 | 80.0 | 1.0 |
| OpenCV DNN C++ | 可选，未安装 OpenCV C++ SDK | - | - | - |

对齐顺序应固定为：

```text
同一输入 tensor
  -> PyTorch reference
  -> ONNX Runtime Python
  -> 保存原始 float tensor
  -> ONNX Runtime C++
  -> max/mean absolute error + PSNR
```

PNG 只适合肉眼检查，8-bit 量化会掩盖或引入误差；严格对齐使用 float tensor。

## Latency

所有结果必须包含 warm-up 次数和重复次数。

| Backend | Warm-up | Repeats | Mean ms | P50 ms | P95 ms |
|---|---:|---:|---:|---:|---:|
| ONNX Runtime Python CPU | 5 | 30 | 72.1614 | 71.7367 | 82.2435 |
| ONNX Runtime C++ CPU | 5 | 30 | 70.3157 | 70.4122 | 80.1261 |
| OpenCV DNN C++ | - | - | 可选 | 可选 | 可选 |

## 验收

- [x] ONNX 文件通过 checker。
- [x] PyTorch 和 ONNX 输出图片已保存。
- [x] `alignment.json` 已生成。
- [x] C++ float 输出和 PNG preview 已生成。
- [x] C++ latency 使用 5 次 warm-up、30 次重复。
- [x] 误差为 CPU backend 浮点算子顺序造成的约 `1e-7` 级差异。
- [x] 工程 summary 已加入 test 指标和 latency。

当前可以写“完成 ONNX Runtime Python/C++ CPU 推理 smoke test 与输出对齐”。不能写成
端侧量产部署、TensorRT 优化或 OpenCV DNN 已验证。

## 练习与掌握标准

1. 故意交换 RGB/BGR，观察 max error 和输出颜色；
2. 故意漏掉 `/255`，解释 range 错误为何不是模型精度问题；
3. 比较固定 `128x128` 与 `512x512` 输入，记录 shape 支持和 latency 口径；
4. 明确 warm-up、repeats、线程、设备和 I/O 是否计时；
5. 能解释“数值对齐通过”不等于“质量、速度、内存和端侧兼容性全部通过”。
