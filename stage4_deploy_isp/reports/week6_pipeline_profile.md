# 第 6 周：CUDA 前后处理、Pipeline 串联与性能剖析

## 目标

Week 6 关注端到端链路，而不是只报模型 inference time。当前阶段三还在收尾，因此本周先做轻量 RGB denoise pipeline：

```text
PNG noisy input
  -> preprocess: RGB uint8 / HWC -> float32 / NCHW / [0, 1]
  -> ONNX Runtime inference
  -> postprocess: clamp -> NCHW -> HWC -> uint8
  -> save output
```

## 已新增

- `scripts/07_week6_pipeline_profile.py`
- `scripts/10_week6_cuda_preprocess_benchmark.py`
- `cuda_kernels/normalize.cu`
- `cuda_kernels/pack_raw.cu`
- `cpp/include/cuda_preprocess.hpp`
- `cpp/src/cuda_preprocess_benchmark.cpp`
- CMake option：`STAGE4_BUILD_CUDA_PREPROCESS`

`normalize.cu` 是 RGB preprocess 的 CUDA 替换点；`pack_raw.cu` 是后续 RAW / RGGB AI-ISP 模型的替换点。

## CPU Pipeline 分阶段性能剖析

运行命令：

```powershell
python stage4_deploy_isp/scripts/07_week6_pipeline_profile.py
```

结果：

| 阶段 | 平均耗时 |
|---|---:|
| preprocess | 19.45 ms |
| inference | 87.51 ms |
| postprocess | 8.03 ms |
| save output | 38.32 ms |
| end-to-end | 153.31 ms |

这个结果说明，模型 inference 只占端到端流程的一部分。即使后续 TensorRT 把 inference 降到很低，如果 preprocess、copy、postprocess 或 I/O 不优化，端到端收益也会被稀释。

## CUDA 前处理性能测试

由于当前 CUDA 12.6 + VS Build Tools 2026 的 `nvcc` host compiler 路径仍会早退，本次先采用 NVRTC runtime compilation 编译同一个 normalize kernel，并通过 CUDA Driver API launch。

运行命令：

```powershell
C:\Users\10439\.conda\envs\stage4-cuda\python.exe stage4_deploy_isp/scripts/10_week6_cuda_preprocess_benchmark.py --runs 200
```

输出文件：

- `outputs/week6_pipeline/week6_cuda_preprocess_summary.csv`

结果：

| 项目 | 结果 |
|---|---:|
| 输入 | `pair_00001.ppm` |
| 尺寸 | 512 x 512 x 3 |
| 测量次数 | 200 |
| CUDA 编译路径 | NVRTC |
| CPU 前处理平均耗时 | 5.031 ms |
| CUDA kernel 平均耗时 | 0.0092 ms |
| 最大绝对误差 | 5.96e-8 |
| 平均绝对误差 | 8.22e-9 |

说明：这里的 CUDA 数字是 normalize kernel 本身，不包含 H2D / D2H 和完整 pipeline 调度。它证明 kernel 逻辑、layout 和数值对齐已经跑通；后续要继续补 copy、pinned memory、stream overlap 和 Nsight timeline。

## 当前限制

- `STAGE4_BUILD_CUDA_PREPROCESS=ON` 的 CMake/nvcc 路线已补代码入口，但当前机器的 CUDA 12.6 对 VS Build Tools 2026 host compiler 兼容性不稳定，配置阶段尚未通过。
- NVRTC 路线已完成 kernel 编译、launch 和 CPU vs CUDA 输出对齐。
- 阶段三 C++ ISP 模块尚未正式接入 Week 6 pipeline。

## AI-ISP / ISP 算法岗表达

这一周要讲清：

- 传统 ISP 模块和 AI 模块之间必须约定数据协议。
- RAW-domain 模型需要 pack RGGB、black level、white level、normalization。
- RGB-domain denoise 模型更容易部署，但离真正 sensor RAW ISP 更远。
- CUDA kernel 快不等于端到端快；还要把 H2D / D2H、postprocess、I/O 和 pipeline overlap 纳入 profiling。
