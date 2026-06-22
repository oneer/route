# Tone Mapping 算法专题报告

## 1. 问题背景

Tone Mapping 把 scene-referred linear value 压缩到可显示范围。阶段 3 明确区分：

- Tone Mapping：动态范围压缩；
- Gamma：显示编码或感知编码。

当前实现：

- Reinhard、Filmic、S-curve；
- RGB per-channel 与 luminance-preserving 两种应用方式；
- percentile exposure；
- Tone curve LUT approximation；
- fixed-point helper；
- banding 与 quantization error 分析。

## 2. 输入、输出与数值范围

输入是 CPF32 float，可以是 linear RGB 或单通道 linear luminance。HDR-like 场景在
压缩前允许超过 `[0,1]`。

输出仍为 CPF32 float，通常在 optional gamma 之前映射到 `[0,1]`。

## 3. 算法

### 3.1 Reinhard 曲线

```text
y = x / (1+x)
```

它单调、稳定、计算便宜，能平滑压缩高光；但 exposure 不合适时容易显得灰或对比度
不足。

### 3.2 Filmic 曲线

```text
y_raw = ((x*(a*x+c*b)+d*e) / (x*(a*x+b)+d*f)) - e/f
y = clamp(y_raw(x) / y_raw(11.2), 0, 1)
```

实现使用：

```text
a=0.15, b=0.50, c=0.10
d=0.20, e=0.02, f=0.30
white_point=11.2
```

white-point normalization 让指定白点映射到输出白端附近。

### 3.3 S-Curve 曲线

```text
s(x) = 1 / (1 + exp(-contrast*(x-midpoint)))
y = clamp((s(x)-s(0)) / max(s(1)-s(0), eps), 0, 1)
```

实现先把输入 clamp 到 `[0,1]`，再做 normalized sigmoid。若省略端点归一化，
black 会高于 0，white 会低于 1。

### 3.4 亮度保持型 Tone Mapping

```text
Y = dot(RGB, [0.2126, 0.7152, 0.0722])
Y' = tone_curve(Y * exposure)
RGB' = RGB * Y' / max(Y, eps)
```

对 `RGB=[2,1,0.5]` 分别做 per-channel Reinhard，可得约
`[0.667,0.5,0.333]`，通道比例发生变化。luminance-preserving 路径对三个通道使用
同一 scale，在未触发输出 clamp 时更能保持 hue ratio。

### 3.5 LUT 近似

LUT 把 quantized input code 映射到 output code，再转换回 normalized float。阶段 3
使用 nearest lookup，便于清楚解释误差来源。

## 4. 公式到代码的对应关系

主要文件：

- `python_ref/tone_mapping_ref.py`
- `python_ref/run_week5_tone_mapping.py`
- `python_ref/run_week6_tone_lut_fixed.py`
- `src/tone_mapping.cpp`
- `src/tone_lut.cpp`
- `src/fixed_point.cpp`
- `tests/test_tone_mapping.cpp`
- `tests/test_tone_lut.cpp`
- `tests/test_fixed_point.cpp`

| 概念 | C++ 函数 | 验证重点 |
|---|---|---|
| curve evaluation | `apply_tone_curve` | clamp、常数、white normalization |
| percentile exposure | `compute_percentile_exposure` | rank 与 luma/RGB sample |
| luma-preserving apply | `tone_map` | epsilon、common RGB scale、final clamp |
| gamma encode | `apply_gamma` | `pow(x,1/gamma)` 与执行顺序 |
| LUT approximation | `ToneCurveLut` path | domain、bits、round、saturate |

## 5. 测试方法

测试覆盖：

- curve monotonicity；
- 已知 Reinhard 数值；
- percentile exposure；
- luminance-preserving RGB ratio；
- gamma；
- invalid parameter rejection；
- LUT code range 与 output range；
- fixed-point round、shift、saturate。

