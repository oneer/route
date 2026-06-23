# 阶段四复现实验检查清单

## 资产

- [ ] checkpoint、source config 存在，SHA-256 与 `outputs/audit/model_card.json` 一致。
- [ ] 20 张 fixed manifest 路径可读。
- [ ] ONNX 与 `.onnx.data` 同目录。
- [ ] Week 4 calibration/evaluation manifest 交集为 0。
- [ ] TensorRT plan 只在记录环境使用；环境变化时从 ONNX 重建。

## Python 环境

历史/本次实测：

- PyTorch `2.12.0+cpu`
- ONNX Runtime CPU/C++ SDK `1.26.0`
- GPU 环境 ORT `1.21.1`
- CUDA `12.6.20`
- TensorRT `10.8.0`
- cuDNN `9.23`
- GPU RTX 4060 Ti，driver `591.74`
- MSVC `19.51.36248`，CMake `4.3.1-msvc1`

运行前记录实际 `python/torch/onnx/onnxruntime/providers/nvidia-smi/trtexec` 版本，不能只照抄历史值。

## Python smoke

```powershell
python stage4_deploy_isp/scripts/01_week0_pytorch_baseline.py --config configs/week0_baseline.yaml
$env:PYTHONIOENCODING='utf-8'
python stage4_deploy_isp/scripts/03_week1_export_validate_onnx.py --config configs/week1_onnx.yaml
python stage4_deploy_isp/scripts/04_week2_prepare_cpp_io.py
python stage4_deploy_isp/scripts/06_week4_quantization_eval.py
python stage4_deploy_isp/scripts/07_week6_pipeline_profile.py
python stage4_deploy_isp/scripts/11_generate_audit_matrices.py
```

预期：ONNX max error `<1e-4`；INT8 split overlap `0`；audit 三张 CSV 生成。

## C++ 构建与 raw tensor smoke

```powershell
cmake -S stage4_deploy_isp -B stage4_deploy_isp/build_audit_release -G Ninja `
  -DCMAKE_BUILD_TYPE=Release `
  -DONNXRUNTIME_ROOT=D:/Env/onnxruntime/cpu/onnxruntime-win-x64-1.26.0
cmake --build stage4_deploy_isp/build_audit_release
```

将 ORT DLL 放到 exe 同目录。对每张 PPM 执行：

```powershell
stage4_ort_runner.exe model.onnx input.ppm output.ppm output.f32 3 5
python stage4_deploy_isp/scripts/08_week2_compare_cpp_output.py
```

预期：20 张 raw tensor，max error `<=1e-5`。

## GPU/TensorRT

```powershell
C:\Users\10439\.conda\envs\stage4-cuda\python.exe `
  stage4_deploy_isp/scripts/09_week3_trt_cuda_benchmark.py --runs 5
```

预期：两个 `trtexec` return code 0；FP16 failure maps 生成；日志记录 TensorRT 版本和实测口径。PATH 需包含 TensorRT `bin/lib`、CUDA、cuDNN。

## CUDA preprocess

```powershell
C:\Users\10439\.conda\envs\stage4-cuda\python.exe `
  stage4_deploy_isp/scripts/10_week6_cuda_preprocess_benchmark.py --runs 200
```

预期：max error `<1e-6`；CSV 同时包含 pageable H2D、kernel、D2H、GPU stage E2E。不要只引用 kernel 数字。

## 结果核查

- [ ] correctness matrix 不混用 reference。
- [ ] latency matrix 标明设备、shape、precision、warmup/runs、同步与 I/O。
- [ ] FP16/INT8 有 PSNR/SSIM 与最差 error map/crop。
- [ ] C++ 比较 raw float，而不是只比 PNG。
- [ ] 无 Android 设备时状态保持“未完成”。
- [ ] 未实际运行 Polygraphy/Nsight 等工具时，不写入完成成果。
