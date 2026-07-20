# Lab 04：降噪、NLM 与质量—性能取舍

对应章节：8–9。

## 目标

同时评价噪声残留、纹理损失、边缘、计算量和访存，避免把“更平滑”当作“更好”。

## 软件基线

使用 [`stage1_soft_isp/soft_isp/denoise.py`](../../stage1_soft_isp/soft_isp/denoise.py) 和 [`openisp/nlm.py`](../../stage1_soft_isp/openisp/nlm.py)。先运行 Stage 1 测试确认环境：

```powershell
Set-Location D:\document\route\stage1_soft_isp
python -m unittest discover -s tests -v
python scripts/22_run_tuning_sweep.py
```

## C++ 性能基线

前置检查：`cmake --version`。当前工具不可用时先按 Stage 3 README 配置，不跳过并伪造性能结果。

```powershell
Set-Location D:\document\route\stage3_cpp_isp
cmake --preset verify
cmake --build --preset verify
ctest --preset verify
.\build\bench_denoise.exe --full
```

如果本机 preset 或生成器不同，按 [`stage3_cpp_isp/README.md`](../../stage3_cpp_isp/README.md) 的本机工具链命令执行，并记录差异。

## 参数矩阵

| 方法 | 参数 | 质量指标 | 纹理 crop | p50/p90 时间 | 内存/窗口估计 |
|---|---|---:|---|---:|---:|
| Gaussian/Bilateral | sigma 等 |  |  |  |  |
| NLM | patch/search/h |  |  |  |  |
| 硬件近似 NLM | LUT/截断/早停 |  |  |  |  |

## 验收

- 至少包含平坦区、纹理区、边缘区和低照区。
- 同时记录 PSNR/SSIM 或 MAE，以及固定 crop 主观判断。
- 能解释 NLM 的 patch、search window、`h` 分别控制什么。
- 能估算计算量和缓存需求，并说明为什么标准 NLM 很难直接做实时硬件。
