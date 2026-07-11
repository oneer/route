# 环境与兼容矩阵

## 公共基线

| 范围 | 要求 | 说明 |
|---|---|---|
| Python | `>=3.11,<3.15` | 根级元数据边界；CI 使用 3.12 |
| Stage 1 | `stage1_soft_isp/requirements.txt` | 传统 ISP 与单元测试 |
| Stage 2 | `stage2_ai_isp/requirements.txt` | PyTorch CPU/GPU 训练；当前仍需生成 lock |
| Stage 3 | CMake >= 3.20、C++17、Ninja | 使用 `CMakePresets.json` 的 `verify` preset |
| Stage 4 CPU | PyTorch、ONNX、ONNX Runtime | 合同测试只要求 PyYAML，不要求 GPU |
| Stage 4 GPU | Python 3.11、ORT GPU 1.21.1、CUDA/cuDNN/TensorRT | `requirements/constraints-ort-gpu-win-py311.txt` 是 runtime profile，不包含 PyTorch |

## 当前观测环境

当前机器的详细绝对路径和实测版本记录在 `environment_paths.md`。该文件是本机观测记录，不是可移植安装说明。公共脚本必须使用相对路径、环境变量、命令行参数或 CMake preset。

## 待完成

1. CPU 与 ORT GPU 直接依赖约束已经生成并通过本机版本检查。
2. 为原生 CUDA、cuDNN、TensorRT 和驱动生成更严格的机器可读兼容清单。
3. 在 GitHub hosted Python 3.12 和第二台 GPU 机器复验安装与测试。
4. 如需完全可重复的 transitive/hash lock，应在目标平台使用专用锁文件工具生成。
