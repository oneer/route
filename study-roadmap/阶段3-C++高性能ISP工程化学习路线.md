# 阶段 3：C++ 高性能 ISP 算法工程化学习路线

> **阶段定位**：面向三年社招 ISP 算法工程师，不走图像测试岗或纯 tuning 岗路线。阶段三聚焦 ISP 算法模块本身：RAW Denoise、Tone Mapping 和简化 HDR merge。目标是完成算法理解、Python reference、C++ 实现、对齐验证、fixed-point / LUT 近似、1080P / 4K 性能分析和面试表达闭环。
>
> **适用对象**：已经完成阶段 1 的传统 Soft-ISP 和阶段 2 的 AI-ISP baseline，理解 RAW pipeline、BLC / DPC / LSC / Demosaic / AWB / CCM / Gamma / Tone Mapping 的基本位置，具备 Python 和 C++ 基础，希望把能力升级为可展示的 ISP 算法工程项目。
>
> **阶段周期**：8 周。
>
> **阶段目标**：实现并工程化 RAW 域去噪、全局 / 局部 Tone Mapping 和简化双曝光 HDR merge；建立 Python-C++ 输出对齐、单元测试、边界测试、误差报告、benchmark、tile / halo / 多线程性能分析和社招面试复述材料。
>
> **阶段产出**：一个 `stage3_cpp_isp/` 项目，一套 CMake + GoogleTest + Google Benchmark 工程，RAW denoise / Tone Mapping / HDR toy 三类算法模块，一份 alignment report，一份 denoise algorithm report，一份 tone mapping algorithm report，一份 HDR toy report，一份 performance report，一份社招三年口径的 interview notes。

---

## 0. 阶段三的正确方向

阶段三不是图像测试，也不是 tuning 参数适配。判断标准很简单：

- 如果主要工作是搭场景、看图、提问题单、回归验证，那偏图像测试。
- 如果主要工作是调参数、调风格、适配场景，让图更讨喜，那偏 IQ tuning。
- 如果主要工作是理解公式、实现模块、定义输入输出、处理边界、定点化、对齐验证、性能优化和解释 tradeoff，那是 ISP 算法工程。

所以本阶段的表达要始终保持算法岗口径：

- 不说“我调了很多曲线，让图更好看”。
- 要说“我实现了 Reinhard / filmic / S-curve Tone Mapping，并分析高光压缩、中间调对比、暗部噪声放大和 LUT 量化误差”。
- 不说“我对比了降噪效果”。
- 要说“我实现了 RAW 域 Gaussian / bilateral denoise，分析 shot/read noise、range sigma、kernel size、纹理误伤和 4K 性能瓶颈”。
- 不说“我做了 HDR 效果”。
- 要说“我实现了已对齐双曝光 merge toy，使用 saturation mask 和曝光权重融合 short / long exposure，并接入 Tone Mapping 验证 HDR -> SDR 链路”。

阶段三的主线是：

```text
算法原理
-> Python reference
-> C++ float implementation
-> test / alignment
-> fixed-point or LUT approximation
-> benchmark / performance analysis
-> interview explanation
```

---

## 1. 最终项目结构

```text
stage3_cpp_isp/
├── README.md
├── CMakeLists.txt
├── cmake/
│   ├── Sanitizers.cmake
│   └── CompilerOptions.cmake
├── configs/
│   └── default.yaml
├── data/
│   ├── input/
│   ├── reference/
│   └── synthetic/
├── include/
│   └── cpp_isp/
│       ├── image.hpp
│       ├── border.hpp
│       ├── fixed_point.hpp
│       ├── metrics.hpp
│       ├── denoise.hpp
│       ├── tone_mapping.hpp
│       ├── hdr_merge.hpp
│       └── pipeline.hpp
├── src/
│   ├── image.cpp
│   ├── border.cpp
│   ├── fixed_point.cpp
│   ├── metrics.cpp
│   ├── denoise_basic.cpp
│   ├── bilateral_denoise.cpp
│   ├── tone_mapping.cpp
│   ├── tone_lut.cpp
│   ├── local_tone_mapping.cpp
│   ├── hdr_merge.cpp
│   └── pipeline.cpp
├── python_ref/
│   ├── make_test_vectors.py
│   ├── noise_model_ref.py
│   ├── denoise_ref.py
│   ├── tone_mapping_ref.py
│   ├── hdr_merge_ref.py
│   └── compare_outputs.py
├── tools/
│   ├── run_pipeline.cpp
│   ├── compare_with_reference.cpp
│   └── dump_intermediate.cpp
├── tests/
│   ├── test_image.cpp
│   ├── test_border.cpp
│   ├── test_fixed_point.cpp
│   ├── test_denoise_basic.cpp
│   ├── test_bilateral_denoise.cpp
│   ├── test_tone_mapping.cpp
│   ├── test_tone_lut.cpp
│   ├── test_local_tone_mapping.cpp
│   └── test_hdr_merge.cpp
├── benchmarks/
│   ├── bench_denoise.cpp
│   ├── bench_bilateral.cpp
│   ├── bench_tone_mapping.cpp
│   ├── bench_tone_lut.cpp
│   ├── bench_local_tone_mapping.cpp
│   └── bench_pipeline.cpp
└── reports/
    ├── stage3_report.md
    ├── alignment_report.md
    ├── denoise_algorithm_report.md
    ├── tone_mapping_algorithm_report.md
    ├── hdr_toy_report.md
    ├── performance_report.md
    ├── stage3_interview_notes.md
    └── figures/
```

