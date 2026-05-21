# 阶段 3：C++ 高性能 ISP 工程化学习路线

> **适用对象**：已经完成阶段 1 的传统 Soft-ISP 和阶段 2 的 AI-ISP baseline，具备 C++ / Python / CUDA / ISP Pipeline 对齐经验，做过定点化、四通道改造、4K / 多模式 Pipeline 适配，但需要把这些经历系统化为可展示的 C++ 图像算法工程能力。
>
> **阶段周期**：7 周。
>
> **阶段目标**：把阶段 1 的 Python Soft-ISP 中 2～3 个核心模块迁移到 C++，完成浮点版、定点版、单通道版、四通道版、多线程版和性能报告；建立 Python-C++ 输出对齐、单元测试、边界测试、基准测试、内存检查和 profiling 的完整工程闭环。
>
> **阶段产出**：一个 `cpp_isp_stage3/` 项目，一套 CMake + GoogleTest + Google Benchmark 工程，一个 C++ Soft-ISP 子集，一个 fixed-point 对齐模块，一份 1080P / 4K 性能报告，一份 Python-C++ bit-exact / tolerance 对齐报告，一份面试复述笔记。

---

## 0. 阶段三的正确学习姿势

阶段三不是单纯刷 C++ 语法，也不是把所有 Python 代码机械翻译成 C++。你要训练的是国内 ISP / AI-ISP 算法岗很看重的工程能力：

- **可对齐**：C++ 输出能和 Python reference 对齐，误差来源可解释。
- **可验证**：每个模块有单元测试、边界测试、随机测试、回归测试。
- **可量化**：性能不是“感觉快”，而是有 benchmark、平台、编译选项、输入尺寸和耗时表。
- **可优化**：知道瓶颈在内存带宽、cache miss、分支、SIMD、线程调度还是算法复杂度。
- **可迁移**：同一个模块能从单通道扩展到四通道，从 1080P 扩展到 4K，从 float 扩展到 fixed-point。

你的真实工作经历已经有 Python/C++ 对齐、定点化、四通道改造、多模式 Pipeline 和测试验证。阶段三要做的是把这些经验抽象成方法论，并用一个开源式小项目展示出来。

---

## 1. 最终项目结构

```text
cpp_isp_stage3/
├── README.md
├── CMakeLists.txt
├── cmake/
│   ├── Sanitizers.cmake
│   └── CompilerOptions.cmake
├── configs/
│   └── default.yaml
├── data/
│   ├── input/                    # 小尺寸 RAW / npy / png 测试输入
│   └── reference/                # Python 生成的 golden 输出
├── include/
│   └── cpp_isp/
│       ├── image.hpp             # ImageView / ImageBuffer / stride / layout
│       ├── fixed_point.hpp       # Q format、round、saturate
│       ├── border.hpp            # padding / border policy
│       ├── blc.hpp
│       ├── lsc.hpp
│       ├── gamma.hpp
│       ├── conv.hpp
│       ├── four_channel.hpp
│       └── pipeline.hpp
├── src/
│   ├── image.cpp
│   ├── fixed_point.cpp
│   ├── blc.cpp
│   ├── lsc.cpp
│   ├── gamma.cpp
│   ├── conv.cpp
│   ├── four_channel.cpp
│   └── pipeline.cpp
├── tools/
│   ├── run_pipeline.cpp
│   ├── compare_with_reference.cpp
│   └── dump_intermediate.cpp
├── python_ref/
│   ├── generate_reference.py
│   ├── compare_cpp_output.py
│   └── make_test_vectors.py
├── tests/
│   ├── test_fixed_point.cpp
│   ├── test_blc.cpp
│   ├── test_lsc.cpp
│   ├── test_gamma.cpp
│   ├── test_conv.cpp
│   └── test_four_channel.cpp
├── benchmarks/
│   ├── bench_blc.cpp
│   ├── bench_lsc.cpp
│   ├── bench_gamma.cpp
│   ├── bench_conv.cpp
│   └── bench_pipeline.cpp
└── reports/
    ├── stage3_report.md
    ├── alignment_report.md
    ├── performance_report.md
    └── figures/
```

**项目验收标准**：

