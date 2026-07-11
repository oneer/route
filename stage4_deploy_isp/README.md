# 阶段四：端侧 AI-ISP 部署与 CUDA 推理

这是阶段四唯一入口。项目从固定的阶段二 DnCNN checkpoint 出发，依次完成 PyTorch baseline、ONNX、ONNX Runtime Python/C++、TensorRT FP32/FP16、ORT CPU QDQ INT8、CUDA 前处理与端到端 profiling。

## 先看结论

| 环节 | 当前状态 | 证据 |
|---|---|---|
| 固定 baseline | 已复验 | 20 张固定 RGB paired 输入、checkpoint/model card、PSNR/SSIM/CPU latency |
| ONNX + ORT Python | 已复验 | checker 通过；max error `4.17e-7`；20 张 error map |
| ORT C++ | 已复验 | 20/20 raw float tensor 对齐；max error `0` |
| TensorRT FP32/FP16 | 已复验 | RTX 4060 Ti、TensorRT 10.8；engine/log/画质/失败样本 |
| ORT QDQ INT8 | 已复验 | 10 张校准、10 张独立评价；无 split overlap |
| CUDA normalize | 已复验但未接入推理 | NVRTC kernel、H2D/kernel/D2H 拆时和 CPU 对齐 |
| Android/ARM 移动端 | 未完成 | 无设备、`adb`、NCNN/MNN 工具链；仅保留设计章节 |
| 阶段三 C++ ISP 串联 | 已复验 | 固定 20 张 manifest；Stage 3 global Reinhard → Stage 4 C++ ORT；C++/Python max error `0` |

“已复验”只代表表中明确的环境和口径。TensorRT engine 不承诺跨 GPU、CUDA 或 TensorRT 版本通用。

## 固定部署协议

| 边界 | 协议 |
|---|---|
| 图像输入 | RGB uint8、HWC、512×512 |
| 模型输入 | `input`，`[1,3,512,512]`，NCHW，float32，RGB，`[0,1]` |
| 预处理 | `float32(uint8) / 255`，HWC → NCHW；无均值方差归一化 |
| 模型输出 | `output`，NCHW float；DnCNN residual：`input - predicted_noise` |
| 后处理 | float tensor 先用于对齐；仅可视化时 clamp `[0,1]`、NCHW → HWC、round 到 uint8 |
| 固定测试集 | `data/test_inputs/week0_fixed_manifest.csv`，20 张 |
| INT8 校准集 | `data/calibration/week4_calibration_manifest.csv`，前 10 张 |
| INT8 评价集 | `data/test_inputs/week4_evaluation_manifest.csv`，后 10 张，与校准集无交集 |

机器可读 contract 位于 `configs/deployment_contract.yaml`，hash/model card 位于 `outputs/audit/model_card.json`。ONNX 使用外部权重，复制模型时必须同时携带：

```text
models/onnx/dncnn_sidd_tiny_fp32.onnx
models/onnx/dncnn_sidd_tiny_fp32.onnx.data
```

## 数据流

```text
PNG RGB uint8/HWC/host
  → /255 + HWC→NCHW
  → float32 [1,3,512,512]/host
  → PyTorch or ORT CPU
      或 H2D → CUDA/TensorRT → D2H
  → float output（先做 raw tensor correctness）
  → clamp → NCHW→HWC → round uint8
  → PNG/PPM（只用于观察与交付）
```

不要用最终 PNG 替代 tensor 对齐；uint8 round 会掩盖小于约 `1/255` 的误差。

## 推荐学习顺序

1. [Week 0：固定 baseline](reports/week0_deploy_baseline.md)
2. [Week 1：ONNX 导出与 ORT Python](reports/week1_onnx_alignment.md)
3. [Week 2：ORT C++ raw tensor 对齐](reports/week2_onnxruntime_cpp.md)
4. [Week 3：TensorRT FP32/FP16](reports/week3_tensorrt_fp16.md)
5. [Week 4：INT8 QDQ 与独立校准集](reports/week4_int8_quantization.md)
6. [Week 5：移动端设计边界](reports/week5_mobile_inference.md)
7. [Week 6：CUDA 与 pipeline profile](reports/week6_pipeline_profile.md)
8. [总报告](reports/stage4_report.md)
9. [复现清单](reports/reproducibility_checklist.md)
10. [调试练习与 capstone](reports/debugging_exercises_and_capstone.md)

统一结果：

- `outputs/audit/correctness_matrix.csv`
- `outputs/audit/latency_matrix.csv`
- `outputs/audit/asset_traceability.csv`

## 最小复现

先运行不需要数据集、checkpoint 或 GPU 的合同回归：

```powershell
python -m unittest discover -s stage4_deploy_isp/tests -v
```

该测试检查 tensor contract、模型卡、跟踪模型 hash、manifest 数量、路径可移植性和 INT8 校准/评价 split 隔离。

