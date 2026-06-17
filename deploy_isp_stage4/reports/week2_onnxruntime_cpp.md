# Week 2 ONNX Runtime C++ 推理 Baseline

## 目标

Week 2 的目标是建立 C++ 推理 baseline，让后续 TensorRT / NCNN / MNN 后端有一个可解释的 correctness reference。C++ baseline 不追求极致性能，重点是输入输出协议严格一致。

## 当前实现

已新增：

- `CMakeLists.txt`
- `cpp/include/image_io.hpp`
- `cpp/include/onnxruntime_runner.hpp`
- `cpp/src/image_io.cpp`
- `cpp/src/onnxruntime_runner.cpp`
- `cpp/src/main.cpp`
- `scripts/04_week2_prepare_cpp_io.py`

这个 runner 采用最小依赖策略：

- 输入格式：RGB PPM P6。
- 输入 tensor：`NCHW / float32 / [0, 1]`。
- 输出 tensor：`NCHW / float32`，保存前 clamp 到 `[0, 1]`。
- 推理后端：ONNX Runtime C++ API。

使用 PPM 是为了避免 C++ 阶段引入 OpenCV / stb / libpng 依赖，让 Week 2 的核心问题保持在 tensor layout 和 ORT API 上。

已生成 C++ I/O fixtures：

- `outputs/week2_cpp_io/ppm_inputs/`
- `outputs/week2_cpp_io/ort_reference_png/`

这些样本用于后续验证 C++ runner 输出是否和 Python ORT reference 一致。

## 预期构建命令

需要先准备：

- C++17 编译器。
- CMake 3.20+。
- ONNX Runtime C/C++ release package，例如 `onnxruntime-win-x64-1.27.0`。

```powershell
cmake -S deploy_isp_stage4 -B deploy_isp_stage4/build -DONNXRUNTIME_ROOT=C:/path/to/onnxruntime-win-x64-1.27.0
cmake --build deploy_isp_stage4/build --config Release
```

运行：

```powershell
deploy_isp_stage4/build/Release/stage4_ort_runner.exe ^
  deploy_isp_stage4/models/onnx/dncnn_sidd_tiny_fp32.onnx ^
  deploy_isp_stage4/data/test_inputs/sample.ppm ^
  deploy_isp_stage4/outputs/week2_cpp/sample_cpp_output.ppm
```

## 当前编译与验证结果

VS Build Tools 2026、Ninja 和 ONNX Runtime CPU C++ SDK 补齐后，C++ runner 已经成功编译并完成 smoke test。

构建命令：

```powershell
cmd /c '"D:\application\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && cmake -S deploy_isp_stage4 -B deploy_isp_stage4\build_ninja_release -G Ninja -DCMAKE_BUILD_TYPE=Release -DONNXRUNTIME_ROOT=D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0 && cmake --build deploy_isp_stage4\build_ninja_release'
```

运行前需要把 ORT DLL 放到 exe 同目录，避免 Windows 优先加载 `C:\Windows\System32\onnxruntime.dll`：

```powershell
Copy-Item D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0\lib\onnxruntime.dll deploy_isp_stage4\build_ninja_release\
Copy-Item D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0\lib\onnxruntime_providers_shared.dll deploy_isp_stage4\build_ninja_release\
```

Smoke test：

```powershell
deploy_isp_stage4\build_ninja_release\stage4_ort_runner.exe ^
  deploy_isp_stage4\models\onnx\dncnn_sidd_tiny_fp32.onnx ^
  deploy_isp_stage4\outputs\week2_cpp_io\ppm_inputs\pair_00001.ppm ^
  deploy_isp_stage4\outputs\week2_cpp_io\cpp_outputs\pair_00001_cpp_output.ppm
```

结果：

| 项目 | 结果 |
|---|---:|
| C++ ORT single-image inference | 151.85 ms |
| C++ output vs Python ORT reference max abs error | 0.0 |
| C++ output vs Python ORT reference mean abs error | 0.0 |
| C++ output vs Python ORT reference PSNR | 80.0 dB |

说明：这里的对齐基于保存后的 8-bit PPM / PNG 图像比较，结果完全一致。后续如果要做 float tensor 级别对齐，可以让 C++ runner 额外 dump `.bin` tensor。

## AI-ISP / ISP 面试表达

这一周的可讲点不是“我会调 ONNX Runtime API”，而是：

- 我把 Python 训练阶段的 tensor 协议明确搬到 C++：`NCHW / RGB / float32 / [0, 1]`。
- 我避免在 C++ baseline 里引入复杂图像库，先把 correctness 问题收敛到 layout、range、dtype。
- 只有 C++ ORT baseline 和 PyTorch / ORT Python 对齐后，TensorRT / NCNN 的速度对比才有意义。
