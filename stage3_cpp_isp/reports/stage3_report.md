# 阶段 3 总报告：C++ ISP 算法工程化

> 阅读提示：`stage3_tutorial_audit.md` 提供数据契约和
> 公式→reference→C++→测试→对齐→性能的证据矩阵。本报告用于建立学习地图和总结
> 阶段结论，不能替代每周教程。

## 0. 如何把这套报告当教材使用

阶段 3 不适合从性能表倒着背结论。推荐按四轮学习：

| 学习轮次 | 阅读材料 | 学习目标 | 过关检查 |
|---|---|---|---|
| 数据契约 | Week 0、Week 1、`stage3_tutorial_audit.md` | CPF32、HWC/planar、stride、border | 能手算带 padding 地址和 reflect-101 |
| 算法正确性 | Week 2、3、5、7 | 从公式写 Python reference，再对应 C++ loop | 能解释参数、边界与 range |
| 数值工程 | Week 4、6、`alignment_report.md` | LUT、rounding、阈值、优化后复验 | 能区分实现对齐误差与近似误差 |
| 集成与性能 | Week 8、`performance_report.md` | 中间张量排错、正确解释 benchmark | 能说清计时范围、复杂度和证据边界 |

每篇报告采用同一学习动作：

```text
1. 遮住结果，先预测输出或趋势。
2. 手算小例子。
3. 打开 Python/C++ 函数，逐项对应公式。
4. 运行测试与对齐命令。
5. 完成故障注入，找到第一个错误中间结果。
6. 不看答案复述质量、误差、速度和产品边界。
```

### 0.1 各报告职责

- 周报：解释一周内怎样从问题走到证据，是主教材；
- 算法专题：按 denoise、Tone Mapping、HDR 纵向串联知识；
- `alignment_report.md`：统一解释数值验收，不评价审美画质；
- `performance_report.md`：统一解释计时方法和性能证据；
- 本报告：提供学习入口、阶段结论和阶段 4 接口。

### 0.2 阶段最终自测

1. CPF32 为什么使用 HWC，而内部 `ImageBuffer` 可以是 planar？
2. `row_stride > width` 时怎样计算地址？
3. bilateral 的 `sigma_range` 为什么必须结合 input range？
4. Python-C++ LUT 对齐误差和 float-vs-LUT 近似误差有什么区别？
5. Local TM halo 在 base estimation 还是 reconstruction 中形成？
6. HDR merge 后为什么仍需 Tone Mapping？
7. benchmark 是否包含 allocation、I/O、thread creation，会怎样影响结论？
8. 最终图错误时，怎样用 first-divergence tensor 定位模块？

## 1. 项目目标

阶段 3 围绕以下内容构建 C++17 ISP 算法工程项目：

- RAW-like denoise；
- Global Tone Mapping；
- Tone curve LUT / fixed-point approximation；
- Local Tone Mapping；
- aligned HDR toy merge；
- Python-C++ alignment、tests、benchmark、reports 和 interview expression。

项目定位是三年经验 ISP 算法工程师学习作品，不是图像测试项目，也不是纯 IQ tuning。
重点是算法实现、验证、性能分析和工程 tradeoff。

## 2. 已实现 Pipeline

可复用 API 与命令行工具：

```text
include/cpp_isp/pipeline.hpp
src/pipeline.cpp
tools/run_pipeline.cpp
```

单输入路径：

```text
linear / RAW-like input
-> optional denoise: none / box / gaussian
-> tone: global / local / LUT
-> optional gamma
-> CPF32 output
```

HDR 路径：

```text
short exposure + long exposure
-> aligned HDR merge
-> optional denoise
-> tone: global / local / LUT
-> optional gamma
-> CPF32 output
```

示例：

```powershell
.\stage3_cpp_isp\build\run_pipeline.exe single `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\week8_global.cpf32 `
  gaussian global reinhard 0.22 2.2
```

## 3. 模块总览

| 模块 | 主要文件 | 学习重点 |
|---|---|---|
| Image / Border / CPF32 | `image.hpp`、`border.hpp`、`cpf32.hpp` | layout、stride、border、跨语言 tensor |
| Denoise | `denoise.hpp`、`denoise_basic.cpp`、`bilateral_denoise.cpp` | Gaussian、bilateral、LUT、noise-detail tradeoff |
| Global TM | `tone_mapping.hpp`、`tone_mapping.cpp` | Reinhard、Filmic、S-curve、percentile exposure |
| Tone LUT / Fixed | `tone_lut.hpp`、`fixed_point.hpp` | 10/12/14-bit LUT、quantization、banding |
| Local TM | `local_tone_mapping.hpp` | base/detail、halo、box 与 bilateral |
| HDR toy | `hdr_merge.hpp` | aligned short/long merge 与 HDR-to-SDR |
| Pipeline | `pipeline.hpp`、`run_pipeline.cpp` | 模块连接、数据契约和中间结果排错 |

