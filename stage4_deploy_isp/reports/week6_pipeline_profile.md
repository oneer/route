# Week 6 CUDA 前后处理、Pipeline 串联与 Profiling

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
- `cuda_kernels/normalize.cu`
- `cuda_kernels/pack_raw.cu`

`normalize.cu` 是 RGB preprocess 的 CUDA 替换点；`pack_raw.cu` 是后续 RAW / RGGB AI-ISP 模型的替换点。

## 运行命令

```powershell
python stage4_deploy_isp/scripts/07_week6_pipeline_profile.py
```

## 当前限制

由于当前没有 `nvcc` 和 CUDA Toolkit，CUDA kernel 只完成源码骨架，尚未编译运行。当前 profiling 使用 CPU preprocess + ORT CPU inference。

## 当前 profiling 结果

| 阶段 | 平均耗时 |
|---|---:|
| preprocess | 19.45 ms |
| inference | 87.51 ms |
| postprocess | 8.03 ms |
| save output | 38.32 ms |
| end-to-end | 153.31 ms |

这个结果说明，模型 inference 只占端到端流程的一部分。即使后续 TensorRT 把 inference 降到很低，如果 preprocess、copy、postprocess 或 I/O 不优化，端到端收益也会被稀释。

## AI-ISP / ISP 算法岗表达

这一周要讲清：

- 传统 ISP 模块和 AI 模块之间必须约定数据协议。
- RAW-domain 模型需要 pack RGGB、black level、white level、normalization。
- RGB-domain denoise 模型更容易部署，但离真正 sensor RAW ISP 更远。
- 端到端 latency 可能被 preprocess、copy、postprocess 或保存图像拖慢，不能只报 engine time。