**验收标准**：

- 至少完成 RAW denoise、Global Tone Mapping、Tone LUT / fixed-point、Local Tone Mapping、HDR toy merge 五类模块中的四类。
- 每个核心模块都有 Python reference、C++ float 实现、对齐测试和误差报告。
- Tone Mapping 至少有一个 LUT / fixed-point 近似版本。
- Denoise 至少包含 Gaussian / box baseline 和 bilateral 主模块。
- HDR 只要求完成已对齐双曝光 toy merge，不要求 motion alignment 和 ghost removal。
- 测试覆盖小图、奇数尺寸、stride、border、随机输入、极值输入。
- 性能报告覆盖 1080P / 4K、不同线程数、至少一个 tile / halo 实验。
- 报告必须解释算法假设、输入输出、dtype / range、误差来源、性能瓶颈和 known limitations。

---

## 2. 学习资源使用顺序

### 2.1 本仓库优先资料

| 主题 | 资料 | 用法 |
|---|---|---|
| Tone Mapping 基础 | `stage1_soft_isp/soft_isp/tone.py` | 作为 Python reference 的起点，迁移到 C++。 |
| Tone Mapping 报告 | `stage1_soft_isp/reports/week4/tone_mapping_report.md` | 复习 Gamma / TM 区别、曲线和动态范围压缩。 |
| 降噪总览 | `isp_tutorial_study/full_chapters/chapter08-第8章：ISP降噪技术全景.md` | 建立 RAW denoise、亮噪、色噪、时域/空域降噪框架。 |
| NLM 专题 | `isp_tutorial_study/full_chapters/chapter09-第9章：NLM算法硬件实现专题.md` | 理解非局部去噪和复杂度，不作为阶段三主实现。 |
| HDR/TM | `isp_tutorial_study/full_chapters/chapter14-第14章：HDR技术与ToneMapping.md` | 理解 HDR merge 与 Tone Mapping 的关系。 |
| OpenISP BNF/CNF/NLM | `stage1_soft_isp/openisp/bnf.py`、`cnf.py`、`nlm.py` | 参考传统 ISP 去噪模块结构和参数含义。 |
| HDR+ 论文 | `stage1_soft_isp/materials/papers/Hasinoff_2016_HDRPlus_Burst_Photography.pdf` | 只读 pipeline、burst/HDR/low-light 关系，不复现完整 HDR+。 |
| 阶段二 denoise | `stage2_ai_isp/reports/week1_toy_rgb_denoise.md`、`week2_real_paired_rgb.md` | 对照传统 denoise 和 AI denoise 的边界。 |

### 2.2 外部公开资料

