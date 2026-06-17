# Reproducibility Checklist

## 已验证命令

```powershell
python stage4_deploy_isp/scripts/01_week0_pytorch_baseline.py --config configs/week0_baseline.yaml
$env:PYTHONIOENCODING='utf-8'; python stage4_deploy_isp/scripts/03_week1_export_validate_onnx.py --config configs/week1_onnx.yaml
python stage4_deploy_isp/scripts/04_week2_prepare_cpp_io.py
cmd /c '"D:\application\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && cmake -S stage4_deploy_isp -B stage4_deploy_isp\build_ninja_release -G Ninja -DCMAKE_BUILD_TYPE=Release -DONNXRUNTIME_ROOT=D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0 && cmake --build stage4_deploy_isp\build_ninja_release'
python stage4_deploy_isp/scripts/08_week2_compare_cpp_output.py
python stage4_deploy_isp/scripts/05_week3_backend_probe_benchmark.py
python stage4_deploy_isp/scripts/06_week4_quantization_eval.py
python stage4_deploy_isp/scripts/07_week6_pipeline_profile.py
```

## Python 依赖

已用到：

- torch
- numpy
- Pillow
- PyYAML
- matplotlib
- onnx
- onnxruntime
- onnxscript

## 当前环境记录

- GPU：NVIDIA GeForce RTX 4060 Ti，driver 可见。
- PyTorch：`2.12.0+cpu`，CUDA 不可见。
- ONNX Runtime providers：`AzureExecutionProvider; CPUExecutionProvider`。
- C++ compiler：MSVC 19.51.36248.
- CMake：4.3.1-msvc1.
- ONNX Runtime C++ SDK CPU：`D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0`.
- 缺少：CUDA Toolkit、TensorRT / trtexec、NCNN / MNN / adb。

## 需要补齐的系统工具

完整复现 Week 2 / 3 / 5 / 6 GPU-C++ 路径需要：

1. CUDA Toolkit。
2. TensorRT。
3. 可选：NCNN / MNN / Android adb。
