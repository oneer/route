# 阶段 3 教程化审查与证据矩阵

本文回答一个问题：仓库里的公式、Python reference、C++ 实现、测试、对齐和性能结论，是否真的连成了可复查的工程闭环？

## 1. 先读什么

建议按下面顺序学习，而不是先翻最终性能表：

1. `week0_project_setup.md`：CPF32 与误差指标。
2. `week1_image_layout.md`：planar、stride、border。
3. Week 2～4：从基础滤波到 bilateral LUT、tile、线程。
4. Week 5～6：float Tone Mapping 到 LUT/fixed-point。
5. Week 7：Local TM 与 aligned HDR toy。
6. `week8_pipeline_integration.md`：集成、逐阶段 dump 和故障定位。
7. `stage3_report.md`：只做阶段结论回顾，不替代前面的教程。

每个模块都用同一问题清单复述：

```text
公式是什么？
输入的 layout / dtype / range 是什么？
Python reference 的 border / rounding 是什么？
C++ API 如何表达这些约定？
哪个测试向量最容易暴露错误？
阈值来自浮点误差还是量化步长？
benchmark 测量是否包含分配？
优化后是否重新做 correctness？
```

## 2. 全局数据契约

### 2.1 CPF32 wire format

```text
ASCII: CPF32\n
ASCII: <width> <height> <channels>\n
binary: width * height * channels 个 little-endian IEEE-754 float32
```

payload 是连续 HWC / interleaved 顺序：

```text
index(y, x, c) = (y * width + x) * channels + c
```

例如 `width=2, height=1, channels=3`：

```text
[R00, G00, B00, R01, G01, B01]
```

这与内部 `ImageBuffer` 的 planar 布局不同。CPF32 读入算法前要做 HWC → planar
转换，写出时反向转换。CPF32 不保存 stride；文件 payload 必须连续。当前
C++ reader/writer 明确要求 little-endian host，并拒绝 shape 与 payload 长度不一致的文件。

### 2.2 ImageBuffer / ImageView

内部地址公式：

```text
offset(y, x, c) = c * channel_stride + y * row_stride + x
channel_stride >= row_stride * height
row_stride >= width
```

`operator()` 不检查边界，热循环使用它；`at()` 用于需要诊断的边界检查。算法
API 接受 view，因此可以处理 padding stride；CPF32 只是连续交换格式，不代表算法
内部也是 HWC。

### 2.3 数值范围与非有限值

- denoise synthetic 主线：finite float32，通常 `[0,1]`；
- HDR merge 和 Tone Mapping 输入可高于 `1`；
- Tone Mapping / LUT 输出通常回到 `[0,1]`；
- Python reference 是本项目 golden implementation，不是理论真值；
- NaN/Inf 不属于当前算法数据契约。对齐工具遇到非有限值会报错，避免 NaN 因
  比较规则而被误记为“0 failed values”。

### 2.4 Border 口径

本项目的 `Reflect` 是不重复边界像素的 reflect-101 风格：

```text
输入索引:       0 1 2 3
访问 -1 -> 1
访问  4 -> 2
```

它不同于会重复端点的 symmetric/reflect 变体。Python/C++ 对齐时必须同时写明
policy 和映射样例，不能只写“mirror”。

## 3. 算法—实现—证据对应表

| 模块 | Python golden | C++ API / 实现 | 核心测试 | 对齐阈值/证据 | benchmark | 结论边界 |
|---|---|---|---|---|---|---|
| CPF32/metrics | `make_test_vectors.py`, `compare_outputs.py` | `cpf32.*`, `metrics.*` | `test_cpf32.cpp`, `test_smoke.cpp` | identity 应 bit-exact；非有限值拒绝 | `bench_smoke` 仅 smoke | 项目私有交换格式 |
| Image/Border | `visualize_week1_layout.py` | `image.hpp`, `border.*` | stride、planar4、1×1 reflect、越界 | 手算索引，无容差 | 无 | 尚无 ROI constructor / aligned allocator |
| Box/Gaussian | `noise_model_ref.py`, Week2 runner | `denoise_basic.cpp` | 常量、impulse、kernel sum | float32 累加误差 | `bench_denoise` 部分路径 | RAW-like，不是完整 Bayer RAW |
| Bilateral | `denoise_ref.py` | `bilateral_denoise.cpp` | edge、direct-vs-LUT、奇数 tile/thread | Python-C++ `1e-5`；优化版本 vs LUT `1e-6` | 256/1080P/4K | scalar；无 SIMD；tile 未搬入 scratch |
| Global TM | `tone_mapping_ref.py` | `tone_mapping.cpp` | 单调性、已知值、luma ratio、gamma | `1e-5`，报告 max/mean/RMSE/PSNR | 1080P/4K | synthetic HDR-like 场景 |
| Tone LUT/fixed | Week6 runner | `tone_lut.cpp`, `fixed_point.cpp` | clamp、round、shift、saturate、奇数尺寸 | 阈值应结合输出量化步长 | float vs LUT | fixed helper 不等于硬件定点 kernel |
| Local TM | Week7 runner | `local_tone_mapping.cpp` | 常量、highlight、box-vs-bilateral step | Python-C++ `1e-5` | 640×360/1080P | direct base filter，非产品实时实现 |
| HDR toy | `hdr_merge_ref.py` | `hdr_merge.cpp` | 权重、未饱和恢复、长曝光饱和 | Python-C++ `1e-5` | 只在 pipeline 中观察 | 已对齐双曝光；无配准/去鬼影 |
| Pipeline | Week8 runner | `pipeline.*`, tools | 由模块测试与端到端运行共同覆盖 | 用 `dump_intermediate` 找首个错误阶段 | preview/1080P/4K harness | YAML 仅记录参数，C++ 未解析 YAML |

