# 第 6 周：Tone Curve LUT 与 Fixed-Point

## 1. 学习目标

本周把 Week 5 float tone curve 转换为更接近部署的 approximation path。目标不是
创造新风格，而是理解 ISP firmware/hardware 如何用 quantized LUT 替代昂贵 curve
evaluation，同时让误差可测量。

```text
linear RGB / HDR-like input
-> percentile exposure
-> float reference curve
-> quantize 到 10/12/14-bit LUT index
-> quantize 到 8/10/12/16-bit output code
-> optional luminance-preserving reconstruction
-> alignment / error / banding / benchmark
```

## 2. LUT 问题定义

原始公式：

```text
y = f(x)
```

LUT 路径：

```text
code_in  = round(clamp(x,0,input_max) / input_max * (2^input_bits-1))
code_out = LUT[code_in]
y        = code_out / (2^output_bits-1)
```

需要回答：

- input bits 多少才够；
- output bits 是否会 banding；
- speedup 有多大；
- quantization error 集中在哪里。

### 2.1 10-bit → 8-bit 手算

假设 LUT domain `[0,8]`、输入 `x=2.0`：

```text
input_max_code = 1023
output_max_code = 255
index = round((2/8)*1023) = 256
```

Reinhard：

```text
curve(2) = 2/(1+2) = 0.6667
output_code = round(0.6667*255) = 170
output_float = 170/255 = 0.6667
```

输入 quantization 与输出 quantization 是两处独立误差。

### 2.2 Q 格式

Q4.12 的 scale 为 `2^12=4096`：

```text
1.5 -> round(1.5*4096) = 6144
6144/4096 = 1.5
```

两个 Q4.12 相乘，中间结果带 24 个 fraction bits，需要 round-shift 12 bit 才回到
原 scale。accumulator 位宽不足会 overflow，直接 truncate 会产生 bias。

本项目只实现 arithmetic helper，不代表整条 Tone Mapping kernel 已完成硬件定点化。

## 3. 输入输出契约

输入：

- float32 planar；
- linear RGB 或 single-channel；
- 非负；
- Tone Mapping 前允许超过 1；
- LUT domain 本实验为 `[0,8]`。

输出：

- float32 `[0,1]`；
- 实际含义是 quantized output code 再转回 normalized float；
- luminance-preserving mode 映射 Y，再重建 RGB。

## 4. 实现

新增：

- `include/cpp_isp/fixed_point.hpp`
- `src/fixed_point.cpp`
- `include/cpp_isp/tone_lut.hpp`
- `src/tone_lut.cpp`
- `tests/test_fixed_point.cpp`
- `tests/test_tone_lut.cpp`
- `tools/run_tone_lut.cpp`
- `benchmarks/bench_tone_lut.cpp`
- `python_ref/run_week6_tone_lut_fixed.py`

Fixed-point helper：

- `float_to_fixed`
- `fixed_to_float`
- `round_shift`
- `max_value_for_bits`
- `saturate_to_bits`

Hot path：

```text
clamped = clamp(value, 0, input_max)
code = uint32(clamped * input_scale + 0.5)
output = lut[min(code,input_max_code)] * output_inv_scale
```

第一版使用较重 helper，可能比 float 更慢。缓存 scale 和 max code、简化 index 后，
S-curve LUT 才明显快于每像素 `exp`。

## 5. 测试

CTest 覆盖：

- fixed-point round trip；
- signed `round_shift`；
- unsigned saturation；
- invalid parameter；
- LUT size 与 known Reinhard value；
- input-domain clamp；
- odd-size RGB float-vs-LUT；
- invalid LUT parameter。

早期结果：

```text
100% tests passed
0 tests failed out of 8
```

## 6. Python-C++ 实现对齐

| Curve | Mode | Input bits | Output bits | 最大绝对误差 | PSNR | Failed |
|---|---|---:|---:|---:|---:|---:|
| Reinhard | luma | 10 | 10 | 1.19e-7 | 158.59 dB | 0 / 184320 |
| Reinhard | luma | 12 | 12 | 1.19e-7 | 157.85 dB | 0 / 184320 |
| Filmic | luma | 12 | 12 | 8.94e-8 | 164.08 dB | 0 / 184320 |
| S-curve | luma | 12 | 12 | 2.38e-7 | 157.83 dB | 0 / 184320 |

这些是 implementation alignment error，不是 float-vs-LUT approximation error。

| 比较对象 | 回答的问题 |
|---|---|
| Python LUT vs C++ LUT | 两端是否实现相同 index/round/saturate |
| Float curve vs LUT | 查表近似损失多少精度 |

第一张表误差大，应先查实现；只有第二张表误差大，才调整 bit depth、domain 或
interpolation。

## 7. LUT 尺寸消融

