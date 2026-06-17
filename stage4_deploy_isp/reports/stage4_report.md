# 阶段四学习报告：端侧 AI-ISP 部署与 CUDA 推理

## 1. 项目定位

本阶段面向 AI-ISP / ISP 算法工程师。目标不是单纯证明“我会 ONNX / TensorRT”，而是建立一个可复现、可对齐、可解释的 AI 图像恢复部署闭环。

当前阶段三尚未完全收尾，因此阶段四先使用阶段二已有 RGB denoise 模型形成独立闭环；阶段三 C++ ISP 模块后续再作为正式 preprocess / postprocess 接入。

## 2. 已完成内容总览

| Week | 内容 | 状态 |
|---|---|---|
| Week 0.5 | 固定模型、固定测试集、PyTorch baseline | 已完成 |
| Week 1 | ONNX 导出与 ORT 对齐 | 已完成 |
| Week 2 | ONNX Runtime C++ baseline 源码、编译与输出对齐 | 已完成 |
| Week 3 | TensorRT / FP16 | 当前环境缺 TensorRT，完成 ORT CPU benchmark |
| Week 4 | INT8 QDQ 量化与画质损失 | 已完成 |
| Week 5 | NCNN / MNN 移动端路径 | 工具链缺失，完成适配性分析 |
| Week 6 | Pipeline profiling 与 CUDA kernel 骨架 | 已完成 CPU pipeline，CUDA 编译受限 |
| Week 7 | 报告、复现清单、面试表达 | 已完成 |

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

选择理由：

- 当前 checkpoint 指标稳定。
- ONNX graph 简单，适合先跑通部署闭环。
- 残差学习可解释为 AI denoise 模块。

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

## 6. INT8 量化

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

## 7. Pipeline Profiling

| 阶段 | 平均耗时 |
|---|---:|
| preprocess | 19.45 ms |
| inference | 87.51 ms |
| postprocess | 8.03 ms |
| save output | 38.32 ms |
| end-to-end | 153.31 ms |

结论：端到端时间明显不等于模型 inference time。后续接 TensorRT / CUDA 时，需要同时优化 preprocess、copy 和 postprocess。

## 8. 工具链限制

当前环境限制：

- PyTorch 是 CPU build。
- 缺少 CMake 和 C++ 编译器。
- 缺少 CUDA Toolkit / nvcc。
- 缺少 TensorRT / trtexec。
- 缺少 NCNN / MNN / adb。

这些限制导致 Week 3 TensorRT、Week 5 移动端、Week 6 CUDA 实测尚未完成。Week 2 C++ ORT baseline 已在补齐 VS Build Tools 和 ONNX Runtime C++ SDK 后完成编译与 smoke test。

## 9. 先进内容调研

- DnCNN：残差学习去噪，适合解释 AI denoise 模块如何预测噪声残差。链接：https://arxiv.org/abs/1608.03981
- NAFNet：更现代的高效图像恢复 baseline，后续可作为第二部署模型，但部署复杂度高于 DnCNN。链接：https://arxiv.org/abs/2204.04676
- SIDD / SIDD+：真实手机噪声数据对图像恢复和 AI-ISP 更有意义，避免只在 AWGN 上做玩具实验。链接：https://arxiv.org/abs/2005.04117

## 10. 后续补强

1. 安装 CUDA Toolkit / TensorRT，补 Week 3 FP32 / FP16 engine 实测。
2. 用最差 INT8 样本做 failure case crop sheet。
3. 等阶段三完成后，把 C++ BLC / LSC / tone mapping 接入 Week 6 pipeline。
4. 如投手机厂商端侧岗位，再补 NCNN / MNN + Android 真机测试。