- 至少完成 BLC、Gamma、LSC 或 3x3 convolution 中 3 个模块。
- 每个模块都有 Python reference、C++ float、C++ fixed-point 或 optimized 版本。
- 每个模块都能在小图、奇偶尺寸、边界输入、随机输入上通过测试。
- 至少支持一种四通道数据布局：`planar4` 或 `packed RGGB 4ch`。
- 1080P / 4K 输入有 benchmark 表格。
- 使用 AddressSanitizer 或 Valgrind 做过内存检查。
- 有一份清楚的性能分析：优化前后、瓶颈猜测、验证方式、结论。

---

## 2. 公开资源调研与使用方式

### 2.1 C++ 测试、基准和工程工具

| 资源 | 链接 | 阶段三怎么用 |
|---|---|---|
| GoogleTest Primer | https://google.github.io/googletest/primer.html | 搭建 C++ 单元测试，测试 fixed-point、边界、模块输出。 |
| Google Benchmark | https://github.com/google/benchmark | 做 micro benchmark，避免用手写 `chrono` 得出不稳定结论。 |
| Google Benchmark User Guide | https://github.com/google/benchmark/blob/main/docs/user_guide.md | 学 benchmark 参数、重复次数、输出 CSV/JSON。 |
| AddressSanitizer | https://clang.llvm.org/docs/AddressSanitizer.html | 检查越界、use-after-free、内存错误。Windows 可用 MSVC ASan。 |
| Valgrind Memcheck | https://valgrind.org/docs/manual/mc-manual.html | Linux 下检查非法读写、未初始化值、内存泄漏。 |
| Valgrind Quick Start | https://valgrind.org/docs/manual/quick-start.html | 快速掌握如何编译 `-g` 并运行 Memcheck。 |

**使用要求**：阶段三每个模块不是“能跑就行”，必须先有测试，再做优化。性能优化前后都要能通过同一套测试。

### 2.2 图像处理 C++ 库 / RAW 工具

| 资源 | 链接 | 阶段三怎么用 |
|---|---|---|
| LibRaw C++ API | https://www.libraw.org/docs/API-CXX.html | 学 C++ 读取 RAW / metadata，不要求从零写 RAW decoder。 |
| LibRaw API Overview | https://www.libraw.org/docs/API-overview.html | 理解 LibRaw 能提供哪些 raw data 和 metadata 字段。 |
| OpenCV parallel_for_ | https://docs.opencv.org/4.x/dc/ddf/tutorial_how_to_use_OpenCV_parallel_for_new.html | 学 OpenCV 风格多线程并行图像处理。 |
| OpenCV Universal Intrinsics | https://docs.opencv.org/4.x/d6/dd1/tutorial_univ_intrin.html | 学跨平台 SIMD 抽象，比一开始手写 AVX/NEON 更稳。 |
| OpenImageIO ImageBufAlgo | https://openimageio.readthedocs.io/en/latest/imagebufalgo.html | 了解成熟 C++ 图像库如何组织图像处理和 SIMD。 |

### 2.3 SIMD / 并行 / 性能资料

| 资源 | 链接 | 阶段三怎么用 |
|---|---|---|
| Intel Intrinsics Guide | https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html | 查 SSE / AVX / AVX2 intrinsic 的语义、吞吐和延迟。 |
| Arm Neon Intrinsics Reference | https://arm-software.github.io/acle/neon_intrinsics/ | 查 NEON intrinsic，重点了解 load/store、multiply、narrow、saturate。 |
| Arm Neon 概览 | https://www.arm.com/technologies/neon | 理解 NEON 适用场景：多媒体、图像、信号处理、CV。 |
| xsimd | https://github.com/xtensor-stack/xsimd | 了解现代 C++ SIMD wrapper，不强制使用。 |
| Simd Library | https://github.com/ermig1979/Simd | 参考高性能图像处理库如何组织 SSE/AVX/NEON 多后端。 |
| Intel VTune Profiler | https://www.intel.com/content/www/us/en/developer/tools/oneapi/vtune-profiler-documentation.html | 用于分析 CPU hotspot、memory access、threading。阶段三了解和选做。 |
| VTune Memory Access Analysis | https://www.intel.com/content/www/us/en/docs/vtune-profiler/user-guide/current/memory-access-analysis.html | 学如何定位 cache miss / memory bandwidth 问题。 |