Float curve 与 LUT approximation，domain `[0,8]`，output 12-bit：

| Curve | Input bits | 最大绝对误差 | 平均绝对误差 | PSNR |
|---|---:|---:|---:|---:|
| Reinhard | 8 | 1.54e-2 | 8.76e-4 | 54.66 dB |
| Reinhard | 10 | 3.89e-3 | 2.35e-4 | 66.44 dB |
| Reinhard | 12 | 1.22e-4 | 6.09e-5 | 83.06 dB |
| Filmic | 8 | 5.99e-3 | 9.02e-4 | 57.65 dB |
| Filmic | 10 | 1.59e-3 | 2.33e-4 | 69.50 dB |
| Filmic | 12 | 1.22e-4 | 6.13e-5 | 83.02 dB |
| S-curve | 8 | 3.21e-2 | 9.80e-4 | 48.32 dB |
| S-curve | 10 | 7.41e-3 | 2.44e-4 | 60.35 dB |
| S-curve | 12 | 1.22e-4 | 7.41e-6 | 92.27 dB |

S-curve 在陡峭 mid-tone 区域最敏感。低 input bits 会造成更大局部跳变。

![LUT error curves](figures/week6/week6_lut_error_curves.png)

## 8. Banding 检查

Shadow gradient 最容易暴露 banding，因为信号变化慢、可用 output code 少。

![Shadow banding comparison](figures/week6/week6_shadow_banding_compare.png)

![S-curve LUT scene](figures/week6/week6_scurve_lut_scene.png)

8-bit LUT 的 amplified error map 出现明显台阶，10/12-bit 风险降低。

## 9. 性能测试

Legacy C++ Release benchmark：

| 方法 | Curve | Mode | 尺寸 | 耗时 |
|---|---|---|---:|---:|
| float | Reinhard | luma | 1920×1080 | 50.117 ms |
| LUT 12→12 | Reinhard | luma | 1920×1080 | 47.524 ms |
| float | Filmic | luma | 1920×1080 | 69.585 ms |
| LUT 12→12 | Filmic | luma | 1920×1080 | 49.933 ms |
| float | S-curve | luma | 1920×1080 | 350.182 ms |
| LUT 12→12 | S-curve | luma | 1920×1080 | 58.136 ms |
| float | S-curve | luma | 3840×2160 | 1404.841 ms |
| LUT 12→12 | S-curve | luma | 3840×2160 | 205.724 ms |

解释：

- S-curve 4K 约 `6.8×`，因为移除每像素 `exp`；
- Reinhard 本身便宜，收益小；
- luma-preserving 仍有 luma、division、RGB reconstruction；
- LUT 不是 pipeline 唯一成本。

正式引用绝对 latency 前，应使用 warmup+median harness 重跑。

## 10. 延伸资料

已实现：

- uniform nearest-index LUT；
- 10/12/14-bit input；
- quantized output 转回 float；
- fixed-point helper；
- Python-C++ LUT alignment；
- banding/error visualization。

未完整实现：

- linear interpolation；
- non-uniform LUT；
- dithering；
- hardware integer pipeline；
- SIMD/thread optimization。

## 11. 限制

- nearest indexing；
- domain `[0,8]` 手工设定；
- output 为了对齐又转回 float；
- 无 dithering；
- 无 SIMD / thread-level optimization。

## 12. 面试复述

> 我实现了 Tone curve LUT，并分别测量 approximation error 和 Python-C++
> implementation alignment。12-bit LUT 在当前 domain 上精度较好。LUT 对 S-curve
> 收益大，因为移除 `exp`；对 Reinhard 收益小。排查 fixed-point 时优先检查 scale、
> rounding、saturation、domain 和 lookup rule。

## 13. 后续方向

Week 7 进入：

- base/detail Local TM；
- halo；
- aligned short/long HDR；
- saturation-aware weight；
- HDR output 再连接 Tone Mapping。

## 14. 故障注入

### A. Round 改为 Truncate

观察 gradient error 是否出现单向 bias。系统偏差比随机误差更容易形成 banding。

### B. 忘记最高索引 Clamp

测试：

```text
0
input_max
略小于 input_max
略大于 input_max
```

### C. Domain 选错

真实最大值为 8，却把 domain 配成 `[0,1]`。大量值会 clamp 到最后 code，高光细节
消失；但 Python-C++ LUT alignment 仍可能完全通过。

## 15. 章末自测

1. 12-bit input LUT 与 12-bit output 有什么区别？
2. nearest lookup 的 input quantization step 怎么算？
3. S-curve 为什么更容易从 LUT 获得 speedup？
4. Python/C++ 完全对齐，为什么仍可能 banding？
5. fixed-point multiply 为什么需要更宽 accumulator？
