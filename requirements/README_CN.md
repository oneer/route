# 依赖约束与环境复现

## CPU 开发与 CI 环境

`constraints-cpu.txt` 固定四阶段直接依赖的已验证版本。各阶段仍保留自己的 requirements，安装时统一施加约束：

```powershell
python -m pip install -c requirements/constraints-cpu.txt `
  -r stage1_soft_isp/requirements.txt `
  -r stage2_ai_isp/requirements.txt `
  -r stage2_ai_isp/deployment/requirements.txt `
  -r stage4_deploy_isp/requirements.txt
python tools/check_environment.py --constraints requirements/constraints-cpu.txt
python -m pip check
```

CI 使用 Python 3.12。当前本机 CPU 环境为 Python 3.14.4，因此 hosted CI 首跑仍是 Python 3.12 兼容性的最终验收。

## Windows ORT GPU runtime 环境

该环境只负责 ORT CUDA/TensorRT backend 推理，不包含 PyTorch 训练或 ONNX 导出：

```powershell
conda create -n stage4-cuda python=3.11 pip -y
conda activate stage4-cuda
python -m pip install -r requirements/ort-gpu-win-py311.txt
python tools/check_environment.py --constraints requirements/constraints-ort-gpu-win-py311.txt
python -m pip check
```

TensorRT Python wheel不是当前 profile 的依赖；TensorRT EP 通过已安装的原生 TensorRT/CUDA 运行库加载。provider 是否真正启用仍需运行时检查，不能只看包版本。

## 边界

这些文件锁定直接依赖，不锁定操作系统驱动、CUDA Toolkit、cuDNN、TensorRT 和编译器。对应原生组件版本继续记录在 `environment_paths.md`。完整 hash lock 需要在目标 Python/平台上通过专用锁文件工具生成，不能用另一平台的 `pip freeze` 代替。
