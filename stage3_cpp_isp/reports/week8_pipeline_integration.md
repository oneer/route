# 第 8 周：Pipeline 集成与阶段 3 总结

## 1. 学习目标

本周把阶段 3 模块集成为可运行 pipeline，并建立最终报告：

- `run_pipeline.cpp`
- `pipeline.hpp` / `pipeline.cpp`
- `bench_pipeline.cpp`
- `dump_intermediate.cpp`
- `stage3_report.md`
- `alignment_report.md`
- `denoise_algorithm_report.md`
- `tone_mapping_algorithm_report.md`
- `hdr_toy_report.md`
- `performance_report.md`
- `stage3_interview_notes.md`

## 2. Pipeline 结构

单输入路径：

```text
input
-> denoise: none / box / gaussian
-> tone: global / local / LUT
-> gamma
-> output
```

HDR 路径：

```text
short + long exposure
-> aligned HDR merge
-> denoise
-> tone
-> gamma
-> output
```

工具保持 command-line based，便于检查参数与执行顺序。reference settings 记录在
`configs/default.yaml`，C++ 工具当前仍通过 CLI 显式传参。

## 3. 生成结果

![Pipeline comparison](figures/week8/week8_pipeline_comparison.png)

旧 pipeline metrics：

| Case | Mean luma | P95 luma | Clip fraction | Pipeline |
|---|---:|---:|---:|---:|
| global | 0.4006 | 0.6240 | 0.0000 | 43.24 ms |
| LUT | 0.4006 | 0.6241 | 0.0000 | 25.36 ms |
| local | 0.4006 | 0.6241 | 0.0000 | 103.72 ms |
| HDR local | 0.3982 | 0.6191 | 0.0000 | 126.64 ms |

这些时间来自早期 Python-side experiment，不等于当前 C++ benchmark。

## 4. 运行命令

```powershell
python .\stage3_cpp_isp\python_ref\run_week8_pipeline_summary.py
ctest --test-dir .\stage3_cpp_isp\build --output-on-failure
.\stage3_cpp_isp\build\bench_pipeline.exe
```

直接运行：

```powershell
.\stage3_cpp_isp\build\run_pipeline.exe single `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\week8_global.cpf32 `
  gaussian global reinhard 0.216 2.2
```

## 5. 阶段结果

阶段 3 已形成完整主线：

- correctness：Python-C++ alignment + CTest；
- algorithms：denoise、TM、LUT/fixed、LTM、HDR toy；
- performance：1080P/4K experiment、LTM bottleneck、pipeline benchmark；
- presentation：总报告、专题报告、面试表达和 resume bullet。

## 6. 输出排错流程

最终图异常时，不要先调 Tone Mapping 参数：

```text
source
-> denoised
-> tone_mapped
-> output (gamma)
```

使用 `dump_intermediate`：

```powershell
.\stage3_cpp_isp\build\dump_intermediate.exe `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\debug `
  gaussian global reinhard 0.216 2.2
```

诊断顺序：

1. `source` 首先错误：CPF32 shape、HWC conversion、range；
2. `denoised` 首先错误：stride、border、radius、sigma；
3. `tone_mapped` 首先错误：exposure、curve、luma/RGB、LUT rounding；
4. 只有 `output` 错误：gamma 或 output range；
5. 只有边缘错误：reflect/replicate；
6. 出现 NaN/Inf：停止，非有限输入超出当前契约。

### 6.1 第一发散原则

| 阶段 | 必查契约 | 常见形态 |
|---|---|---|
| source | shape、HWC↔planar、range | 通道错位、错行、全局 scale |
| denoised | border、radius、sigma | 边缘环带、过平滑、噪声残留 |
| HDR merged | exposure、weight、alignment | 高光低估、暗部偏差、ghost |
| tone mapped | exposure、curve、luma/RGB、LUT | 亮度、色偏、banding |
| output | gamma、clamp、range | 仅显示亮度或 clipping |

“第一个错误阶段”比“误差最大阶段”更有诊断价值，因为后续非线性模块可能放大或
压缩上游误差。

### 6.2 端到端 Golden Fixture

当前已实现自动 fixture：

```text
固定 synthetic input 与参数
Python 生成 source/denoised/tone/output golden CPF32
C++ dump 同名 intermediate tensor
逐阶段使用各自 tolerance
报告 first failed stage
```

对应文件：

- `python_ref/make_pipeline_golden.py`
- `data/pipeline_golden/`
- `tests/test_pipeline_golden.cpp`

CTest 阈值：source bit-exact、denoised `1e-6`、tone/output `1e-5`。不能只比较最终
output，否则上游正负误差可能被 curve 偶然抵消。

## 7. 阶段 4 接口

下一阶段应：

- 复用 CPF32 fixture；
- 把 hot per-pixel module 移植到 CUDA 或其他 backend；
- deployed output 与阶段 3 CPU reference 对齐；
- 固定 correctness 与 performance baseline。

## 8. Pipeline 故障实验

1. Gamma 从 `2.2` 改为 `1.0`，确认 output 首先发散；
2. Denoise border 从 reflect 改为 replicate，确认 denoised edge 首先发散；
3. LUT rounding 改成 truncate，观察 tone gradient bias；
4. CPF32 RGB channel order 交换，确认 source 已错误；
5. 每次只引入一个 bug，并记录：

```text
症状
最初怀疑
第一个发散 tensor
根因
后续 stage 如何放大或掩盖
永久测试
```

## 9. 章末自测

1. 最终输出偏暗，为什么不能立即调 exposure？
2. 只有四周不一致，应先查什么？
3. Pipeline benchmark 是否包含 allocation 为什么必须说明？
4. YAML 与 CLI 参数不一致会造成什么问题？
5. Module unit test 全过，端到端为什么仍可能失败？