| 主题 | 资料 | 阶段三怎么用 |
|---|---|---|
| GoogleTest | https://google.github.io/googletest/primer.html | 搭建 C++ 单元测试。 |
| Google Benchmark | https://github.com/google/benchmark | 做稳定 benchmark，避免手写计时误判。 |
| AddressSanitizer | https://clang.llvm.org/docs/AddressSanitizer.html | 检查越界、use-after-free、buffer bug。 |
| OpenCV parallel_for_ | https://docs.opencv.org/4.x/dc/ddf/tutorial_how_to_use_OpenCV_parallel_for_new.html | 学图像按行 / tile 并行的工程写法。 |
| OpenCV Universal Intrinsics | https://docs.opencv.org/4.x/d6/dd1/tutorial_univ_intrin.html | SIMD 只做选读，不作为阶段三主线。 |
| Debevec HDR | https://www.pauldebevec.com/Research/HDR/ | 理解多曝光 HDR radiance map 的经典思路。 |
| Exposure Fusion | https://www.tommertens.com/old-academic/exposure_fusion/index.html | 理解不显式恢复 HDR radiance 的曝光融合思想。 |

---

## 3. 八周详细路线

### Week 0：工程骨架与验证基准

**目标**：先搭验证闭环，防止后面变成看图感觉对。

**学习内容**：

- CMake 工程组织。
- GoogleTest 单元测试。
- Google Benchmark 性能测试。
- Python reference 与 C++ 输出对齐。
- 中间结果保存格式。
- 误差统计：max abs error、mean abs error、PSNR、failed pixel count。

**具体任务**：

1. 新建 `stage3_cpp_isp/`。
2. 配置 CMake：
   - Debug
   - Release
   - RelWithDebInfo
   - 可选 `ENABLE_ASAN`
3. 接入 GoogleTest 和 Google Benchmark。
4. 写 `python_ref/make_test_vectors.py`：
   - 8x8
   - 17x19
   - 128x128
   - 1080P synthetic
   - 4K synthetic
   - 全 0、全 max、checkerboard、random、gradient、highlight patch、dark patch
5. 写 `tools/compare_with_reference.cpp`：
   - max abs error
   - mean abs error
   - RMSE
   - PSNR
   - failed pixel count under threshold

**交付物**：

- `CMakeLists.txt`
- `tests/test_smoke.cpp`
- `benchmarks/bench_smoke.cpp`
- `python_ref/make_test_vectors.py`
- `tools/compare_with_reference.cpp`
- `reports/week0_project_setup.md`

**掌握标准**：

- 能一条命令编译、测试、跑 benchmark。
- 能解释为什么 ISP 算法优化前必须有 golden reference。
- 能解释误差阈值怎么定，而不是随手写 `1e-3`。

**面试问题**：

1. Python 和 C++ 输出不一致，你怎么排查？
2. 为什么不能只看最终图判断模块正确？
3. float32 / float64 / uint16 在图像处理中分别有什么风险？

---

### Week 1：ImageBuffer / Layout / Border

**目标**：建立 C++ 图像算法底座。三年社招很容易追问 stride、边界、内存布局和 tile。

**学习内容**：

- `ImageView` vs `ImageBuffer`。
- width / height / stride / channel。
- single channel / planar RGB / planar4。
- Bayer packed 4ch 思想。
- border policy：constant、replicate、reflect。
- row-major、cache locality、alignment。

**具体任务**：

1. 实现 `ImageView<T>`：
   - data pointer
   - width / height / stride
   - `operator()(y, x)`
2. 实现 `ImageBuffer<T>`：
   - owning buffer
   - 转换为 `ImageView`
3. 实现 layout：
   - single channel
   - planar RGB
   - planar4
4. 实现 border 访问：
   - constant
   - replicate
   - reflect 可选
5. 写测试：
   - stride > width
   - 奇数尺寸
   - 边界访问
   - planar4 indexing
   - 空图 / 1x1 图

**交付物**：

- `include/cpp_isp/image.hpp`
- `include/cpp_isp/border.hpp`
- `tests/test_image.cpp`
- `tests/test_border.cpp`
- `reports/week1_image_layout.md`

**掌握标准**：

- 能解释 stride 为什么不能默认等于 width。
- 能解释 planar 和 interleaved 的访存差异。
- 能解释 border policy 为什么会导致 Python-C++ 对齐失败。
- 能说清四通道 RAW-like layout 的意义。

**面试问题**：

1. 图像处理中 stride 有什么坑？
2. tile 处理为什么需要 halo？
3. planar4 适合什么场景？

---

### Week 2：RAW 噪声模型与基础去噪

**目标**：不是会调用滤波，而是理解 RAW 域噪声和去噪的数学假设。

**学习内容**：