### 2.4 定点化 / Q 格式资料

| 资源 | 链接 | 阶段三怎么用 |
|---|---|---|
| CMSIS-DSP fixed point datatypes | https://arm-software.github.io/CMSIS-DSP/latest/group__FIXED.html | 学 Q 格式、float 到 fixed 的饱和转换思路。 |
| TI Fixed-Point Data Types | https://software-dl.ti.com/msp430/msp430_public_sw/mcu/msp430/DSPLib/latest/exports/html/usersguide_fixed.html | 理解 Q15 / IQ31 等定点表示方式。 |
| Q number format | https://en.wikipedia.org/wiki/Q_%28number_format%29 | 快速查 Qm.n 表示、scale 和范围。 |
| Saturation arithmetic | https://en.wikipedia.org/wiki/Saturation_arithmetic | 理解饱和算术和普通溢出的区别。 |

**使用要求**：定点化不是简单把 `float` 改成 `int`。必须写清楚 scale、rounding、shift、saturation、intermediate bit width、误差统计。

### 2.5 Halide / 图像 pipeline 调度思想

| 资源 | 链接 | 阶段三怎么用 |
|---|---|---|
| Halide GitHub | https://github.com/halide/Halide | 了解 algorithm / schedule 分离思想，不作为阶段三主线。 |
| Halide CVPR Tutorial | https://halide-lang.org/cvpr2015.html | 学高性能图像 pipeline 的 tile、vectorize、parallel 思想。 |
| Halide Autoscheduler paper | https://halide-lang.org/papers/halide_autoscheduler_2019.pdf | 了解自动调度，不需要深入实现。 |

---

## 3. 七周详细路线

### Week 0.5：C++ 工程骨架、测试和 reference 数据

**目标**：先搭好工程和验证框架，避免后面优化时失去正确性基准。

**学习内容**：

- CMake 项目结构。
- GoogleTest 基本用法。
- Google Benchmark 基本用法。
- Python reference 与 C++ 输出文件格式约定。

**具体步骤**：

1. 新建 `cpp_isp_stage3/`。
2. 配置 CMake：
   - `Debug`
   - `Release`
   - `RelWithDebInfo`
   - 可选 `ENABLE_ASAN`
3. 接入 GoogleTest。
4. 接入 Google Benchmark。
5. 写 `python_ref/make_test_vectors.py`，生成小尺寸测试输入：
   - 8x8
   - 17x19
   - 128x128
   - 随机数据
   - 全 0 / 全 max / checkerboard
6. 定义统一二进制或 `.npy` / `.png` / `.txt` 中间输出格式。

**掌握标准**：

- 能一条命令编译项目和运行测试。
- 能解释 Debug、Release、RelWithDebInfo 的区别。
- 能说明为什么优化前必须建立 golden reference。
- 能把 Python 输出和 C++ 输出统一到同一数据范围和 dtype。

**交付物**：

- `CMakeLists.txt`
- `tests/test_smoke.cpp`
- `benchmarks/bench_smoke.cpp`
- `python_ref/make_test_vectors.py`
- `reports/week0_cpp_project_setup.md`

### Week 1：ImageBuffer / 内存布局 / 边界策略

**目标**：建立图像数据结构和内存布局直觉，这是后续四通道、4K、SIMD 的基础。

**学习内容**：

- `ImageView` vs `ImageBuffer`。
- width / height / stride / channel / layout。
- planar、interleaved、packed 4ch、RGGB 4ch。
- padding / border policy：constant、replicate、reflect、valid。
- row-major、cache line、alignment。

**具体步骤**：

1. 实现 `ImageView<T>`：
   - 指针
   - width / height / stride
   - `operator()(y, x)`
2. 实现 `ImageBuffer<T>`：
   - owning buffer
   - aligned allocation 可选
   - 转 `ImageView`
3. 支持至少两种 layout：
   - single channel
   - planar 4ch
4. 实现 border 访问函数：
   - clamp / replicate
   - constant zero
