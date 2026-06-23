# 阶段 3 性能报告

## 1. 报告范围

本报告汇总阶段 3 各模块在 CPU Release build 下的 benchmark 行为。目标是理解
bottleneck 和 scaling，不是宣称已经达到 production realtime。

## 2. 测量契约

当前自写 C++ harness 使用：

- 1 次 warmup；
- quick mode 测 5 次；
- `--full` mode 测 3 次；
- 报告 median latency；
- file I/O 不在计时区间；
- module benchmark 在计时前分配主要 buffer；
- `bench_pipeline` 的 `run_pipeline_single` 内仍包含中间 buffer allocation。

仓库中已提交的旧 CSV 来自早期 harness，当时只运行 1–3 次并选择最好值。这批数据
只能用于解释数量级和相对趋势，不能冒充当前 median methodology 的结果。

旧 Week 4 环境记录：

- CMake 3.30.5；
- Ninja 1.12.1；
- MinGW.org GCC 9.2.0；
- Release build；
- 32-bit MinGW toolchain。

旧 CSV 没有可靠记录 CPU model 与 core count，因此不能泛化到 ARM、NEON、
mobile SoC 或其他桌面 CPU。

### 2.1 证据状态

| 数据 | 方法 | 当前用途 |
|---|---|---|
| Week 4–7 committed CSV | early best-of-few | 学习数量级与相对趋势 |
| 2026-06-18 smoke | warmup + 5-run median | 验证新 harness |
| 2026-06-22 clean pipeline smoke | clean Release build + median | 验证当前源码端到端执行 |
| 2026-06-23 完整数据 | warmup + median | 当前正式性能基线 |

正式证据目录：`reports/figures/benchmark_20260623/`。

环境：

- Intel Core i3-12100F，4 physical cores / 8 logical processors；
- Windows 10 Pro 64-bit，10.0.19045；
- MinGW.org GCC 9.2.0；
- CMake 3.30.5，Ninja 1.12.1；
- Release build；
- Release flags：`-O3 -DNDEBUG`；
- commit `80de98a` 加本轮 golden-test 文档补丁；
- 不包含 file I/O；module benchmark 在计时前分配主要 buffer；
- pipeline 包含 `run_pipeline_single` 内部 intermediate allocation。

## 3. 当前 Harness 冒烟验证

2026-06-18 更新后的 harness 在以下环境完成 smoke test：

- Intel Core i3-12100F；
- 4 physical cores / 8 logical processors；
- MinGW.org GCC 9.2.0；
- CMake 3.30.5；
- Ninja 1.12.1；
- Release build；
- 1 warmup + 5 measured runs + median；
- synthetic float input；
- 不包含 file I/O。

代表性结果：

| Case | 尺寸 | Median |
|---|---:|---:|
| bilateral direct | 128×128×1 | 47.325 ms |
| bilateral LUT | 128×128×1 | 38.718 ms |
| bilateral direct | 256×256×1 | 188.478 ms |
| bilateral LUT | 256×256×1 | 155.599 ms |
| gaussian + global Reinhard | 640×360×3 | 134.122 ms |
| gaussian + Reinhard LUT | 640×360×3 | 158.343 ms |
| local Reinhard | 640×360×3 | 1446.478 ms |

该 smoke run 证明新测量路径可用，但不能替代完整 1080P/4K 数据。它也说明不能写
“LUT 永远更快”：640×360 integrated pipeline 中，Reinhard LUT 反而慢于 float。

2026-06-22 使用独立临时目录重新配置当时源码，clean Release build 成功，
11/11 CTest 通过，`bench_pipeline` 结果为历史 smoke：

| Case | 尺寸 | Median |
|---|---:|---:|
| gaussian + global Reinhard | 320×180×3 | 17.010 ms |
| gaussian + Reinhard LUT | 320×180×3 | 19.606 ms |
| local Reinhard | 320×180×3 | 283.578 ms |
| gaussian + global Reinhard | 640×360×3 | 66.997 ms |
| gaussian + Reinhard LUT | 640×360×3 | 65.000 ms |
| local Reinhard | 640×360×3 | 1140.898 ms |

两次 smoke 不应求平均，因为 background load 与运行条件没有作为同一正式实验控制。
它们只能支持定性结论：Local TM 明显最重；便宜的 Reinhard 不保证 LUT 加速。

## 4. Tone Mapping 性能

2026-06-23 正式 median 数据：