## 4. 正确性与测试

项目使用：

- CTest unit test；
- CPF32 Python-C++ alignment；
- `test_pipeline_golden` 分阶段端到端 golden fixture；
- synthetic edge、gradient、highlight、HDR-like scene；
- visual comparison 与 metrics CSV。

最近一次 clean verification：

```text
2026-06-23 Release verification
100% tests passed
0 tests failed out of 12
```

该结果来自独立临时 build directory，不依赖仓库中旧 CMake cache。现有
`stage3_cpp_isp/build` 曾在目录重命名前生成，重新使用时应先 configure，不能把旧
binary 的存在当作当前源码已经验证。

## 5. 关键对齐结果

| Week | 模块 | 最大绝对误差 | Failed |
|---|---|---:|---:|
| Week 5 | Global TM Reinhard RGB | 5.96e-8 | 0 / 184320 |
| Week 5 | Global TM Filmic luma | 1.79e-7 | 0 / 184320 |
| Week 6 | Tone LUT Filmic 12→12 | 8.94e-8 | 0 / 184320 |
| Week 7 | Local TM Reinhard bilateral | 1.79e-7 | 0 / 73728 |
| Week 7 | HDR aligned short/long merge | 4.77e-7 | 0 / 73728 |

这些数字证明 C++ implementation 与 Python reference 对齐，不证明审美画质更好。

## 6. Pipeline 演示

Week 8 生成四类输出：

- gaussian denoise + global Reinhard TM；
- gaussian denoise + Reinhard LUT TM；
- gaussian denoise + local Reinhard TM；
- HDR merge + local Reinhard TM。

![Week8 pipeline comparison](figures/week8/week8_pipeline_comparison.png)

160×96 synthetic scene 的旧实验：

| Case | Mean luma | P95 luma | Clip fraction | Pipeline |
|---|---:|---:|---:|---:|
| global | 0.4006 | 0.6240 | 0.0000 | 43.24 ms |
| LUT | 0.4006 | 0.6241 | 0.0000 | 25.36 ms |
| local | 0.4006 | 0.6241 | 0.0000 | 103.72 ms |
| HDR local | 0.3982 | 0.6191 | 0.0000 | 126.64 ms |

这些 Python-side pipeline timing 是 legacy illustrative measurement，与当前 C++
`bench_pipeline` 不是同一实验。

## 7. 性能总结

2026-06-23 正式 Tone Mapping 结果：

- 4K S-curve float luma：约 `1334.930 ms`；
- 4K S-curve LUT luma：约 `203.076 ms`；
- 主要原因：LUT 移除每像素 `exp`。

2026-06-23 正式 Local TM 结果：

- box r5 1080P：约 `1474.546 ms`；
- direct bilateral r1 1080P：约 `1791.271 ms`；
- direct bilateral r5 640×360：约 `2457.221 ms`。

结论：Global TM 和 LUT TM 是可用 CPU baseline；naive Local TM 适合学习正确性，
但未达到 deployable speed。

完整正式数据位于 `reports/figures/benchmark_20260623/`。没有 hardware counter，
因此 bottleneck 结论仍只能基于 complexity 与 size scaling 推断。

## 8. 已知限制

- 没有完整 Bayer RAW pipeline；
- HDR merge 假设完美对齐且无运动；
- Local TM 没有 guided filter、bilateral grid、pyramid、SIMD 或 multithreading；
- Tone LUT 使用 nearest index，无 interpolation/dithering；
- `configs/default.yaml` 只记录 reference settings，C++ 仍使用 CLI；
- 没有 AVX/NEON、ARM measurement、cache-counter evidence 或 realtime claim；
- CUDA/TensorRT/NCNN deployment 属于阶段 4。

## 9. 简历表述

- 构建 C++17 ISP 算法工程项目，覆盖 RAW-like denoise、Global/Local Tone Mapping、
  LUT/fixed-point 和 aligned HDR toy merge；
- 使用 CPF32 建立 Python reference 与 C++ output 对齐闭环；
- 实现 Reinhard、Filmic、S-curve 与 10/12/14-bit LUT approximation；
- 分析 banding、halo、noise-detail、1080P/4K performance；
- 构建 `pipeline.hpp` 和 `run_pipeline`，支持中间结果 dump 与 first-divergence
  debugging。

## 10. 阶段 4 接口

阶段 4 可复用：

- CPF32 correctness fixture；
- C++ `ImageBuffer` 与 module API；
- 1080P/4K CPU baseline；
- Week 8 pipeline intermediate output；
- alignment threshold 与 error report。

合适的后续方向：

- CUDA tone LUT 与 separable filter；
- guided filter / bilateral grid Local TM；
- ONNX / TensorRT / NCNN learned denoise；
- deployed output 与阶段 3 deterministic baseline 对齐。