5. 写测试：
   - stride 大于 width
   - 奇数尺寸
   - 边界访问
   - planar 4ch indexing

**小实验**：

- 连续内存 row-major 遍历 vs 跨行/跨通道跳跃遍历。
- interleaved RGB vs planar RGB 访问某一个通道的耗时。
- stride 对性能和 bug 的影响。

**掌握标准**：

- 能解释为什么图像处理里 stride 不能默认等于 width。
- 能说明 planar 和 interleaved 在访问模式上的差异。
- 能解释 padding 策略变化为什么会导致 Python/C++ 对齐失败。
- 能手写一个不依赖 OpenCV Mat 的轻量 ImageView。

**交付物**：

- `include/cpp_isp/image.hpp`
- `include/cpp_isp/border.hpp`
- `tests/test_image.cpp`
- `reports/week1_memory_layout.md`

### Week 2：Python-C++ 对齐：BLC / Gamma 浮点版

**目标**：先从简单逐像素模块建立 Python-C++ 对齐方法。

**学习内容**：

- float32 / float64 差异。
- clamp / round / cast 顺序。
- absolute error / relative error / max error / mean error。
- Golden test 和 tolerance test。

**具体步骤**：

1. 从阶段一选 BLC 和 Gamma 作为第一批模块。
2. Python 生成 reference：
   - input
   - BLC output
   - Gamma output
3. C++ 实现 float 版：
   - `blc_float`
   - `gamma_srgb_float`
4. 写 `compare_with_reference.cpp`：
   - max abs error
   - mean abs error
   - error histogram
   - failed pixel count
5. GoogleTest 中加入 reference 对齐。

**小实验**：

- Python 使用 `float64` vs `float32`，观察对齐误差。
- C++ 先 clamp 再 cast vs 先 cast 再 clamp。
- `std::pow` 和近似 LUT gamma 的差异。

**掌握标准**：

- 能解释 tolerance 怎么定，不是随便写 `1e-3`。
- 能定位逐像素模块不一致的常见原因。
- 能说清 Python reference 的 dtype 必须固定。
- 能把“输出一致”写成自动化测试，而不是人工看图。

**交付物**：

- `src/blc.cpp`
- `src/gamma.cpp`
- `tests/test_blc.cpp`
- `tests/test_gamma.cpp`
- `tools/compare_with_reference.cpp`
- `reports/week2_python_cpp_alignment_float.md`

### Week 3：定点化：Q 格式、舍入、饱和与误差预算

**目标**：把你已有的定点化经验系统化，形成可讲清楚的 fixed-point 方法论。

**学习内容**：

- Qm.n 格式。
- scale 选择。
- round to nearest、floor、ceil、round half away / even。
- saturation vs wrap-around。
- intermediate bit width。
- LUT 定点化。
- 误差传播和误差预算。

**具体步骤**：

1. 实现 `fixed_point.hpp`：
   - `float_to_fixed`
   - `fixed_to_float`
   - `round_shift`
   - `saturate_cast`
   - `mul_shift`
2. 将 BLC 改成 fixed-point：
   - `(raw - black) * inv_range`
   - `inv_range` 定点化
   - 输出 uint16 或 Q 格式
3. 将 Gamma 改成 LUT：
   - 12bit / 14bit input LUT
   - output 8bit / 10bit / 16bit
4. 生成误差表：
   - float reference vs fixed output
   - max error
   - mean error
   - PSNR
   - failed pixel count under threshold
5. 写定点化设计说明。

**小实验**：

- Q8.8 / Q4.12 / Q2.14 对比误差。
- 不同 rounding 策略对 bias 的影响。
- intermediate 用 int32 vs int64 的溢出风险。
- LUT size 对 gamma 误差和速度的影响。

**掌握标准**：

- 能解释定点化不是为了“省内存”这么简单，也常用于硬件一致性和可复现。
- 能说明 scale、round、saturate、shift 的顺序。
- 能回答“为什么 Python float 和 C++ fixed 对不齐”。
- 能给出一个模块的误差预算，并说明误差是否可接受。

**交付物**：