| 方法 | Curve | Mode | 尺寸 | 耗时 |
|---|---|---|---:|---:|
| float | Reinhard | luma | 1920×1080 | 53.530 ms |
| LUT 12→12 | Reinhard | luma | 1920×1080 | 47.595 ms |
| float | S-curve | luma | 1920×1080 | 331.794 ms |
| LUT 12→12 | S-curve | luma | 1920×1080 | 45.999 ms |
| float | S-curve | luma | 3840×2160 | 1334.930 ms |
| LUT 12→12 | S-curve | luma | 3840×2160 | 203.076 ms |

解释：

- Reinhard 本身便宜，LUT 收益小；
- S-curve 含每像素 `exp`，LUT 收益明显；
- luminance-preserving 仍要计算 luma、division 和 RGB scale；
- LUT 查表不是整个 pipeline 的唯一成本。

## 5. Local Tone Mapping 性能

2026-06-23 正式 median 数据：

| Base filter | Radius | 尺寸 | 耗时 |
|---|---:|---:|---:|
| box | 5 | 640×360 | 179.882 ms |
| box | 9 | 640×360 | 451.166 ms |
| bilateral | 3 | 640×360 | 1090.061 ms |
| bilateral | 5 | 640×360 | 2457.221 ms |
| box | 5 | 1920×1080 | 1474.546 ms |
| bilateral | 1 | 1920×1080 | 1791.271 ms |

解释：

- direct local filter 的样本数随 `(2r+1)^2` 增长；
- bilateral 每个邻居还要计算 spatial 与 range weight；
- naive LTM 适合 correctness 与 halo 学习，不适合 production deployment；
- 产品方向可考虑 guided filter、bilateral grid、pyramid、SIMD、threading 或 GPU；
- 没有 perf/VTune counter 时，不能声称已实测 cache miss。

## 6. 集成 Pipeline

2026-06-23 正式 full pipeline median：

| Case | Pipeline 耗时 |
|---|---:|
| gaussian + global TM，1080P | 593.998 ms |
| gaussian + LUT TM，1080P | 642.063 ms |
| local TM，1080P | 9920.300 ms |
| gaussian + global TM，4K | 2362.866 ms |
| gaussian + LUT TM，4K | 2360.626 ms |
| local TM，4K | 39098.739 ms |

该结果表明：

- Local TM base estimation 明显占主导；
- 4K 像素数约为 1080P 的 4 倍，三条 pipeline 延迟也接近 4 倍；
- Reinhard 公式本身便宜，integrated LUT 并不稳定优于 float。

当前 pipeline benchmark：

```powershell
.\stage3_cpp_isp\build\bench_pipeline.exe
.\stage3_cpp_isp\build\bench_pipeline.exe --full
```

## 7. 下一步优化目标

1. 将 direct LTM base 替换为 guided filter 或 bilateral grid，重新验证 alignment
   和 halo；
2. 在尝试 hardware-specific SIMD 之前，先加入 persistent thread pool；
3. 在 ARM/移动端复验同一 correctness 与 benchmark 契约。

SIMD、CUDA、OpenCL、Halide、AVX、NEON 当前只是对比与后续方向，没有在阶段 3
实现和测量。

## 8. 怎样正确阅读性能表

看到 640×360 Local TM 约 1.1 s，不能直接写“cache 很差”。正确推理链：

```text
已知：
direct neighborhood filter
每像素访问 (2r+1)^2 个邻居

观察：
Local TM 远慢于 global per-pixel TM

合理推断：
邻域计算与中间 buffer 是主要候选成本

仍未知：
cache miss、带宽、分支、指令比例

下一步证据：
stage timing 或 perf/VTune/hardware counter
```

## 9. 正式 Benchmark 模板

```text
Machine:
  CPU / physical cores / logical processors / RAM / OS

Build:
  compiler / version / architecture / Release flags / commit

Case:
  width / height / channels / parameters / threads

Method:
  warmup / repeats / median or percentile

Timed scope:
  I/O? allocation? format conversion? thread creation?

Correctness:
  optimization 后是否重跑 tests 与 alignment?

Result:
  latency / throughput / speedup / efficiency

Boundary:
  哪些结论不能泛化？
```

## 10. 性能练习

选择一个 case：

1. 先预测像素数扩大 4 倍时的耗时比例；
2. 预测 radius 变化对应的邻域样本比例；
3. 分别测包含和不包含 buffer allocation 的版本；
4. 保存每次 raw timing，不只保存汇总值；
5. 若结果违背预测，列出至少三个可验证假设，不要直接归因于 cache。