## 4. 性能证据应怎样读

当前 C++ benchmark harness 测量算法调用，输入和主要输出 buffer 在计时前建立；
pipeline benchmark 仍包含各阶段中间 buffer 的分配。更新后的自写 harness 统一使用：

- 1 次 warmup；
- quick 模式 5 次、full 模式 3 次测量；
- median latency；
- `steady_clock`；
- 不包含文件 I/O。

仓库中已经提交的旧 CSV 是早期 harness 结果，使用过“1～3 次取最好值”的方法。
它们可以解释数量级和相对趋势，但不能与更新后的 median 结果混为同一批实验。重新
发布性能数字时必须重新生成 CSV，并记录：

```text
CPU 型号 / 物理核心与逻辑线程
OS
编译器与版本
Release flags
输入尺寸、通道和参数
线程数
warmup / repeats / statistic
是否包含 I/O、分配、格式转换
latency 或 throughput
```

没有 perf、VTune 或硬件计数器时，报告只能说“根据邻域访问次数和尺寸缩放推断”
计算/访存压力，不能声称 cache miss 已被实测定位。

## 5. 审查中修复的事实问题

- 补充 CPF32 的 HWC payload 与内部 planar layout 区别。
- C++ CPF32 reader 现在拒绝多余 payload，writer 拒绝零维 shape。
- alignment metrics 现在拒绝 NaN/Inf，避免错误通过。
- 新增 CPF32 HWC round-trip、payload 长度和 non-finite 测试。
- benchmark 从“少量运行取最好值”改为 warmup + median。
- 文档明确：默认测试是 CTest 驱动的轻量可执行文件；只有 FetchContent smoke
  target 会实际使用 GoogleTest / Google Benchmark。
- 将已提交旧 CSV 标记为 legacy methodology，不冒充新 harness 结果。

## 6. 仍未具备的证据

- 没有 AVX/NEON/Universal Intrinsics 实现与数值复验。
- 没有 ARM、移动 SoC、DSP、GPU 或硬件 ISP 测量。
- 没有 perf/VTune cache miss、带宽或指令级证据。
- 没有真实 Bayer RAW pipeline；SIDD bridge 输入是 sRGB 图像。
- 没有产品级 NLM、HDR 配准、motion rejection 或 deghost。
- 没有用新 benchmark 方法重新生成全部 1080P/4K CSV。

## 7. 三个最高优先级后续项

1. 用新 harness 在固定机器重新生成全部性能 CSV，并补设备元数据。
2. 为 pipeline 增加端到端 golden fixture，逐阶段比较 source/denoised/tone/output。
3. 只选择一个热点做真实优化：优先 persistent thread pool 或 guided-filter LTM；
   每次优化后重跑单测、Python-C++ 对齐和 benchmark。

## 8. Capstone

在干净目录独立实现一个 3×3 finite-input 模块，例如 unsharp mask：

1. 写公式和 range/border 契约；
2. 写 Python golden；
3. 写 C++17 `ImageView` API；
4. 覆盖 1×1、奇数尺寸、stride>width、极值；
5. 生成 CPF32 并报告 max/mean/RMSE/PSNR/failed count；
6. 写 warmup + median benchmark；
7. 故意制造一次 stride 或 border bug，用中间结果找到首个错误点；
8. 用两分钟说明质量、误差、速度和产品升级方向。
