# 第 3 周：TensorRT、高性能后端与 FP16

## 目标

完成 NVIDIA GPU 上的 TensorRT FP32 / FP16 engine 构建、benchmark，并把 CUDA / TensorRT 输出与 ORT CPU golden output 做数值对齐。

## 当前环境结论

当前 Week 3 GPU 部署环境已补齐：

- GPU：NVIDIA GeForce RTX 4060 Ti，driver 591.74。
- CUDA Toolkit：12.6，`nvcc` 可见。
- TensorRT：10.8.0，`trtexec` 可用。
- ONNX Runtime GPU：`onnxruntime-gpu 1.21.1`。
- ORT available providers：`TensorrtExecutionProvider; CUDAExecutionProvider; CPUExecutionProvider`。

TensorRT / cuDNN DLL 需要显式加入 PATH：

- `D:\Env\TensorRT\TensorRT-10.8.0.43\bin`
- `D:\Env\TensorRT\TensorRT-10.8.0.43\lib`
- `C:\Program Files\NVIDIA\CUDNN\v9.23\bin\12.9\x64`
- `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin`

## 运行命令

```powershell
C:\Users\10439\.conda\envs\stage4-cuda\python.exe stage4_deploy_isp/scripts/09_week3_trt_cuda_benchmark.py --runs 5
```

## 输出文件

- `outputs/week3_backend/dncnn_sidd_tiny_fp32_trt108.plan`
- `outputs/week3_backend/dncnn_sidd_tiny_fp16_trt108.plan`
- `outputs/week3_backend/week3_trtexec_summary.csv`
- `outputs/week3_backend/week3_backend_summary.csv`
- `outputs/week3_backend/week3_gpu_alignment_latency.csv`
- `outputs/week3_backend/week3_trtexec_fp32.log`
- `outputs/week3_backend/week3_trtexec_fp16.log`

## trtexec 引擎性能测试

| 精度 | 引擎状态 | GPU 平均计算耗时 | GPU 计算耗时 p50 |
|---|---|---:|---:|
| FP32 | built | 1.964 ms | 1.352 ms |
| FP16 | built | 0.870 ms | 0.585 ms |

结论：在 `trtexec` 的纯 engine 视角下，FP16 明显快于 FP32。但这不是端到端 pipeline latency，不能直接替代真实输入、前后处理和拷贝后的总耗时。

## ORT CUDA / TensorRT EP 对齐与延迟

| 后端 | 实际启用的 provider | 平均延迟 | 相对 ORT CPU 最大绝对误差 | 相对 ORT CPU 平均绝对误差 |
|---|---|---:|---:|---:|
| CPU | CPUExecutionProvider | 74.50 ms | baseline | baseline |
| CUDA | CUDAExecutionProvider; CPUExecutionProvider | 10.91 ms | 3.58e-7 | 2.18e-8 |
| TensorRT FP32 | TensorrtExecutionProvider; CUDAExecutionProvider; CPUExecutionProvider | 8.26 ms | 5.29e-4 | 4.94e-5 |
| TensorRT FP16 | TensorrtExecutionProvider; CUDAExecutionProvider; CPUExecutionProvider | 7.45 ms | 1.47e-3 | 1.30e-4 |

这些误差是 TensorRT / CUDA 输出相对 ORT CPU output 的 float tensor 级误差。FP16 误差高于 FP32，符合预期；下一步需要把最差样本做 crop sheet，看暗区噪声、颜色和纹理是否出现可见问题。

## 注意事项

- 当前 ORT TensorRT EP 的延迟包含 Python session 调用和数据准备开销，不等同于 `trtexec` engine compute time。
- 固定 shape ONNX 不应给 `trtexec` 传 `--shapes`，否则会报 `Static model does not take explicit shapes`。
- `trtexec` 成功依赖 TensorRT `lib` 目录进入 PATH，否则会找不到 `nvinfer_plugin_10.dll`。

## AI-ISP / ISP 算法岗视角

这一周现在可以讲成：先用 ORT CPU 做 correctness baseline，再用 CUDA EP / TensorRT EP 和 `trtexec` 分别验证数值一致性与 engine 性能。FP16 的速度收益明确，但图像恢复任务还必须看误差图和失败样本，不能只报 engine latency。