### Stage 3 C++ → Stage 4 C++ ORT 串联

先在已加载 MSVC 环境且可找到 Ninja 的终端构建 Stage 4 runner：

```powershell
$env:ONNXRUNTIME_ROOT='D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0'
cmake --preset ort-verify
cmake --build --preset ort-verify
```

然后对固定 manifest 执行桥接：

```powershell
python stage4_deploy_isp/scripts/12_stage3_stage4_bridge.py
```

构建会把匹配版本的 `onnxruntime.dll` 复制到 runner 旁，避免 Windows 系统目录中的其他 ORT 版本被优先加载。真实数据流是 `PNG → CPF32 → Stage 3 C++ global Reinhard node → 8-bit PPM → Stage 4 C++ ORT → f32`。中间文件写入已忽略的 `out/`，汇总写入 `reports/stage3_stage4_bridge_summary.csv`。Python ORT 参考读取同一个量化后 PPM tensor，因此 C++/Python 对齐不会把 PPM 量化误差混进后端误差。固定 20 张实测的 C++/Python max error 均为 `0`；该桥接证明两个 C++ 阶段可串联，但 Stage 3 tone node 与原 DnCNN 训练域存在 domain shift，不等于真实 RAW AI-ISP 已完成。

从仓库根目录执行：

```powershell
python stage4_deploy_isp/scripts/01_week0_pytorch_baseline.py --config configs/week0_baseline.yaml
$env:PYTHONIOENCODING='utf-8'
python stage4_deploy_isp/scripts/03_week1_export_validate_onnx.py --config configs/week1_onnx.yaml
python stage4_deploy_isp/scripts/04_week2_prepare_cpp_io.py
python stage4_deploy_isp/scripts/06_week4_quantization_eval.py
python stage4_deploy_isp/scripts/07_week6_pipeline_profile.py
python stage4_deploy_isp/scripts/11_generate_audit_matrices.py
```

C++、GPU 和 CUDA 的完整命令见复现清单。不同脚本的 latency 不能直接混成一列排名：

- PyTorch/ORT session：host 侧 API 调用；
- `trtexec` compute：engine GPU compute；
- `trtexec` latency：包含其 H2D/compute/D2H 调度口径；
- C++：当前 runner 的 warm steady-state inference；
- pipeline：pre/infer/post/save 拆分。

## 当前核心结果

| Backend | Precision | Correctness / quality | Latency 口径 |
|---|---|---|---|
| ORT Python CPU | FP32 | vs PyTorch max `4.17e-7` | session mean `70.38 ms` |
| ORT C++ CPU | FP32 | 20 张 raw tensor max `0` | 单进程逐图 warm run，约 `143–151 ms` |
| ORT CUDA EP | FP32 | vs ORT CPU max `3.58e-7` | session mean `10.70 ms` |
| ORT TensorRT EP | FP32 | quality PSNR `32.9825 dB` | session mean `7.89 ms` |
| ORT TensorRT EP | FP16 | quality PSNR `32.9820 dB` | session mean `7.46 ms` |
| ORT CPU QDQ | INT8 | 独立评价集平均 drop `0.0833 dB` | session p50 `121.25 ms` |

`trtexec` 本次 FP32/FP16 compute mean 分别为 `1.968/0.979 ms`；这不是上述 ORT session latency。

## 排错顺序

输出异常时按以下顺序，不要先怪后端：

1. manifest 是否相同；
2. RGB/BGR；
3. NCHW/NHWC；
4. `[0,255]`/`[0,1]`；
5. dtype；
6. input/output name 与 shape；
7. clamp/round 是否过早；
8. provider 是否真的启用，是否 fallback；
9. FP16 overflow、dynamic profile；
10. INT8 calibration 分布和 split；
11. GPU 测时是否同步；
12. 是否把 I/O、engine build、session creation 混进 steady-state。

## 官方资料

部署生态变化快。以下链接于 **2026-06-23** 核对；实验版本以复现清单为准。

- [PyTorch ONNX exporter](https://docs.pytorch.org/docs/stable/onnx.html)
- [ONNX checker API](https://onnx.ai/onnx/api/checker.html)
- [ONNX Runtime C/C++ API](https://onnxruntime.ai/docs/api/c/)
- [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
- [TensorRT command-line programs / trtexec](https://docs.nvidia.com/deeplearning/tensorrt/latest/reference/command-line-programs.html)
- [TensorRT developer guide](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/)
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/)
- [Nsight Compute](https://docs.nvidia.com/nsight-compute/NsightCompute/)
- [NCNN](https://github.com/Tencent/ncnn)
- [MNN](https://github.com/alibaba/MNN)

Polygraphy、GraphSurgeon、TensorRT Model Optimizer 和 Nsight 在本仓库中尚未形成实测产物，因此只列为后续工具，不写入“已完成成果”。