- shot noise：光子统计噪声，近似 Poisson。
- read noise：读出电路 / ADC 噪声，近似 Gaussian。
- Poisson-Gaussian noise model。
- RAW 域去噪 vs RGB / sRGB 域去噪。
- 去噪与 demosaic、sharpen、Tone Mapping 的关系。
- 亮噪 / 色噪区别。

**具体任务**：

1. 写 synthetic noise generator：
   - Gaussian noise
   - Poisson-Gaussian noise
   - different gain / ISO-like scale
2. 实现基础滤波：
   - box filter
   - Gaussian filter
3. 输出 residual noise map。
4. 做 edge preservation 简单指标：
   - 边缘 ROI 均值差
   - gradient magnitude 变化
5. 对比：
   - 不去噪
   - box
   - Gaussian
   - 不同 kernel size

**交付物**：

- `python_ref/noise_model_ref.py`
- `src/denoise_basic.cpp`
- `tests/test_denoise_basic.cpp`
- `reports/week2_raw_noise_and_basic_denoise.md`

**掌握标准**：

- 能解释为什么暗部噪声更明显。
- 能解释为什么 AWB gain 会放大色噪。
- 能解释 RAW denoise 为什么通常放在 demosaic 前。
- 能解释简单均值滤波为什么会糊边。

**面试问题**：

1. shot noise 和 read noise 有什么区别？
2. 为什么低光图像 denoise 更难？
3. RAW 域去噪和 sRGB 去噪有什么差别？

---

### Week 3：Bilateral / NLM 思想与工程实现

**目标**：做一个真正可讲的传统去噪模块。主攻 bilateral，NLM 做理解和小尺寸实验。

**学习内容**：

- bilateral filter：
  - spatial weight
  - range weight
  - edge preserving
- NLM：
  - patch similarity
  - search window
  - 计算复杂度
- 参数影响：
  - kernel size
  - sigma spatial
  - sigma range
  - noise level

**具体任务**：

1. 实现 C++ bilateral filter：
   - scalar baseline
   - replicate border
   - float32 input / output
2. 实现 range LUT 优化：
   - intensity difference -> weight
   - 对比直接 `exp` 与 LUT
3. 写 Python reference 并做对齐。
4. 做小尺寸 NLM reference：
   - 只要求 32x32 或 64x64
   - 重点理解复杂度，不追实时
5. 做参数消融：
   - kernel size
   - sigma spatial
   - sigma range
   - noise level

**交付物**：

- `python_ref/denoise_ref.py`
- `src/bilateral_denoise.cpp`
- `src/nlm_reference.cpp` 可选
- `tests/test_bilateral_denoise.cpp`
- `benchmarks/bench_bilateral.cpp`
- `reports/week3_bilateral_nlm_denoise.md`

**掌握标准**：

- 能解释 bilateral 为什么保边。
- 能解释 sigma range 太大 / 太小分别发生什么。
- 能解释 NLM 为什么质量好但计算重。
- 能解释去噪和纹理误伤的 tradeoff。

**面试问题**：

1. bilateral filter 的核心公式是什么？
2. 为什么 range weight 能保护边缘？
3. NLM 为什么不适合直接做实时 4K baseline？

---

### Week 4：Denoise 性能优化与 4K 分析

**目标**：把去噪从算法实现推进到工程能力。

**学习内容**：

- 复杂度分析。
- tile processing。
- halo。
- row parallel vs tile parallel。
- cache locality。
- memory bandwidth vs compute bound。
- Google Benchmark 正确使用。

**具体任务**：

1. 建立 bilateral scalar baseline。
2. 对比 range LUT version。
3. 实现 tile version：
   - 64x64
   - 128x64
   - 128x128
   - halo = radius
4. 实现多线程版本：
   - row split
   - tile split
5. benchmark：
   - 256x256
   - 1080P
   - 4K
   - 1 / 2 / 4 / 8 threads
6. 输出 speedup 和 efficiency：
   - speedup = T1 / TN
   - efficiency = speedup / N

**交付物**：

- `benchmarks/bench_denoise.cpp`
- `reports/week4_denoise_performance.md`

**掌握标准**：

- 能解释为什么去噪模块很容易成为性能瓶颈。
- 能解释 tile size 如何影响 cache。
- 能解释线程数增加为什么不一定更快。
- 能判断瓶颈偏计算还是偏访存。

**面试问题**：

1. 4K bilateral filter 为什么慢？
2. tile halo 怎么处理？
3. 如何证明优化没有破坏结果？

---

