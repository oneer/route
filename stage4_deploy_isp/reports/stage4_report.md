# 阶段四学习报告：端侧 AI-ISP 部署与 CUDA 推理

## 1. 项目定位

本阶段面向 AI-ISP / ISP 算法工程师。目标不是单纯证明“会 ONNX / TensorRT”，而是建立一个可复现、可对齐、可测量、可解释的 AI 图像恢复部署闭环。

当前阶段三尚未完全收尾，因此阶段四先使用阶段二已有 RGB denoise 模型形成独立闭环；阶段三 C++ ISP 模块后续再作为正式 preprocess / postprocess 接入。

## 2. 已完成内容总览

| Week | 内容 | 状态 |
|---|---|---|
| Week 0.5 | 固定模型、固定测试集、PyTorch baseline | 已完成 |
| Week 1 | ONNX 导出与 ORT 对齐 | 已完成 |
| Week 2 | ONNX Runtime C++ baseline 源码、编译与输出对齐 | 已完成 |
| Week 3 | TensorRT FP32 / FP16 与 CUDA / TensorRT EP 对齐 | 已完成 |
| Week 4 | INT8 QDQ 量化与画质损失 | 已完成 |
| Week 5 | NCNN / MNN 移动端路径 | 工具链缺失，完成适配性分析 |
| Week 6 | Pipeline profiling 与 CUDA preprocess kernel | 已完成 CPU pipeline + NVRTC CUDA kernel |
| Week 7 | 报告、复现清单、面试表达 | 已完成并更新 |

## 3. 数据与模型

固定测试集：

- 数据：SIDD tiny validation subset。
- 样本：20 对 noisy / clean RGB 图像。
- manifest：`data/test_inputs/week0_fixed_manifest.csv`。

主部署模型：

- 模型：DnCNN。
- checkpoint：阶段二 `paired_rgb_sidd_tiny_dncnn_l2_300`。
- 输入：RGB 3ch，`NCHW`，`float32`，`[0,1]`。
- 输出：RGB 3ch，`NCHW`，`float32`，输出后 clamp 到 `[0,1]`。

## 4. PyTorch Baseline

| 指标 | 结果 |
|---|---:|
| Noisy mean PSNR | 26.57 dB |
| PyTorch output mean PSNR | 32.98 dB |
| PSNR gain | +6.42 dB |
| Noisy mean SSIM | 0.934 |
| PyTorch output mean SSIM | 0.985 |
| CPU latency p50 | 182.86 ms |

结论：模型在固定测试集上有明确画质提升，可作为部署 golden baseline。

## 5. ONNX 对齐

ONNX graph：

```text
Conv x5
Relu x4
Sub x1
```

| 指标 | 结果 |
|---|---:|
| ORT vs PyTorch max abs error | 4.17e-7 |
| ORT vs PyTorch mean abs error | 3.40e-8 |
| ORT quality PSNR | 32.98 dB |

结论：ONNX Runtime 和 PyTorch 输出高度一致，ORT 可以作为后续后端 correctness baseline。

## 6. TensorRT / CUDA

Week 3 已补齐 CUDA / TensorRT 实测。

`trtexec` engine benchmark：

| precision | GPU compute mean | GPU compute p50 |
|---|---:|---:|
| FP32 | 1.964 ms | 1.352 ms |
| FP16 | 0.870 ms | 0.585 ms |

ORT backend 对齐与延迟：

| backend | active providers | mean latency | max abs error vs ORT CPU |
|---|---|---:|---:|
| CPU | CPUExecutionProvider | 74.50 ms | baseline |
| CUDA | CUDAExecutionProvider; CPUExecutionProvider | 10.91 ms | 3.58e-7 |
| TensorRT FP32 | TensorrtExecutionProvider; CUDAExecutionProvider; CPUExecutionProvider | 8.26 ms | 5.29e-4 |
| TensorRT FP16 | TensorrtExecutionProvider; CUDAExecutionProvider; CPUExecutionProvider | 7.45 ms | 1.47e-3 |

结论：FP16 engine 有明显速度收益，且 float tensor 误差仍处于较小范围。后续要补失败样本 crop sheet，看误差是否形成可见画质问题。

## 7. INT8 量化

| 指标 | 结果 |
|---|---:|
| Calibration images | 10 |
| FP32 mean PSNR | 32.98 dB |
| INT8 mean PSNR | 32.89 dB |
| Mean PSNR drop | 0.091 dB |
| Max PSNR drop | 0.337 dB |
| Worst sample | pair_00005 |
| FP32 p50 latency | 93.91 ms |
| INT8 p50 latency | 87.06 ms |

结论：当前 ORT CPU QDQ INT8 初步可接受，但还需要针对最差样本做主观画质分析，尤其关注红色高饱和区域、暗区噪声和纹理过平滑。

## 8. Pipeline Profiling 与 CUDA Preprocess

CPU pipeline：

| 阶段 | 平均耗时 |
|---|---:|
| preprocess | 19.45 ms |
| inference | 87.51 ms |
| postprocess | 8.03 ms |
| save output | 38.32 ms |
| end-to-end | 153.31 ms |

NVRTC CUDA preprocess：

| 项目 | 结果 |
|---|---:|
| CPU normalize mean | 5.031 ms |
| CUDA normalize kernel mean | 0.0092 ms |
| max abs error | 5.96e-8 |
| mean abs error | 8.22e-9 |

结论：CUDA normalize kernel 已完成编译、launch 和 CPU 对齐。当前数字是 kernel 本身，不含 H2D / D2H；后续端到端优化必须继续测 copy、pinned memory、stream overlap 和 Nsight timeline。

## 9. 当前限制

- Week 5 移动端工具链仍缺：NCNN / MNN / Android adb。
- CMake + `nvcc` 编译 CUDA executable 的入口已补，但 CUDA 12.6 与 VS Build Tools 2026 host compiler 兼容性仍不稳定；当前通过 NVRTC 完成 CUDA kernel 编译实测。
- 阶段三 C++ ISP 模块尚未正式接入 Week 6 pipeline。

## 10. 后续补强

1. 用最差 INT8 / FP16 样本做 failure case crop sheet。
2. 把 H2D / D2H、pinned memory、CUDA stream 和 Nsight timeline 补进 Week 6。
3. 等阶段三完成后，把 C++ BLC / LSC / tone mapping 接入 Week 6 pipeline。
4. 如果投手机厂商端侧岗位，再补 NCNN / MNN + Android 真机测试。
