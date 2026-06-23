# 阶段四：端侧 AI-ISP 部署与 CUDA 推理学习路线

> 更新日期：2026-06-23。实际教程唯一入口为 `stage4_deploy_isp/README.md`。

## 阶段目标

学习者应独立完成：

```text
固定 checkpoint/manifest/contract
→ PyTorch baseline
→ ONNX checker + ORT Python
→ ORT C++ raw tensor
→ FP32/FP16 或 INT8
→ pre/H2D/infer/D2H/post/save profiling
→ 失败案例与证据边界
```

重点是正确性、画质、可复现和测量口径，不是“模型成功转换”。

## 七周安排

| 周次 | 核心问题 | 必须交付 |
|---|---|---|
| Week 0 | 部署对象是否固定 | model card、hash、contract、manifest、PyTorch baseline |
| Week 1 | ONNX 是否语义一致 | checker、graph、max/mean/RMSE/PSNR、error map |
| Week 2 | C++ 是否保持 tensor 协议 | 20 张 raw float tensor 对齐、warm/cold 说明 |
| Week 3 | FP16 是否值得 | engine 环境、compute/copy/session 口径、PSNR/SSIM、最差 crop |
| Week 4 | INT8 是否可信 | 独立 calibration/evaluation、QDQ 方法、画质/大小/latency |
| Week 5 | 目标平台是否真实 | 有设备则实测；无设备明确为设计章节 |
| Week 6 | 局部优化是否改善 E2E | pre/H2D/kernel/infer/D2H/post/save、同步、p50/p90 |

## 每周统一教学模板

每份周报必须包含：

1. 为什么需要；
2. 输入输出协议；
3. 工具/运行时角色；
4. 核心概念/API；
5. 对应文件；
6. 命令和环境；
7. 正确输出；
8. 指标与项目阈值；
9. 失败排查顺序；
10. 性能测量；
11. 画质/速度/内存 tradeoff；
12. 证据边界；
13. 练习与掌握标准。

## 硬性验收

- 所有后端使用同一固定输入；量化 calibration 与 evaluation 隔离。
- Python/C++ 比较 raw tensor，最终 PNG 仅用于可视化。
- correctness matrix 至少有 max/mean/RMSE、alignment PSNR、quality PSNR/SSIM。
- latency matrix 标明设备、shape、precision、warmup/runs、同步和 I/O。
- `trtexec` compute、ORT session、C++ run 和 E2E 不混用。
- FP16/INT8 有最差 error map/crop 和可接受性结论。
- TensorRT engine 记录 GPU/CUDA/TensorRT 环境，不承诺通用。
- 无 Android 真机时不得声称移动端部署完成。

## 后端选择

- NVIDIA GPU 岗：TensorRT 为主，补 C++ runner、dynamic profile、Nsight、INT8。
- 手机影像岗：NCNN 或 MNN 为主，必须有真实 Android arm64、CPU/Vulkan、内存、温度证据。
- Intel 边缘端：OpenVINO。
- 跨平台应用：根据算子、量化和目标硬件评估 ORT/TFLite。

本项目已实践 TensorRT；后续移动端只选择 NCNN 一条路径，避免同时铺开多个未验证后端。

## 调试顺序

manifest → RGB/BGR → NCHW/NHWC → range → dtype → shape/name → clamp/round → provider/fallback → FP16/profile → calibration → synchronization → I/O。

## Capstone

从 checkpoint 独立生成 model card、ONNX、ORT Python/C++ raw 对齐、至少一种加速或量化、端到端拆时、失败分析和统一矩阵。具体题目见 `reports/debugging_exercises_and_capstone.md`。

## 官方资料

资料于 2026-06-23 核对：

- [PyTorch ONNX](https://docs.pytorch.org/docs/stable/onnx.html)
- [ONNX Runtime C/C++](https://onnxruntime.ai/docs/api/c/)
- [ONNX Runtime Quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
- [TensorRT](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/)
- [trtexec](https://docs.nvidia.com/deeplearning/tensorrt/latest/reference/command-line-programs.html)
- [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [NCNN](https://github.com/Tencent/ncnn)
- [MNN](https://github.com/alibaba/MNN)