### Week 5：Global Tone Mapping 算法

**目标**：建立动态范围压缩的算法理解，不停留在曲线调参。

**学习内容**：

- dynamic range。
- linear RGB / luminance。
- global tone mapping。
- Reinhard operator。
- filmic curve。
- S-curve。
- percentile exposure normalization。
- Gamma vs Tone Mapping。

**具体任务**：

1. 实现 Reinhard TM。
2. 实现 filmic TM。
3. 实现 S-curve TM。
4. 实现 luminance-based TM：
   - 计算 Y
   - 对 Y 做 tone mapping
   - 用 RGB ratio preserve 还原颜色比例
5. 实现 histogram / ROI 统计：
   - high-light ROI
   - shadow ROI
   - mid-tone ROI
6. 对比：
   - 高光压缩
   - 中间调对比
   - 暗部抬升
   - 饱和 / clipping

**交付物**：

- `python_ref/tone_mapping_ref.py`
- `src/tone_mapping.cpp`
- `tests/test_tone_mapping.cpp`
- `reports/week5_global_tone_mapping.md`

**掌握标准**：

- 能解释 TM 和 Gamma 的区别。
- 能解释为什么 TM 应该在线性域做。
- 能解释高光压缩和中间调对比的取舍。
- 能解释为什么 Reinhard 容易发灰。

**面试问题**：

1. Tone Mapping 解决什么问题？
2. 为什么不能先 Gamma 再 Tone Mapping？
3. 高光保护和整体对比有什么冲突？

---

### Week 6：Tone Curve LUT / Fixed-Point

**目标**：把 Tone Mapping 做成接近部署的工程模块。

**学习内容**：

- LUT 近似。
- input bit depth：10 / 12 / 14 / 16 bit。
- output bit depth：8 / 10 / 12 / 16 bit。
- fixed-point scale。
- rounding。
- saturation。
- banding。
- quantization error。

**具体任务**：

1. 实现 tone curve LUT generator：
   - 10bit input LUT
   - 12bit input LUT
   - 14bit input LUT 可选
2. 实现 C++ LUT apply。
3. 实现 fixed-point helper：
   - `float_to_fixed`
   - `fixed_to_float`
   - `round_shift`
   - `saturate_cast`
4. 做 float vs LUT error report：
   - max error
   - mean error
   - PSNR
   - failed pixel count
5. 做 LUT size 消融。
6. 检查暗部 banding：
   - gradient input
   - shadow crop

**交付物**：

- `include/cpp_isp/fixed_point.hpp`
- `src/fixed_point.cpp`
- `src/tone_lut.cpp`
- `tests/test_fixed_point.cpp`
- `tests/test_tone_lut.cpp`
- `benchmarks/bench_tone_lut.cpp`
- `reports/week6_tone_lut_fixed.md`

**掌握标准**：

- 能解释 LUT 为什么适合 TM / Gamma。
- 能解释 LUT size 和误差 / 速度的关系。
- 能解释 fixed-point 的 scale、round、saturate。
- 能解释 banding 从哪里来。

**面试问题**：

1. 12bit 输入映射到 10bit 输出怎么设计 LUT？
2. fixed-point 和 float 对不齐，你怎么查？
3. LUT 和直接公式计算各有什么优缺点？

---

### Week 7：Local Tone Mapping / HDR Toy

**目标**：理解局部动态范围压缩和 HDR merge，但不做完整商用 HDR+。

**学习内容**：

- Local Tone Mapping。
- base/detail 分解。
- bilateral / guided filter 思想。
- halo artifact。
- 双曝光 HDR merge。
- short exposure / long exposure。
- saturation mask。
- exposure ratio。
- ghosting 风险。

**具体任务**：

Local TM：

1. 用 blur / bilateral 估计 base layer。
2. 计算 detail layer。
3. 对 base 做 tone compression。
4. reconstruct 输出。
5. 对比 global TM：
   - 高光
   - 暗部
   - 局部对比
   - halo 风险

HDR toy：

1. 构造两张已对齐曝光图：
   - short exposure
   - long exposure
2. 设计 saturation-aware weight：
   - 饱和区降低 long exposure 权重
   - 暗区降低 short exposure 权重
3. 做 simple exposure merge。
4. 输出 HDR-like linear result。
5. 接 Global TM / Local TM。
6. 分析 ghosting 风险，但不实现 motion alignment / ghost removal。

