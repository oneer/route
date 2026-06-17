# Week 3 TensorRT / 高性能后端与 FP16

## 目标

原计划是完成 TensorRT FP32 / FP16 engine 构建、C++ runtime 和端到端 latency 对比。

## 当前环境结论

当前机器有 RTX 4060 Ti 和 NVIDIA Driver，但阶段四当前 Python / 系统工具链缺少：

- CUDA 版 PyTorch：当前 `torch==2.12.0+cpu`。
- `nvcc`。
- `trtexec`。
- TensorRT Python / C++ SDK。
- CMake / C++ 编译器。

因此本周无法完成真正的 TensorRT engine 实测。为保证完整路线继续推进，本周先完成后端探测和 ONNX Runtime FP32 CPU benchmark，作为后续 TensorRT 对比基线。

## 运行命令

```powershell
python deploy_isp_stage4/scripts/05_week3_backend_probe_benchmark.py
```

## 输出文件

- `outputs/week3_backend/week3_backend_summary.csv`
- `outputs/week3_backend/week3_ort_cpu_latency.csv`

## 当前 benchmark 结果

| 项目 | 结果 |
|---|---:|
| ONNX Runtime providers | AzureExecutionProvider; CPUExecutionProvider |
| `trtexec` | missing |
| `nvcc` | missing |
| `cmake` | missing |
| `nvidia-smi` | available |
| ORT CPU mean latency | 93.28 ms |
| ORT CPU p50 latency | 90.63 ms |
| ORT CPU p90 latency | 111.65 ms |

和 Week 0.5 的 PyTorch CPU p50 182.86 ms 相比，ONNX Runtime CPU baseline 已经明显更快。这说明 graph-level runtime 优化本身有收益，但这还不是端到端 GPU 部署结论。

## 后续补齐标准

等工具链补齐后，Week 3 需要补：

1. `trtexec --onnx=... --saveEngine=...` 构建 FP32 engine。
2. `trtexec --fp16` 构建 FP16 engine。
3. 记录 engine latency、H2D、D2H、end-to-end latency。
4. TensorRT output 与 PyTorch / ORT output 做 max abs error、mean abs error、PSNR 对齐。
5. 分析 FP16 对暗区噪声、颜色、纹理和高光的影响。

## AI-ISP / ISP 算法岗视角

对于 AI-ISP / ISP 算法岗，TensorRT 不是目的。真正要讲清的是：FP16 是否改变了画质，速度提升是否值得，部署输出是否引入偏色、过平滑或暗区噪声残留。
