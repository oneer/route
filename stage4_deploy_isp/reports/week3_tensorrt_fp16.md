# Week 3：TensorRT FP32/FP16

## 1. 为什么需要

验证 NVIDIA GPU 上 engine 构建、精度变化和性能收益，同时保持 engine compute 与应用端 session latency 两种口径分离。

## 2. 输入输出协议

与 Week 0 相同的 20 张 fixed-shape RGB NCHW float32 输入；FP16 指 TensorRT 内部低精度优化，输出仍以 float tensor 与 ORT CPU 比较。

## 3. 链路角色

`trtexec` 负责 parser/build/engine benchmark；ORT CUDA EP 和 TensorRT EP 负责在真实固定输入上做 correctness 与 host session timing。

## 4. 核心概念/API

ONNX parser → builder → engine → execution context；fixed shape 本次不需 optimization profile。stream、H2D/D2H 和同步决定实际 latency；engine 与 TensorRT/CUDA/GPU 架构绑定。

## 5. 对应文件

- `scripts/09_week3_trt_cuda_benchmark.py`
- `outputs/week3_backend/*.plan`
- `outputs/week3_backend/week3_trtexec_*.log`
- `outputs/week3_backend/fp16_error_maps/`
- `outputs/week3_backend/fp16_failure_cases/`

## 6. 运行命令与环境

```powershell
C:\Users\10439\.conda\envs\stage4-cuda\python.exe `
  stage4_deploy_isp/scripts/09_week3_trt_cuda_benchmark.py --runs 5
```

实测环境：RTX 4060 Ti、driver 591.74、CUDA 12.6、TensorRT 10.8.0、ORT GPU 1.21.1。

## 7. 正确输出

FP32/FP16 plan、构建日志、每次 H2D/compute/D2H JSON、20×3 backend 对齐 CSV、最差 3 张 FP16 comparison/error map。

## 8. 对齐指标与阈值

| Backend | max error vs ORT CPU | quality PSNR | quality SSIM |
|---|---:|---:|---:|
| CUDA FP32 | `3.58e-7` | `32.98387` | `0.9847913` |
| TensorRT FP32 | `5.29e-4` | `32.98247` | `0.9847891` |
| TensorRT FP16 | `1.47e-3` | `32.98200` | `0.9847886` |

FP16 平均质量 PSNR 相对 ORT CPU 仅下降约 `0.00187 dB`，低于项目 warning `0.1 dB`；阈值是项目标准，不是行业统一标准。

## 9. 常见失败与排查

DLL/版本 → ONNX external data → parser → fixed/dynamic shape/profile → provider fallback → 非有限值 → 同步与计时。必须记录 `session.get_providers()`，但 provider 列表本身仍不能证明每个节点都未 fallback。

## 10. 性能测量

| 口径 | FP32 | FP16 |
|---|---:|---:|
| `trtexec` compute mean | `1.968 ms` | `0.979 ms` |
| `trtexec` H2D mean | `1.986 ms` | `2.004 ms` |
| `trtexec` D2H mean | `2.163 ms` | `2.323 ms` |
| `trtexec` latency mean | `6.118 ms` | `5.306 ms` |
| ORT TensorRT EP session mean | `7.886 ms` | `7.458 ms` |

`trtexec` warmup 200 ms、duration 3 s；ORT 每图 warmup 5、runs 5。两行不能混成同一“推理时间”。

## 11. Tradeoff

FP16 compute 接近减半，但 copy 和 host/runtime 开销限制 session 收益；画质损失很小，显存分配日志显示 FP16 execution context 较小，但这不是完整峰值显存报告。

## 12. 证据边界

engine 只对记录环境负责；没有 C++ TensorRT runner、dynamic profile、功耗、Nsight timeline 或跨 GPU 复验。

## 13. 练习与掌握标准

解释为何 compute `0.979 ms` 而 session `7.458 ms`；移动同步点制造虚假 latency；检查最差 FP16 crop 后给出是否接受的结论。
