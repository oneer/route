# 去噪算法专题报告

## 1. 问题背景与实现范围

阶段 3 的去噪模块处理重度非线性处理之前的 RAW-like 线性数据。目标不是调出一张
“看起来讨喜”的图，而是实现经典去噪模块、验证 Python/C++ 一致性，并解释画质、
数值误差和性能之间的取舍。

当前实现范围：

- Python 合成 Poisson-Gaussian 噪声；
- C++ box 与 Gaussian baseline；
- C++ direct bilateral filter；
- range-LUT bilateral approximation；
- tile、row-thread 与 tile-thread bilateral 性能实验；
- 仅用于理解的小尺寸 NLM Python reference。

NLM 保留为扩展知识，因为直接 patch search 的计算量过高，不适合作为本阶段
1080P/4K CPU 主实现。

## 2. 输入、输出与数值范围

输入使用 CPF32：

```text
width × height × channels
float32
linear range 通常为 [0,1]
```

输出 shape 与 dtype 不变。邻域算法必须显式指定 border；不同实验使用 replicate
或 reflect-101。

`sigma_range` 与输入使用相同数值单位。`0.08` 只有在 normalized `[0,1]` 数据上
才有明确含义。如果输入改成 integer sensor code，应同步换算参数或先归一化数据。

## 3. 算法原理

### 3.1 Box 滤波

```text
out(p) = mean(input(q)), q ∈ local window
```

所有邻域样本权重相同。优点是简单，缺点是会跨越强边缘平均。

### 3.2 Gaussian 滤波

```text
out(p) = sum_q G_sigma(||p-q||) * input(q)
         / sum_q G_sigma(||p-q||)
```

距离中心越远，空间权重越低。它比 box 更平滑，但仍然不知道“哪个像素位于边缘
另一侧”。

### 3.3 Bilateral 滤波

```text
out(p) = sum_q Ws(p,q) * Wr(Ip-Iq) * Iq
         / sum_q Ws(p,q) * Wr(Ip-Iq)

Ws = exp(-||p-q||^2 / (2*sigma_s^2))
Wr = exp(-(Ip-Iq)^2 / (2*sigma_r^2))
```

`Ws` 控制空间距离，`Wr` 控制像素值相似度。强边缘两侧的像素差大，range weight
会快速下降，因此跨边缘平均受到抑制。

### 3.4 Range LUT 近似

direct bilateral 对每个邻域样本计算 `exp`。LUT 版本把 `Wr` 替换成查表：

```text
abs(center-neighbor)
-> quantized LUT index
-> nearest range weight
```

这是工程近似，必须同时验证：

- Python LUT 与 C++ LUT 的实现对齐；
- direct float 与 LUT 的近似误差；
- tiled/threaded LUT 与 serial LUT 的调度一致性。

## 4. 公式到代码的对应关系

主要文件：

- `python_ref/noise_model_ref.py`
- `python_ref/denoise_ref.py`
- `src/denoise_basic.cpp`
- `src/bilateral_denoise.cpp`
- `include/cpp_isp/denoise.hpp`
- `tests/test_denoise_basic.cpp`
- `tests/test_bilateral_denoise.cpp`
- `benchmarks/bench_denoise.cpp`
- `benchmarks/bench_bilateral.cpp`

| 数学步骤 | Python golden | C++ 实现 | 易不一致点 |
|---|---|---|---|
| spatial kernel | `denoise_ref.py` | `spatial_weight` | radius / sigma |
| direct range weight | NumPy `exp` | `range_weight` | float64 / float32 |
| LUT 构建 | Python LUT array | `make_range_lut` | domain / bin count |
| LUT 索引 | nearest quantized index | `lookup_range_weight` | round / clamp |
| border sample | reference index mapping | border sampler | reflect / replicate |
| 加权归一化 | numerator / denominator | bilateral pixel loop | accumulation order |
| 优化调度 | golden 无需并行 | tiled / row-thread / tile-thread | tail tile / race |

Python golden 故意保持直白。C++ 可以改变调度和近似方式，但不能偷偷改变输入契约、
border 和算法语义。

## 5. 测试设计

测试覆盖：

