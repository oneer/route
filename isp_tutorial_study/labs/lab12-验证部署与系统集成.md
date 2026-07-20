# Lab 12：验证、部署与系统集成

对应章节：32–34。

## 目标

运行软件、C++、模型部署和系统级回归，建立 golden、误差阈值、性能预算和失败恢复的统一证据。

## 分层回归

先检查 Python、CMake/CTest 和各阶段依赖。某一后端不可用时保留 `not_run` 并记录原因，不得降低断言或误差阈值来制造通过。

```powershell
Set-Location D:\document\route
python -m unittest discover -s stage1_soft_isp/tests -v
$env:PYTHONPATH='stage2_ai_isp'
python -m unittest discover -s stage2_ai_isp/tests -v
Set-Location D:\document\route\stage3_cpp_isp
cmake --preset verify
cmake --build --preset verify
ctest --preset verify
Set-Location D:\document\route
python -m unittest discover -s stage4_deploy_isp/tests -v
python -m unittest discover -s camera_system_capstone/tests -v
```

## 部署对齐

```powershell
Set-Location D:\document\route\stage4_deploy_isp
python scripts/03_week1_export_validate_onnx.py
Set-Location D:\document\route
python stage4_deploy_isp/scripts/13_profile_device_pipeline.py
python stage4_deploy_isp/scripts/14_generate_quality_latency_memory_matrix.py
```

如果脚本依赖模型或环境变量，按 [`stage4_deploy_isp/README.md`](../../stage4_deploy_isp/README.md) 配置；不得通过删除阈值或跳过测试来“通过”。

## 验证矩阵

| 层级 | Golden | 输入集合 | 容差/不变量 | 质量 | 性能 | 失败恢复 |
|---|---|---|---|---|---|---|
| 单模块 |  |  |  |  |  |  |
| Pipeline |  |  |  |  |  |  |
| 部署后端 |  |  |  |  |  |  |
| 相机系统 |  |  |  |  |  |  |

## 验收

- Golden 文件、生成代码、配置和版本可追溯。
- 数值容差说明绝对/相对误差、dtype 和饱和边界。
- 性能报告包含 warm-up、重复次数、p50/p90/p99 和环境。
- 系统验证覆盖 buffer/metadata 对齐、超时、丢帧和恢复。
- AI 模块额外覆盖数据分布、极端输入和 failure gallery。
