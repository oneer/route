# 第 5 周：Global Tone Mapping

## 1. 学习目标

本周实现 Global Tone Mapping，重点是理解“动态范围压缩”，不是手工调风格。

完整路径：

```text
HDR-like linear RGB
-> percentile exposure normalization
-> Reinhard / Filmic / S-curve
-> RGB per-channel 或 luminance-preserving
-> optional display gamma
-> Python-C++ alignment
-> benchmark
```

## 2. 问题背景

RAW 或 linear RGB 可以表达远高于显示范围的 scene-referred radiance；普通 SDR
显示或 8-bit image 需要 bounded display-referred value。

Tone Mapping 解决：

- highlight compression；
- mid-tone contrast placement；
- shadow visibility；
- clipping reduction。

它与 Gamma 不同：

- Tone Mapping 把 scene dynamic range 映射到 display range；
- Gamma 是之后的显示/感知编码。

输入：

- linear RGB 或 single-channel float；
- 非负；
- 允许大于 1。

输出：

- float `[0,1]`；
- shape 与 channel count 不变。

## 3. 算法

### 3.1 百分位曝光（Percentile Exposure）

```text
exposure = target / percentile(Y, p)
Y = 0.2126R + 0.7152G + 0.0722B
```

使用高亮 percentile，而不是单个最大值，可以避免极端 hot pixel 或小高光完全控制
整图曝光。

### 3.2 Reinhard 曲线

```text
f(x) = x / (1+x)
```

特点：

- simple；
- monotonic；
- smooth highlight compression；
- exposure 不合适时容易显灰。

手算：

```text
f(0)=0
f(1)=0.5
f(4)=0.8
```

### 3.3 Filmic 曲线

使用 Hable-style curve：

```text
f_raw(x) = ((x(Ax+CB)+DE) / (x(Ax+B)+DF)) - E/F
f(x) = clamp(f_raw(x) / f_raw(11.2), 0, 1)
```

Filmic 的 highlight shoulder 比简单 clipping 或 Reinhard 更柔和。

### 3.4 S-Curve 曲线

```text
s(x) = 1 / (1 + exp(-contrast*(x-midpoint)))
f(x) = (s(x)-s(0)) / (s(1)-s(0))
```

端点 normalization 让 black/white 回到 0/1。S-curve 能增强 mid-tone contrast，
但也更容易 clipping、banding，而且每像素 `exp` 成本高。

### 3.5 RGB 与 Luminance-Preserving

Per-channel：

```text
R' = f(exposure*R)
G' = f(exposure*G)
B' = f(exposure*B)
```

Luminance-preserving：

```text
Y = luma(R,G,B)
Y' = f(exposure*Y)
scale = Y' / max(Y,eps)
RGB' = RGB * scale
```

对 `RGB=[2,1,0.5]` 做 per-channel Reinhard 约得到：

```text
[0.667, 0.500, 0.333]
```

原始通道比例改变。luminance-preserving 对 RGB 乘同一 scale，在未触发 clamp 时
更能保持 hue ratio。

## 4. 实现

新增：

- `include/cpp_isp/tone_mapping.hpp`
- `src/tone_mapping.cpp`
- `tests/test_tone_mapping.cpp`
- `tools/run_tone_mapping.cpp`
- `benchmarks/bench_tone_mapping.cpp`
- `python_ref/tone_mapping_ref.py`
- `python_ref/run_week5_tone_mapping.py`

| 数学步骤 | C++ 函数 | 易错点 |
|---|---|---|
| curve | `apply_tone_curve` | Filmic constants、white point、S-curve normalization |
| percentile | `compute_percentile_exposure` | rank rounding、luma/RGB sample |
| luma preserve | `tone_map` | epsilon、common scale、final clamp |
| gamma | `apply_gamma` | `1/gamma`，且必须在 TM 之后 |

本周先保持 float-only；LUT/fixed-point 放到 Week 6。

## 5. 数据与可视化

synthetic HDR-like scene 包含：

- smooth color gradient；
- sun-like highlight；
- bright window region；
- shadow patch；
- low-amplitude texture。

这种 scene 保留大于 1 的 linear value，比普通 clipped PNG 更适合观察 dynamic-range
compression。

![Tone curves](figures/week5/week5_tone_curves.png)

![Tone mapping comparison](figures/week5/week5_tone_mapping_comparison.png)

![Luminance histograms](figures/week5/week5_luminance_histograms.png)

## 6. 测试

CTest 覆盖：

- curve monotonicity；
- Reinhard known value；
- percentile exposure；
- luminance-preserving RGB ratio；
- gamma correction。

早期结果：

```text
100% tests passed
0 tests failed out of 6
```

## 7. Python-C++ 对齐

Python 写 CPF32 input 与 golden reference；C++ 运行同一 curve，再由
`compare_with_reference` 比较。

| Curve | Mode | 最大绝对误差 | PSNR | Failed |
|---|---|---:|---:|---:|
| Reinhard | RGB | 5.96e-8 | 161.30 dB | 0 / 184320 |
| Reinhard | luma | 1.79e-7 | 158.04 dB | 0 / 184320 |
| Filmic | luma | 1.79e-7 | 154.29 dB | 0 / 184320 |
| S-curve | luma | 2.98e-7 | 155.78 dB | 0 / 184320 |

