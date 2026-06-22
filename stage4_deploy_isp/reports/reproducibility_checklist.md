# 复现实验检查清单

## 已验证命令

```powershell
python stage4_deploy_isp/scripts/01_week0_pytorch_baseline.py --config configs/week0_baseline.yaml
$env:PYTHONIOENCODING='utf-8'; python stage4_deploy_isp/scripts/03_week1_export_validate_onnx.py --config configs/week1_onnx.yaml
python stage4_deploy_isp/scripts/04_week2_prepare_cpp_io.py
cmd /c '"D:\application\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && cmake -S stage4_deploy_isp -B stage4_deploy_isp\build_ninja_release -G Ninja -DCMAKE_BUILD_TYPE=Release -DONNXRUNTIME_ROOT=D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0 && cmake --build stage4_deploy_isp\build_ninja_release'
python stage4_deploy_isp/scripts/08_week2_compare_cpp_output.py
C:\Users\10439\.conda\envs\stage4-cuda\python.exe stage4_deploy_isp/scripts/09_week3_trt_cuda_benchmark.py --runs 5
python stage4_deploy_isp/scripts/06_week4_quantization_eval.py
python stage4_deploy_isp/scripts/07_week6_pipeline_profile.py
C:\Users\10439\.conda\envs\stage4-cuda\python.exe stage4_deploy_isp/scripts/10_week6_cuda_preprocess_benchmark.py --runs 200
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
- onnxruntime-gpu
- onnxscript

## 当前环境记录

- GPU：NVIDIA GeForce RTX 4060 Ti，driver 591.74。
- PyTorch：`2.12.0+cpu`，训练/导出仍使用 CPU build。
- Stage 4 CUDA Python：`C:\Users\10439\.conda\envs\stage4-cuda\python.exe`。
- ONNX Runtime GPU：`1.21.1`。
- ONNX Runtime providers：`TensorrtExecutionProvider; CUDAExecutionProvider; CPUExecutionProvider`。
- C++ compiler：MSVC 19.51.36248。
- CMake：4.3.1-msvc1。
- ONNX Runtime C++ SDK CPU：`D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0`。
- CUDA Toolkit：12.6.20。
- TensorRT：10.8.0。
- cuDNN：9.23。

## 当前仍需注意

- TensorRT / cuDNN DLL 目录需要进入 PATH，尤其是 TensorRT `lib` 目录。
- CMake + `nvcc` 编译 CUDA executable 的路线已补入口，但 CUDA 12.6 与 VS Build Tools 2026 host compiler 仍存在兼容问题；当前通过 NVRTC 完成 Week 6 CUDA kernel 编译实测。
- 移动端工具链仍缺：NCNN / MNN / Android adb。