**交付物**：

- `python_ref/hdr_merge_ref.py`
- `src/local_tone_mapping.cpp`
- `src/hdr_merge.cpp`
- `tests/test_local_tone_mapping.cpp`
- `tests/test_hdr_merge.cpp`
- `benchmarks/bench_local_tone_mapping.cpp`
- `reports/week7_ltm_hdr_toy.md`

**掌握标准**：

- 能解释 Global TM 和 Local TM 区别。
- 能解释 LTM 为什么容易出 halo。
- 能解释 HDR merge 为什么需要曝光对齐。
- 能解释 short exposure 和 long exposure 分别保什么。
- 能解释 HDR 后为什么仍然需要 TM。

**面试问题**：

1. HDR 和 Tone Mapping 是什么关系？
2. 多帧 HDR 为什么会有 ghost？
3. Local TM 的 halo 怎么产生？
4. base/detail 分解为什么有用？

---

### Week 8：整合、报告和面试表达

**目标**：形成三年社招可展示项目。

最终 pipeline：

```text
RAW-like / linear input
-> optional RAW denoise
-> optional HDR merge
-> global TM / local TM
-> gamma / output
```

**具体任务**：

1. 整合 `run_pipeline.cpp`：
   - denoise on/off
   - HDR merge on/off
   - global TM / local TM switch
   - LUT / float switch
2. 跑完整测试：
   - GoogleTest
   - ASan 可选
3. 跑最终 benchmark：
   - 1080P
   - 4K
   - different thread count
   - different tile size
4. 写最终报告：
   - correctness
   - alignment
   - algorithm analysis
   - fixed / LUT error
   - performance
   - known limitations
5. 写面试复述笔记。

**最终交付**：

- `stage3_cpp_isp/`
- `reports/stage3_report.md`
- `reports/alignment_report.md`
- `reports/denoise_algorithm_report.md`
- `reports/tone_mapping_algorithm_report.md`
- `reports/hdr_toy_report.md`
- `reports/performance_report.md`
- `reports/stage3_interview_notes.md`

**最终报告必须包含**：

- 算法公式。
- 输入输出定义。
- 数据范围和 dtype。
- Python-C++ 对齐方式。
- error table。
- visual crop。
- 1080P / 4K benchmark。
- 性能瓶颈分析。
- known limitations。

**最终面试表达**：

> 我在阶段三做了一个 C++ ISP 算法工程化项目，围绕 RAW denoise、Tone Mapping 和简化 HDR merge 展开。去噪部分实现了 Gaussian / bilateral baseline，并分析了噪声模型、保边能力、参数消融和 4K 性能瓶颈；Tone Mapping 部分实现了 Reinhard、filmic、S-curve 和 LUT/fixed-point 版本，并分析了高光压缩、暗部噪声放大、banding 和误差来源；HDR 部分实现了已对齐双曝光 merge toy，并接入 TM 验证动态范围压缩链路。整个项目有 Python reference、C++ 实现、GoogleTest、benchmark 和误差报告。

---

## 4. 可选扩展

阶段三主线已经足够支撑三年社招，不建议继续堆模块。如果要扩展，只加两个轻量点。

### 4.1 Unsharp Mask / Edge Enhancement

**为什么加**：去噪后常接锐化，面试可能追问去噪和锐化如何平衡。

**做法**：

- 实现 unsharp mask baseline。
- 对比 denoise 前锐化 vs denoise 后锐化。
- 观察 noise amplification、halo、overshoot。

**交付物**：

- `src/unsharp_mask.cpp`
- `reports/optional_unsharp_mask.md`

### 4.2 RAW 前后去噪位置对比

**为什么加**：ISP 算法面试常问 RAW 域 / RGB 域 / sRGB 域处理差别。

**做法**：

- RAW-like single channel denoise。
- Demosaic / pseudo RGB 后 denoise。
- 对比边缘、色噪、细节损失。

**交付物**：

- `reports/optional_raw_vs_rgb_denoise.md`

---

## 5. 阶段三不要做什么

- 不做完整 HDR+ burst pipeline。
- 不做复杂 optical flow / motion alignment。
- 不做商用级 ghost removal。
- 不做纯 tuning 参数适配。
- 不做“我调了很多曲线所以图好看”的表达。
- 不做 AI denoise 大模型训练。
- 不一开始手写 AVX / NEON。
- 不堆很多模块但没有测试和报告。