- identity 与基本平滑行为；
- constant input；
- border access；
- direct bilateral 与 LUT approximation；
- tiled/threaded 版本与 serial LUT 输出一致性。

Week 4 使用 `reports/figures/week4/week4_python_cpp_alignment.csv` 记录 bilateral
fixture 的跨语言误差。

| 测试向量 | 暴露的问题 |
|---|---|
| constant image | 归一化错误、亮度漂移 |
| impulse | kernel footprint 与对称性 |
| strong step edge | 跨边缘泄漏与 `sigma_range` |
| odd `23x19` | tail tile、非均匀 row split |
| `stride > width` | 错误的连续内存假设 |
| direct vs LUT | 近似误差 |
| LUT vs threaded LUT | race、漏 tile、调度错误 |

## 6. 数值对齐与误差分析

代表性文件：

- `data/week4_alignment/week4_bilateral_python_ref.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_lut.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_tile.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_rows.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_tiles.cpf32`

主要误差来源：

- float32 accumulation order；
- Python 中间 float64；
- direct `exp` 与 LUT quantization；
- border policy 不一致。

去噪不能只看视觉相似。错误 border 可能只影响一圈像素，但后续 sharpen 或 Local
Tone Mapping 可能把这圈误差放大。

## 7. 视觉结果

关键图片：

- `reports/figures/week2/week2_noise_denoise_grid.png`
- `reports/figures/week2/week2_noise_std_curve.png`
- `reports/figures/week3/week3_bilateral_grid.png`
- `reports/figures/week3/week3_nlm_small_crop.png`
- `reports/figures/week3_sidd_real/week3_sidd_real_comparison.png`

整体趋势：

- 简单滤波能压低噪声，但会损失边缘；
- bilateral 对强边缘的保护更好；
- NLM 有助于理解 patch similarity，但不作为本阶段 CPU 主实现；
- SIDD bridge 输入是手机 sRGB paired data，不是真实 Bayer RAW。

## 8. 性能分析

主要输出：

- `reports/figures/week4/week4_denoise_benchmark_full.csv`
- `reports/figures/week4/week4_thread_speedup.png`
- `reports/figures/week4/week4_tile_sensitivity.png`

性能主线：

- direct bilateral 每个邻居都计算 range weight，计算量高；
- range LUT 减少 expensive math，但 4K 下仍有大量访存；
- tile/thread speedup 取决于 workload、调度开销和 memory traffic；
- 更多线程不保证线性加速。

半径为 `r` 时，scalar kernel 访问邻域样本数约为：

```text
W * H * C * (2r+1)^2
```

因此 radius 对成本近似呈二次影响。当前 tiled 路径只改变 traversal schedule，没有
把 tile+halo 搬入 cache-local scratch，所以不能把它描述成完整 cache blocking。

## 9. 已知限制

- 使用 RAW-like float tensor，不是完整 Bayer RAW pipeline；
- 没有 temporal denoise；
- NLM 只是 Python 小 crop reference；
- 没有 SIMD / NEON / AVX；
- texture preservation 使用简单指标和 crop，不是完整 IQ lab protocol；
- 当前性能数字来自本机学习环境，不能直接泛化到移动 SoC。

## 10. 面试复述

> 我实现了 Gaussian 和 bilateral RAW-like 去噪 baseline，并使用 CPF32 与 Python
> reference 做跨语言对齐。Bilateral 同时使用 spatial weight 和 range weight
> 保护边缘；随后增加 range-LUT approximation、tile traversal 和多线程调度，
> 分析 1080P/4K 下的正确性和性能。NLM 只做小尺寸 Python reference，用来解释
> patch similarity 与复杂度，没有包装成实时 CPU 实现。

## 11. 学习练习

1. 手算 `[0.20, 0.22, 0.80]` 的一个 bilateral 输出；
2. 将输入 range 乘以 1023，但保持 `sigma_range` 不变，解释结果；
3. 只修改 C++ border，根据 error map 形态定位问题；
4. 运行 odd-size threaded case，证明每个 output pixel 只写一次；
5. benchmark radius 4 之前，先预测相对 radius 2 的样本数比例。

完成标准：不依赖单个 PSNR 或 latency 数字，也能解释画质、数值误差、复杂度、
内存访问、线程限制和产品级升级方向。