差异主要来自 float math、`exp` implementation 和 arithmetic order。

## 8. ROI 指标

| 方法 | Highlight mean | Shadow mean | Clip fraction |
|---|---:|---:|---:|
| linear clipped | 0.7548 | 0.1679 | 0.0129 |
| Reinhard RGB | 0.4310 | 0.1420 | 0.0000 |
| Reinhard luma | 0.4358 | 0.1436 | 0.0000 |
| Filmic luma | 0.2513 | 0.0628 | 0.0000 |
| S-curve luma | 0.8063 | 0.0499 | 0.0151 |

解释：

- Reinhard 消除 clipping，但强烈压缩高光；
- Filmic 在当前 exposure 下更暗、更保守；
- S-curve 提升对比，但可能把高光推近 saturation。

## 9. 性能测试

以下为 legacy C++ Release benchmark：

| Curve | Mode | 尺寸 | 耗时 |
|---|---|---:|---:|
| Reinhard | RGB | 1920×1080 | 66.004 ms |
| Reinhard | luma | 1920×1080 | 46.936 ms |
| Filmic | luma | 1920×1080 | 61.000 ms |
| S-curve | luma | 1920×1080 | 330.219 ms |
| Reinhard | RGB | 3840×2160 | 259.933 ms |
| Reinhard | luma | 3840×2160 | 190.576 ms |
| Filmic | luma | 3840×2160 | 247.998 ms |
| S-curve | luma | 3840×2160 | 1307.219 ms |

观察：

- Global TM 是 per-pixel operator，比 bilateral denoise 便宜；
- S-curve 因 `exp` 明显更慢；
- Week 6 使用 LUT 替换 curve evaluation。

绝对时间来自早期 benchmark。正式引用当前平台 latency 前，应使用 warmup+median
harness 重跑。

## 10. 资料与边界

本周已实现：

- Reinhard、Filmic、S-curve；
- percentile exposure；
- luminance-preserving RGB；
- Python-C++ alignment；
- 1080P/4K benchmark。

延伸阅读：

- Reinhard photographic tone reproduction；
- Hable Filmic；
- Gamma correction；
- ACES-style filmic approximation。

## 11. 限制

- 本周尚未加入 LUT/fixed-point；
- 没有 Local TM；
- 没有 color appearance model 或 display calibration；
- synthetic scene 不能替代 calibrated HDR data；
- S-curve 假设 normalized input，激进 exposure 可能 clipping。

## 12. 面试复述

> Week 5 实现了 Reinhard、Filmic、S-curve、percentile exposure 和
> luminance-preserving mapping。Python-C++ 最大误差低于 `3e-7`。我同时分析
> highlight、shadow、clip fraction 与 1080P/4K latency。Tone Mapping 负责动态
> 范围压缩，Gamma 负责显示编码；S-curve 的 `exp` 成本推动 Week 6 LUT 实现。

## 13. 故障注入

1. 把 luma-preserving 改成 per-channel，观察高饱和颜色 hue ratio；
2. 去掉 S-curve endpoint normalization，检查 black/white；
3. 交换 Gamma 与 Tone Mapping 顺序；
4. percentile 从 99 改为 50，预测 exposure；
5. 对高光只做 clamp，与 Reinhard smooth shoulder 比较。

## 14. 章末自测

1. Tone Mapping 与 Gamma 分别解决什么问题？
2. Percentile exposure 为什么比最大值稳健？
3. Per-channel mapping 为什么可能改变 hue？
4. Filmic white-point normalization 有什么作用？
5. 为什么 alignment PSNR 很高不能证明审美更好？

## 15. Tone 参数与面试答案

| 关键词/参数 | 定义 | 调节方向/风险 | 验证方式 |
|---|---|---|---|
| percentile exposure | 用亮度百分位确定缩放白点 | percentile 越低通常主体更亮、高光更易压平 | 曲线 + p50/p99 + highlight ROI |
| Reinhard key/white | 中灰曝光与高光肩部控制 | key 提亮主体；white 改高光压缩起点 | synthetic ramp 和 HDR-like patch |
| Filmic shoulder/toe | 高光肩部 / 暗部趾部形状 | 过强会丢局部反差或压黑 | 灰阶单调性、暗/亮 ROI |
| luma-preserving | 按亮度求比例并同尺度缩放 RGB | 比 per-channel 更保 hue | 饱和色 patch 和 `Y≈0` 除零保护 |
| epsilon | 防止亮度比值除零的小正数 | 太大可能影响极暗值，太小可能数值不稳 | 全黑、近黑和有限性测试 |
| monotonicity | 输入亮度增加时输出不应反向下降 | 防止 contour reversal | dense ramp 自动检查 |

面试回答应区分“对齐正确”和“Tone 好看”：Python/C++ 高 PSNR 只证明实现相同；审美与 IQ 需要在声明场景、显示条件和 ROI 上评价动态范围、局部反差、颜色与 artifact。