- `include/cpp_isp/fixed_point.hpp`
- `src/fixed_point.cpp`
- `tests/test_fixed_point.cpp`
- `reports/week3_fixed_point_quantization.md`

### Week 4：LSC / 3x3 卷积：边界、tile 与 4K 大图

**目标**：进入真实图像模块，处理边界、邻域、tile 和大图性能。

**学习内容**：

- LSC gain map 插值。
- 3x3 convolution / filter。
- border policy 对结果的影响。
- tile-based processing。
- 4K 图像内存带宽和 cache locality。

**具体步骤**：

1. 实现 LSC：
   - full-size gain map 版本
   - coarse mesh + bilinear interpolation 版本
2. 实现 3x3 convolution：
   - scalar baseline
   - border replicate
   - separable optional
3. 支持 4ch planar：
   - 每个通道独立 gain
   - 每个通道独立 convolution 或共享 kernel
4. 实现 tile 版本：
   - tile 64x64 / 128x64 / 128x128
   - halo 处理
5. 做 1080P / 4K benchmark。

**小实验**：

- full gain map vs mesh interpolation 的精度和耗时。
- 不同 tile size 对性能的影响。
- border constant vs replicate 对边缘输出的影响。
- 单通道循环外层 channel vs 内层 channel 的 cache 行为。

**掌握标准**：

- 能解释邻域算子为什么比逐像素算子更容易出边界 bug。
- 能说明 tile 处理为什么需要 halo。
- 能解释四通道处理时状态隔离和边界同步的重要性。
- 能写出 LSC / convolution 的性能报告。

**交付物**：

- `src/lsc.cpp`
- `src/conv.cpp`
- `tests/test_lsc.cpp`
- `tests/test_conv.cpp`
- `benchmarks/bench_lsc.cpp`
- `benchmarks/bench_conv.cpp`
- `reports/week4_lsc_conv_tile.md`

### Week 5：并行优化：OpenMP / parallel_for / 线程切分

**目标**：掌握 CPU 多线程图像处理的正确姿势，避免为了并行而变慢。

**学习内容**：

- 按行切分、按 tile 切分、按通道切分。
- false sharing。
- 动态调度 vs 静态调度。
- OpenMP / std::thread / OpenCV `parallel_for_`。
- 多线程 benchmark 的稳定性。

**具体步骤**：

1. 给 BLC / Gamma / LSC / convolution 添加并行版本。
2. 至少实现两种策略：
   - row range parallel
   - tile parallel
3. 对比：
   - 1 thread
   - 2 threads
   - 4 threads
   - 8 threads
   - hardware concurrency
4. 记录加速比和效率：
   - speedup = T1 / TN
   - efficiency = speedup / N
5. 分析并行变慢的场景。

**小实验**：

- 小图 256x256 并行是否变慢？
- convolution 并行是否比 BLC 更容易获得收益？
- dynamic schedule 和 static schedule 对不同模块的影响。
- 按通道并行 vs 按行并行。

**掌握标准**：

- 能解释为什么多线程不是线程越多越快。
- 能说明 false sharing 和内存带宽瓶颈。
- 能根据模块类型选择并行粒度。
- 能写出加速比表格，而不是只给一个耗时数字。

**交付物**：

- `src/pipeline.cpp` 并行版本
- `benchmarks/bench_pipeline.cpp`
- `reports/week5_parallel_optimization.md`

### Week 6：SIMD / 向量化 / 编译器优化

**目标**：理解 SIMD 优化路径，先会判断是否值得 SIMD，再写小范围可验证优化。

**学习内容**：

- auto-vectorization。
- OpenCV Universal Intrinsics。
- x86 SSE / AVX2 基本 load、store、mul、add、min、max。
- ARM NEON 基本 load、store、multiply、narrow、saturating。
- alignment、tail processing、branchless clamp。

**具体步骤**：

1. 打开编译器优化报告：
   - GCC / Clang vectorization report
   - MSVC optimization report 可选
2. 对 BLC 或 Gamma LUT 写 SIMD 版本：
   - scalar
   - auto-vectorized friendly
   - manual SIMD 或 OpenCV Universal Intrinsics
3. 处理 tail pixels。
4. 对比性能：
   - scalar O3
   - auto-vectorized
   - manual SIMD
