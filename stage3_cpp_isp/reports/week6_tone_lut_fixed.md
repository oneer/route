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

## 16. LUT/定点参数与面试答案

| 关键词/参数 | 定义 | 误差来源 | 验证方式 |
|---|---|---|---|
| LUT size | 曲线采样点数量 | 输入量化与插值误差 | 以 dense ramp 扫 max error/banding |
| nearest/linear | 最近点查表 / 相邻点线性插值 | nearest 更快但阶梯明显，linear 多算术 | 同尺寸 LUT 的质量/速度消融 |
| Qm.n | 固定总位宽中整数/小数位分配 | range 与精度互相制约 | 最小/最大/半 LSB 手算 |
| round/truncate | 舍入到最近值 / 直接截断 | truncate 产生系统负 bias | 误差均值、灰阶 ramp 和单元测试 |
| saturate/clamp | 超范围时限制到合法端点 | 避免 wrap-around | 全 0/全 1/越界输入 |
| accumulator width | 乘加中间值位宽 | 太窄会溢出，即使输出位宽足够 | 最坏值上界推导 + 测试 |

面试题“为何完全对齐仍有 banding”：对齐只说明 Python 与 C++ 实现同一量化；banding 是离散表示本身的视觉误差，需要更大 LUT、插值、dither 或重新分配位宽解决。

## 17. 从 float golden 到量化部署思维

### 17.1 前后依赖、输入输出数据契约、数据流与内存合同

Week 5 的 float curve 是独立 golden；本周先在构造 `ToneCurveLut` 时分配并冻结表，
运行时对 caller-owned planar input/output 做量化、查表、反量化。输出虽然是
`float32`，有效值已受 output code 限制，不能据此声称完成了整数硬件 kernel。

```text
Week 5 float curve
  ├─ dense ramp -> approximation error / monotonicity
  └─ same LUT semantics in Python and C++ -> implementation alignment
linear input -> exposure -> index round+clamp -> lookup -> dequantize
-> optional luma RGB reconstruction -> quality/banding/latency
```

表生命周期应覆盖所有 apply 调用；input/output view 的 storage 仍由调用者持有。当前
没有无锁热更新、硬件寄存器编程、DMA 或端侧 table upload 证据。

### 17.2 从零运行与代码导航

```powershell
python .\stage3_cpp_isp\python_ref\run_week6_tone_lut_fixed.py
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
.\stage3_cpp_isp\out\build\verify\bench_tone_lut.exe
```

先读 `tone_lut.hpp` 的 `ToneLutParams`，再读 `tone_lut.cpp` 的构表、index、saturate；
`fixed_point.cpp` 只提供 Q arithmetic helper；主脚本分别生成 dense curve error、shadow
banding、Python/C++ alignment。`test_tone_lut.cpp` 和 `test_fixed_point.cpp` 用于验证端点、
round、saturate 和 odd shape。

### 17.3 参数空间和误差预算

| 参数 | 控制什么 | 增大/改变后的趋势 | 必查边界 |
|---|---|---|---|
| `input_bits` | index 数量 `2^b` | 量化步长减小，table memory 指数增加 | 0、半 step、`input_max` |
| `output_bits` | 可表示输出 code | banding 风险降低，输出/硬件位宽增加 | 最小/最大/相邻 code |
| `input_max` | LUT 线性 domain 上限 | 大 domain 覆盖高光但同 bits 下步长变粗 | 超上限 clamp 比例 |
| lookup rule | nearest 或未来 interpolation | linear 可减小误差但增加计算 | Python/C++ 必须同 round rule |
| Q `m.n` | 整数 range 与小数精度 | 整数位和小数位在固定位宽下竞争 | 最坏乘加与 accumulator |

最小误差预算至少拆成 `input quantization + curve sampling + output quantization + float
reconstruction`；若走 luma-preserving，还要加 division、epsilon 和 RGB clamp。只报告一个
总 PSNR 无法知道该增加哪一类位宽。

### 17.4 Failure、trade-off 与 benchmark 边界

- 均值误差长期为负：优先检查 truncate 代替 round；
- 只有 `input_max` 附近失败：检查最高 index clamp 与 float-to-code 舍入；
- 高光大片同值：domain 太小或 exposure 过高，implementation alignment 仍可能通过；
- 暗部台阶：查看 output bits、lookup step 与 gamma 后放大，不要用 blur 掩盖根因；
- LUT 比 float 更慢：曲线本身便宜、表访问/转换成本占主导或 benchmark scope 不同。

LUT 对 S-curve 获益大不等于所有 tone curve 都应查表。质量、表内存、启动构表时间和
steady-state latency 要分开报告。本周无 interpolation、dither、SIMD、ARM/ISP block
实测；性能表中的 legacy 绝对时间必须按当前工具链重跑。

### 17.5 面试五问、证据与学习验收

1. **概念：input bits 与 output bits 分别量化什么？** 前者决定采样哪个表项，后者决定
   表项值的离散精度。
2. **原理：为什么 Q 乘法要更宽 accumulator？** 两个整数乘积位数相加，round-shift 前
   中间值范围大于目标 Q 格式。
3. **参数：固定 12 bits 时 input_max 变大有什么代价？** 覆盖范围增加但步长变粗，
   暗部/中间调采样精度下降。
4. **调试：Python/C++ 对齐但画面 banding 怎么办？** 先测 float-vs-LUT；增加 bits、
   interpolation/dither 或非均匀采样，而不是调 alignment tolerance。
5. **系统：LUT 何时不值得？** 原公式便宜、表访问受限、构表/更新频繁或精度成本超过
   算力收益时；必须以目标平台测量。

证据为 `verified_synthetic` 的 float-vs-LUT、Python-C++ 和 legacy benchmark；不代表
硬件 fixed-point pipeline。完成标准：

- [ ] 手算 10→8 bit 的 index/code/反量化；
- [ ] 分开画 implementation error 和 approximation error；
- [ ] sweep input/output bits 并解释内存、banding和 latency；
- [ ] 注入 truncate、漏 clamp、错误 domain 并定位；
- [ ] 说明 Week 7 为什么仍可能复用 float curve，而不是所有模块强制 LUT。