可以了解但不作为主线：

- guided filter。
- BM3D。
- NLM 高性能优化。
- HDRNet。
- deep RAW denoise。
- 3A 联动。
- 车载 HDR sensor pipeline。

---

## 6. 三年社招深度标准

完成阶段三后，至少要能讲清下面内容。

### 6.1 RAW Denoise

- RAW 域和 RGB / sRGB 域去噪差异。
- shot noise / read noise / Poisson-Gaussian model。
- bilateral 的公式和参数影响。
- NLM 为什么计算重。
- 去噪如何影响 demosaic / sharpening / Tone Mapping。
- 如何评估过度去噪和纹理误伤。

### 6.2 Tone Mapping

- Tone Mapping 和 Gamma 的区别。
- Global TM 的局限。
- Reinhard / filmic / S-curve 差异。
- luminance-based TM 和 RGB per-channel TM 的差异。
- LUT / fixed-point 设计。
- banding 和 clipping 来源。
- 暗部提亮为什么会放大噪声。

### 6.3 HDR

- HDR merge 和 Tone Mapping 的关系。
- short / long exposure 分工。
- saturation mask。
- exposure ratio。
- ghosting 风险。
- 为什么阶段三只做 aligned toy。

### 6.4 C++ 工程

- ImageBuffer / stride / border。
- Python-C++ 对齐。
- fixed-point 误差。
- tile / halo。
- benchmark 设计。
- 1080P / 4K 性能瓶颈。
- 如何证明优化正确。

---

## 7. 简历写法

项目名称建议：

```text
C++ 高性能 ISP 算法模块工程化项目：RAW 去噪 / Tone Mapping / HDR
```

项目描述：

```text
围绕 ISP pipeline 中 RAW 去噪、Tone Mapping 和简化 HDR merge 模块，完成从 Python reference 到 C++ 实现、对齐验证、LUT/fixed-point 近似和 1080P/4K 性能优化的工程闭环。
```

项目要点：

- 实现 RAW 域 Gaussian / bilateral 去噪模块，分析 shot noise、read noise、range sigma、kernel size 对噪声抑制和边缘保留的影响，并完成参数消融实验。
- 实现 Reinhard / filmic / S-curve Tone Mapping，并支持基于 LUT 的 fixed-point 近似，输出 float vs LUT 误差统计，分析高光压缩、暗部噪声放大和 banding 风险。
- 实现简化双曝光 HDR merge，基于 saturation mask 和曝光权重融合 short / long exposure，并接入 Tone Mapping 验证 HDR -> SDR 显示链路。
- 搭建 CMake + GoogleTest + Google Benchmark 工程，建立 Python-C++ golden reference 对齐流程，覆盖奇数尺寸、stride、border、随机输入和极值输入测试。
- 针对 1080P / 4K 输入完成 benchmark，分析 bilateral / local tone mapping 的计算复杂度、tile halo、多线程加速比和 cache / 访存瓶颈。
- 输出 alignment report、denoise report、tone mapping report、HDR toy report 和 performance report，沉淀模块输入输出、误差来源、性能瓶颈和已知限制。

简历空间较紧时，可以压缩为三条：

- 实现 C++ RAW denoise / Tone Mapping / HDR merge 模块，完成 Python reference 对齐、单元测试、边界测试和 1080P / 4K benchmark。
- 针对 bilateral denoise 和 local tone mapping 进行参数消融与性能分析，覆盖 kernel size、range sigma、tile halo、多线程加速比等工程问题。
- 实现 Tone Mapping LUT / fixed-point 近似，分析 float 与定点版本误差、高光压缩、暗部噪声放大、banding 和 clipping 风险。

---

## 8. 阶段三与阶段四衔接

阶段三结束后，阶段四再做模型部署或 CUDA / TensorRT / NCNN / MNN 时，不要重新定义输入输出。阶段三要保留三类基准：

- **正确性基准**：Python reference、C++ float、LUT / fixed 的固定测试输入和输出。
- **性能基准**：1080P / 4K CPU baseline，包括单线程、多线程、tile 版本。
- **接口基准**：C++ 模块输入输出结构、内存布局、dtype、range、配置文件。

这样阶段四做 AI denoise、HDRNet、learned ISP 或端侧部署时，才能判断新模块是真的提升了画质 / 性能，还是只是换了口径。