5. 查看汇编或编译器报告，确认是否真的向量化。

**小实验**：

- 分支 clamp vs `min(max(x))` branchless。
- aligned load vs unaligned load。
- float SIMD vs int16 / uint16 SIMD。
- LUT gamma 是否适合 SIMD，还是 memory access 成为瓶颈。

**掌握标准**：

- 能解释 SIMD 适合连续、规则、无复杂分支的计算。
- 能说明 tail 处理和对齐问题。
- 能回答“为什么我写了 AVX 但没有变快”。
- 能用 benchmark 证明 SIMD 版本正确且更快，或者说明不值得优化。

**交付物**：

- `src/blc_simd.cpp` 或 `src/gamma_simd.cpp`
- `benchmarks/bench_simd.cpp`
- `reports/week6_simd_vectorization.md`

### Week 7：完整 Pipeline、内存检查、性能报告和面试表达

**目标**：把阶段三整理成一个完整工程项目，而不是散碎代码实验。

**具体步骤**：

1. 整合完整 pipeline：
   - BLC
   - LSC
   - Gamma
   - optional convolution
2. 支持配置：
   - float / fixed
   - single channel / four channel
   - scalar / parallel / simd
3. 跑完整测试：
   - GoogleTest
   - ASan
   - Valgrind 可选
4. 跑 benchmark：
   - 1080P
   - 4K
   - 不同线程数
   - 不同 tile size
5. 写最终报告：
   - correctness
   - alignment
   - performance
   - memory
   - known limitations
6. 准备面试表达：
   - Python-C++ 对齐怎么做
   - 定点化怎么做
   - 四通道怎么改
   - 性能瓶颈怎么定位
   - 如何证明优化没有破坏结果

**掌握标准**：

- 能展示一套完整 C++ 图像模块工程，而不是单个函数。
- 能讲清优化前后的数据，平台和编译选项明确。
- 能解释每个优化动作为什么有效或为什么无效。
- 能把自己的真实工作经历映射到阶段三项目：对齐、定点化、四通道、4K、多模式、验证。

**最终交付物**：

- `cpp_isp_stage3/`
- `reports/stage3_report.md`
- `reports/alignment_report.md`
- `reports/performance_report.md`
- `reports/stage3_interview_notes.md`

---

## 4. 每个能力点的掌握标准

| 能力 | 入门 | 掌握 | 面试可讲 |
|---|---|---|---|
| C++ 工程骨架 | 能 CMake 编译 | 能 Debug/Release/ASan/Benchmark 分目标构建 | 能解释工程结构和可复现构建 |
| ImageBuffer | 能存图像数据 | 能处理 stride、layout、border | 能解释四通道和 4K 下内存布局取舍 |
| Python-C++ 对齐 | 能人工看图对比 | 能 golden test + error report | 能定位 dtype、round、border、overflow 差异 |
| 定点化 | 能 float 转 int | 能设计 Q 格式、round、saturate、error budget | 能讲清定点化误差和硬件一致性 |
| 邻域算子 | 能写 3x3 filter | 能处理 border、halo、tile | 能解释边界 bug 和 tile 性能 |
| 多线程 | 能 OpenMP parallel for | 能选行切分/tile 切分并分析加速比 | 能解释 false sharing 和内存带宽瓶颈 |
| SIMD | 能看懂 intrinsic | 能写一个小模块 SIMD 版本 | 能解释何时 SIMD 不一定变快 |
| Benchmark | 能手写 chrono | 能用 Google Benchmark 稳定测量 | 能写性能报告并避免误判 |
| 内存检查 | 会跑 ASan | 能用 ASan/Valgrind 定位越界/泄漏 | 能解释图像边界和 buffer bug 的风险 |

---

## 5. 阶段三面试问题清单