## 16. 本周数据流

```text
linear HDR-like RGB -> luminance/percentile statistics
-> Reinhard/Filmic/S-curve/global scale
-> luma-preserving RGB reconstruction -> clamp/display preview
-> Python/C++ alignment + ROI/curve evaluation
```

## 17. 从线性场景到显示结果的学习闭环

### 17.1 前后依赖、输入输出数据契约、颜色语义与 ownership

Week 4 的输出仍是线性、可能带噪的图像；本周开始把 scene-referred 值映射到 bounded
display-referred 值。输入是 planar `float32`，允许大于 1；`tone_map` 输出 `[0,1]`，
`apply_gamma` 再做显示编码。两者使用 caller-owned output view，不应把 gamma 后的
数据重新当作线性输入送入 denoise、曝光统计或 HDR merge。

本周 luminance 系数假设输入可按项目的 RGB 语义计算亮度；没有相机到标准色彩空间的
校准，因此它是教学合同，不是经色度学标定的产品颜色管线。

### 17.2 从零运行和阅读路径

```powershell
python .\stage3_cpp_isp\python_ref\run_week5_tone_mapping.py
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
.\stage3_cpp_isp\out\build\verify\bench_tone_mapping.exe
```

正常产物包括 curve、直方图、视觉对比、ROI metrics、Python-C++ alignment CSV 和
benchmark CSV。阅读顺序是：`tone_mapping_ref.py` 理解曲线；主脚本确认 99th percentile
到 target 1.0 的曝光选择；`tone_mapping.hpp/.cpp` 对照 API；测试检查单调性和 known
value；最后才解释图与性能。

### 17.3 参数、公式耦合和失败现象

| 参数 | 单位/范围 | 作用与耦合 | 错误现象 |
|---|---|---|---|
| percentile `p` | `[0,100] %` | 与 target 共同决定 exposure；低 p 往往提亮更多 | 主体亮但高光被强压或 clip |
| target | tone 前线性目标 | target/p-value 得 exposure | 近零 percentile 会导致极端 gain |
| exposure | 无量纲乘法 | 决定曲线工作区，而非曲线本身 | 太低灰暗，太高丢高光层次 |
| S-curve midpoint | normalized value | 中间调转折位置 | 放错域会把对比增强到错误亮度 |
| contrast | 正数 | 增大斜率，也加剧 saturation/banding | 两端压平、局部跳变明显 |
| gamma | 正数，本实验 2.2 | 使用 `x^(1/gamma)`，必须在 TM 后 | 顺序错误会改变曝光和曲线语义 |

percentile 统计、curve、preserve-luminance 和 final clamp 是相互耦合的：只调曲线名而
不固定 exposure，不能公平比较曲线。

### 17.4 Failure、评价和性能边界

- 输出全暗：先画 tone 前 `exposure*Y`，再查 percentile/target，不要先增大 gamma。
- 色相变化：比较 per-channel 与共同 luma scale，并检查最终单通道 clamp 是否破坏比例。
- 黑色 NaN：检查 `Y≈0` 的 epsilon 与非有限输入。
- 高光反转：用 dense ramp 检查 monotonicity，定位 curve 或 normalization。
- 图“好看”但 alignment 失败：审美和实现正确性是两条证据链，均不能替代对方。

性能表是 scalar 单模块 legacy 数字，S-curve 慢可与每像素 `exp` 相关联；但正式绝对
latency 必须由当前 warmup/median harness 重跑。没有 SIMD、ARM、色彩校准、真实 HDR
显示或产品 IQ 证据。

### 17.5 面试五问、跨周连接与验收

1. **概念：scene-referred 和 display-referred 是什么？** 前者描述场景相对光量，后者
   已映射到显示能力；Tone Mapping 是两者之间的非线性桥梁。
2. **原理：为何 percentile 比 max 稳健？** 少数 hot pixel/小高光不再独占曝光决定，
   但 percentile 仍需按场景验证。
3. **参数：exposure 与 gamma 能互换吗？** 不能；前者在线性域改变曲线输入，后者编码
   已映射输出，顺序和物理含义不同。
4. **调试：饱和色 hue 改变怎样定位？** 对比 RGB ratio、luminance scale 与各通道 clamp，
   看第一个破坏共同 scale 的步骤。
5. **系统：为什么要在 Week 6 做 LUT？** 曲线逐像素执行，尤其 S-curve `exp` 昂贵；
   LUT 用可控量化误差换计算成本，但必须单独验证 banding。

本周证据为 `verified_synthetic` 的算法、对齐与 legacy 性能。学习者应能：

- [ ] 画出 linear→exposure→curve→gamma 的顺序并解释不可交换性；
- [ ] 手算 Reinhard 和一组 luminance-preserving RGB；
- [ ] 固定 exposure 比较三条曲线的 ROI 与 clip fraction；
- [ ] 注入 gamma 顺序、percentile 和 epsilon 故障并定位；
- [ ] 把 float curve 作为 Week 6 LUT approximation 的独立 golden。