| 测试 | 证明什么 |
|---|---|
| known Reinhard values | 公式与 exposure 顺序 |
| monotonic gradient | 曲线不会反转 |
| RGB ratio fixture | luma-preserving scale |
| black/white endpoint | normalized S-curve 与 clamp |
| highlight > 1 | 动态范围压缩而非简单 clipping |
| shadow gradient | LUT bit depth 与 banding |

## 6. 对齐与误差

| 模块 | Case | 最大绝对误差 | Failed |
|---|---|---:|---:|
| Global TM | Reinhard RGB | 5.96e-8 | 0 / 184320 |
| Global TM | Filmic luma | 1.79e-7 | 0 / 184320 |
| Global TM | S-curve luma | 2.98e-7 | 0 / 184320 |
| Tone LUT | Reinhard 10→10 | 1.19e-7 | 0 / 184320 |
| Tone LUT | Filmic 12→12 | 8.94e-8 | 0 / 184320 |

主要误差来源：

- NumPy temporary float64 与 C++ float32；
- `std::exp` 与 NumPy `exp`；
- LUT input/output quantization；
- nearest lookup；
- output code 转回 float。

## 7. 视觉结果

关键图片：

- `reports/figures/week5/week5_tone_curves.png`
- `reports/figures/week5/week5_tone_mapping_comparison.png`
- `reports/figures/week5/week5_luminance_histograms.png`
- `reports/figures/week6/week6_lut_error_curves.png`
- `reports/figures/week6/week6_shadow_banding_compare.png`

主要观察：

- Reinhard 简单稳定，但容易压平对比；
- Filmic 有更柔和的 highlight shoulder；
- S-curve 中间调对比更强，但对 clipping 与 banding 更敏感。

## 8. 性能

| 方法 | Curve | 尺寸 | 耗时 |
|---|---|---:|---:|
| float | S-curve luma | 1920×1080 | 350.182 ms |
| LUT 12→12 | S-curve luma | 1920×1080 | 58.136 ms |
| float | S-curve luma | 3840×2160 | 1404.841 ms |
| LUT 12→12 | S-curve luma | 3840×2160 | 205.724 ms |

LUT 对包含 expensive function 的 curve 收益最大。S-curve 可移除每像素 `exp`；
Reinhard 本身计算便宜，因此 LUT 收益较小。

这些绝对时间来自 legacy benchmark methodology。正式引用新平台 baseline 前，应使用
当前 warmup+median harness 重跑。

## 9. 已知限制

- 没有 dithering；
- LUT 使用 nearest lookup，不做 interpolation；
- fixed helper 只验证 arithmetic rule，不是完整硬件定点 kernel；
- synthetic HDR-like scene 不能替代 calibrated HDR capture；
- 没有 color appearance model 与 display calibration。

## 10. 面试复述

> 我实现了 Reinhard、Filmic 和 S-curve Tone Mapping，并支持
> luminance-preserving mapping。之后加入 LUT/fixed-point approximation，量化
> float-vs-LUT error、banding risk 和 1080P/4K 性能。核心取舍是：LUT 能移除昂贵
> 非线性计算，但会引入 quantization 与 shadow banding 风险。

## 11. 常见失败特征

- 全图过暗或过亮：exposure / percentile contract；
- 未 clipping 时仍色偏：per-channel 与 luminance mode；
- 只有端点错误：clamp 或 S-curve normalization；
- 暗部出现台阶：LUT output bit depth / rounding；
- 只有 S-curve 不对齐：`exp`、midpoint、contrast 或 dtype。

## 12. 学习练习

1. 手算 Reinhard 的 `x={0,1,4}`；
2. 计算未归一化 sigmoid 端点，解释为什么必须 normalization；
3. 在高饱和颜色上比较 per-channel 与 luma-preserving；
4. 配置错误 LUT domain，证明 implementation alignment 可以通过但画质仍错误；
5. 解释本 pipeline 为什么必须先 Tone Mapping，再 gamma。