1. Python 和 C++ 图像模块输出不一致，你会怎么排查？
2. float32、float64、int16、uint16 在图像处理中分别有什么风险？
3. 定点化时 scale 怎么选？
4. rounding 和 saturation 为什么会影响 bit-exact？
5. intermediate bit width 为什么重要？
6. Q 格式是什么？Q4.12 和 Q8.8 有什么区别？
7. 图像 stride 为什么不能默认等于 width？
8. planar 和 interleaved layout 各有什么优缺点？
9. 四通道 Pipeline 改造中状态变量为什么要隔离？
10. padding 策略变化为什么会导致边界输出不一致？
11. tile-based 处理为什么需要 halo？
12. 为什么 4K 图像处理常常受内存带宽限制？
13. row-major 和 column-major 遍历性能为什么不同？
14. OpenMP 加线程为什么可能变慢？
15. false sharing 是什么？图像处理中哪里可能遇到？
16. 如何设计一个可靠的 benchmark？
17. `chrono` 手写计时有什么坑？
18. SIMD 适合优化什么类型的图像模块？
19. 为什么手写 AVX/NEON 不一定比编译器自动向量化快？
20. 如何证明优化没有破坏算法正确性？
21. ASan 和 Valgrind 分别能查什么问题？
22. 如果一个模块 1080P 快，但 4K 很慢，你会怎么分析？
23. 如何从性能报告判断瓶颈是计算还是内存？
24. C++ ISP 模块如何设计接口，才能便于测试和复用？
25. 你过去做四通道改造，最容易出 bug 的地方是什么？

---

## 6. 阶段三结束后的自检

如果下面问题能回答清楚，阶段三就算真正完成：

- 我能不能从 Python reference 自动生成 C++ golden test？
- 我能不能解释一个模块从 float 到 fixed 的完整过程？
- 我能不能用误差统计说明 fixed 版本是否可接受？
- 我能不能支持 single channel 和 four channel 两种数据布局？
- 我能不能处理奇数尺寸、stride、padding、边界像素？
- 我能不能用 Google Benchmark 给出稳定性能结果？
- 我能不能用 ASan / Valgrind 证明没有明显内存错误？
- 我能不能说清每个优化动作带来的收益和代价？
- 我能不能把自己的真实工作经历讲成“工程化算法能力”，而不是“改代码”？

---

## 7. 阶段三不要做什么

- 不要一开始写复杂 C++ 类继承体系，先把模块和测试跑通。
- 不要没有 reference 就做优化。
- 不要只给最终耗时，不给平台、编译选项、输入尺寸和重复次数。
- 不要所有模块都追 SIMD；先找热点。
- 不要把 OpenCV 当黑盒结果来源，OpenCV 可作对照，但你的模块要能解释。
- 不要为了追求 bit-exact 放弃画质或性能分析；要说明 tradeoff。
- 不要忽略 Windows / Linux 工具差异，ASan、Valgrind、perf、VTune 可按平台选择。

---

## 8. 推荐执行顺序摘要

```text
Week 0.5  C++ 工程骨架
  -> CMake + GoogleTest + Google Benchmark + Python reference

Week 1    ImageBuffer / Layout / Border
  -> 支持 stride、single channel、planar 4ch、border policy

Week 2    BLC / Gamma 浮点对齐
  -> Python-C++ golden test、误差报告

Week 3    定点化
  -> Q format、round、saturate、LUT、误差预算

Week 4    LSC / convolution / tile
  -> 邻域算子、四通道、4K、halo 和 tile

Week 5    多线程
  -> row/tile parallel、线程数对比、加速比报告

Week 6    SIMD
  -> auto-vectorization、Universal Intrinsics 或小模块 AVX/NEON

Week 7    总结交付
  -> 完整 Pipeline、ASan/Valgrind、性能报告、面试表达
```

---

## 9. 阶段三与阶段四的衔接

阶段三结束后，进入部署阶段前需要保留三类基准：

- **正确性基准**：Python reference、C++ float、C++ fixed 的固定测试输入和输出。
- **性能基准**：1080P / 4K 的 CPU baseline，包括单线程、多线程、SIMD。
- **接口基准**：C++ 模块的输入输出结构、内存布局、dtype、range、配置文件。

阶段四做 ONNX / TensorRT / NCNN / MNN 部署时，不要重新定义输入输出。直接复用阶段三的 C++ 数据结构和测试输入，这样才能判断部署模块到底是“真的快了”，还是只是在不同口径下测出来的。
