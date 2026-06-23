# Week 6：CUDA 前处理与 Pipeline Profile

## 1. 为什么需要

kernel、inference 和端到端 latency 是三个不同问题；只优化最快的局部不一定改善用户等待时间。

## 2. 输入输出协议

CPU/CUDA normalize 都执行 RGB uint8 HWC → float32 NCHW `[0,1]`。`pack_raw.cu` 面向未来 RGGB RAW，不匹配当前 RGB 模型，未接入本链路。

## 3. 链路角色

当前 CPU pipeline：load/preprocess → ORT CPU → clamp/transpose/round → save。CUDA 实验只替换 normalize，并未把 device tensor零拷贝送入 ORT/TensorRT。

## 4. 核心概念/API

一维 grid/block、线程索引、边界判断、HWC coalesced read、NCHW scattered write、pageable memory、`cuCtxSynchronize`。生产优化还需 pinned memory、stream、CUDA event 和 Nsight。

## 5. 对应文件

- `cuda_kernels/normalize.cu`
- `cuda_kernels/pack_raw.cu`
- `scripts/07_week6_pipeline_profile.py`
- `scripts/10_week6_cuda_preprocess_benchmark.py`
- `cpp/src/cuda_preprocess_benchmark.cpp`

## 6. 运行命令与环境

```powershell
python stage4_deploy_isp/scripts/07_week6_pipeline_profile.py
C:\Users\10439\.conda\envs\stage4-cuda\python.exe `
  stage4_deploy_isp/scripts/10_week6_cuda_preprocess_benchmark.py --runs 200
```

CUDA 12.6、RTX 4060 Ti；kernel 通过 NVRTC + CUDA Driver API 执行。

## 7. 正确输出

100 条 CPU pipeline run（20 图×5）、p50/p90 summary；CUDA H2D/kernel/D2H summary；CPU/CUDA max error `5.96e-8`。

## 8. 对齐指标与阈值

CUDA normalize 相对 CPU max/mean error `5.96e-8/8.22e-9`，低于 float32 preprocess 项目阈值 `1e-6`。

## 9. 常见失败与排查

shape/channels → grid 边界 → HWC/NCHW index → `/255` → kernel launch status → 同步 → copy direction → output tensor。RAW pack 不得误接 RGB 模型。

## 10. 性能测量

CPU pipeline（每图 inference warmup 3、runs 5；save 每图一次）：

| 阶段 | mean | p50 | p90 |
|---|---:|---:|---:|
| preprocess | `14.03` | `10.84` | `20.75` ms |
| inference | `151.24` | `139.95` | `223.79` ms |
| postprocess | `7.52` | `6.02` | `10.81` ms |
| compute E2E，不含 save | `172.79` | `160.50` | `249.83` ms |

单次 save 平均 `49.54 ms`。

CUDA preprocess（pageable memory，明确同步）：

| 阶段 | 时间 |
|---|---:|
| CPU normalize | `2.498 ms` |
| H2D | `1.082 ms` |
| kernel | `0.0091 ms` |
| D2H | `2.707 ms` |
| GPU stage E2E | `3.798 ms` |

## 11. Tradeoff

kernel 比 CPU 快，但 pageable copy 使 GPU stage 总体更慢。下一步应避免 D2H，把 preprocess 输出直接交给 GPU inference；之后再测 pinned memory/stream overlap，而不是继续微调 0.009 ms kernel。

## 12. 证据边界

CUDA preprocess 未接入完整推理；无 pinned memory、CUDA event、Nsight、阶段三 ISP、功耗或峰值显存。CMake/nvcc executable 仍受当前 VS host compiler 兼容问题影响。

## 13. 练习与掌握标准

移除同步观察虚假 latency；实现 pinned memory 对比；解释为何 `0.009 ms` kernel 没有带来 E2E 收益；能画出 host/device 边界即达标。
