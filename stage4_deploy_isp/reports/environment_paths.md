# Environment Paths

This file records local toolchain, dataset, model, and output paths for the
Stage 4 AI-ISP deployment project. Update it whenever a tool is installed or
moved.

## Workspace

| Item | Path |
|---|---|
| Repository root | `C:\Users\10439\Desktop\route` |
| Stage 4 project | `C:\Users\10439\Desktop\route\stage4_deploy_isp` |
| Stage 2 project | `C:\Users\10439\Desktop\route\stage2_ai_isp` |
| Stage 3 project | `C:\Users\10439\Desktop\route\stage3_cpp_isp` |

## Local Directory Policy

| Category | Path |
|---|---|
| Downloads / installers / archives | `D:\download` |
| Environments / SDKs | `D:\Env` |
| Applications / installed tools | `D:\application` |

## Data

| Item | Path |
|---|---|
| SIDD tiny validation noisy | `C:\Users\10439\Desktop\route\stage2_ai_isp\datasets\sidd_tiny\val\noisy` |
| SIDD tiny validation clean | `C:\Users\10439\Desktop\route\stage2_ai_isp\datasets\sidd_tiny\val\clean` |
| SIDD low-light tiny validation | `C:\Users\10439\Desktop\route\stage2_ai_isp\datasets\sidd_low_light_tiny\val` |
| Original SIDD Small download | `C:\Users\10439\Desktop\route\stage2_ai_isp\datasets\downloads\SIDD_Small_sRGB_Only` |
| Stage 4 fixed manifest | `C:\Users\10439\Desktop\route\stage4_deploy_isp\data\test_inputs\week0_fixed_manifest.csv` |

## Models

| Item | Path |
|---|---|
| Stage 2 DnCNN checkpoint | `C:\Users\10439\Desktop\route\stage2_ai_isp\runs\paired_rgb_sidd_tiny_dncnn_l2_300\checkpoints\best_psnr.pth` |
| Stage 2 NAFNet-lite checkpoint | `C:\Users\10439\Desktop\route\stage2_ai_isp\runs\paired_rgb_sidd_tiny_nafnet_lite_l1_300\checkpoints\best_psnr.pth` |
| Stage 4 FP32 ONNX | `C:\Users\10439\Desktop\route\stage4_deploy_isp\models\onnx\dncnn_sidd_tiny_fp32.onnx` |
| Stage 4 INT8 ONNX | `C:\Users\10439\Desktop\route\stage4_deploy_isp\models\onnx\dncnn_sidd_tiny_int8_qdq.onnx` |

## Python

| Item | Path / Version |
|---|---|
| Miniconda root | `D:\Env\miniconda3` |
| Python executable | `C:\Python314\python.exe` |
| PyTorch | `2.12.0+cpu` |
| ONNX | `1.22.0` |
| ONNX Runtime | `1.27.0` |

## Conda Environments

| Item | Path / Version |
|---|---|
| Base conda | `D:\Env\miniconda3` |
| Recommended Stage 4 CUDA env | `TODO: create e.g. stage4-cuda` |
| Recommended command | `TODO: conda create -n stage4-cuda python=3.11` |

## C++ Toolchain

Fill these after Visual Studio Build Tools installation.

| Item | Path / Version |
|---|---|
| Visual Studio Build Tools root | `D:\application\Microsoft Visual Studio\18\BuildTools` |
| Visual Studio package cache | `D:\application\Microsoft\VisualStudio\Packages` |
| Legacy Visual Studio 14.0 root | `D:\application\Microsoft Visual Studio 14.0` |
| x64 Native Tools setup | `D:\application\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat` |
| `cl.exe` | `D:\application\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\cl.exe` |
| MSVC version | `19.51.36248 for x64` |
| `cmake.exe` | `D:\application\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe` |
| CMake version | `4.3.1-msvc1` |
| MSBuild | `D:\application\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe` |

Note: prefer `D:\application\Microsoft Visual Studio\18\BuildTools` for Stage 4.
`D:\application\Microsoft Visual Studio 14.0` is likely an older VS 2015-era
toolchain and should not be used unless a specific legacy dependency requires it.

## ONNX Runtime C++ SDK

| Item | Path |
|---|---|
| ONNX Runtime CPU zip | `TODO: expected D:\download\onnxruntime-win-x64-1.26.0.zip` |
| ONNX Runtime ARM64 zip | `D:\download\onnxruntime-win-arm64-1.26.0.zip` |
| ONNX Runtime GPU CUDA13 zip | `D:\download\onnxruntime-win-x64-gpu_cuda13-1.26.0.zip` |
| ONNX Runtime CPU SDK root | `D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0` |
| ONNX Runtime GPU CUDA13 SDK root | `D:\Env\onnxruntime\gpu_cuda13\onnxruntime-win-x64-gpu-1.26.0` |
| CPU include directory | `D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0\include` |
| CPU library directory | `D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0\lib` |
| CPU runtime DLL | `D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0\lib\onnxruntime.dll` |
| GPU include directory | `D:\Env\onnxruntime\gpu_cuda13\onnxruntime-win-x64-gpu-1.26.0\include` |
| GPU library directory | `D:\Env\onnxruntime\gpu_cuda13\onnxruntime-win-x64-gpu-1.26.0\lib` |
| GPU runtime DLL | `D:\Env\onnxruntime\gpu_cuda13\onnxruntime-win-x64-gpu-1.26.0\lib\onnxruntime.dll` |

## CUDA / cuDNN / TensorRT

| Item | Path / Version |
|---|---|
| GPU | `NVIDIA GeForce RTX 4060 Ti` (8 GB, driver 591.74) |
| `nvidia-smi.exe` | `C:\Windows\System32\nvidia-smi.exe` |
| CUDA Toolkit root | `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6` |
| `nvcc.exe` | `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin\nvcc.exe` |
| CUDA version | **12.6.20** |
| cuDNN root | `C:\Program Files\NVIDIA\CUDNN\v9.23` |
| cuDNN bin (CUDA 12.x) | `C:\Program Files\NVIDIA\CUDNN\v9.23\bin\12.9\x64` |
| cuDNN include (CUDA 12.x) | `C:\Program Files\NVIDIA\CUDNN\v9.23\include\12.9` |
| cuDNN lib (CUDA 12.x) | `C:\Program Files\NVIDIA\CUDNN\v9.23\lib\12.9\x64` |
| TensorRT root | `TODO` |
| `trtexec.exe` | `TODO` |

### CMake integration

Standard CUDA Toolkit layout (`include/` + `lib/` + `bin/` in one tree) — CMake finds it automatically:

```powershell
cmake -S ... -B ... -G Ninja -DCMAKE_CUDA_COMPILER="C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin/nvcc.exe"
```

## Mobile / Edge Toolchains

Optional for Week 5 mobile deployment.

| Item | Path / Version |
|---|---|
| NCNN root | `TODO` |
| `onnx2ncnn.exe` | `TODO: where onnx2ncnn` |
| `ncnnoptimize.exe` | `TODO: where ncnnoptimize` |
| MNN root | `TODO` |
| `MNNConvert.exe` | `TODO: where MNNConvert` |
| Android platform-tools | `TODO` |
| `adb.exe` | `TODO: where adb` |
