# Stage 3 Alignment Report

## Method

The project uses CPF32 as a simple cross-language tensor format:

```text
CPF32
<width> <height> <channels>
<little-endian float32 HWC payload>
```

The alignment loop is:

```text
Python reference output
-> write CPF32
-> C++ tool output
-> write CPF32
-> compare_with_reference
```

Metrics:

- max absolute error
- mean absolute error
- RMSE
- PSNR
- failed values over threshold

`failed values` 的单位是 scalar value，不是 RGB pixel。NaN/Inf 不属于当前
模块契约；比较器会直接报错，不能把非有限值当作通过。

阈值来源：

- identity / integer code path：应接近 bit-exact；
- Python float vs C++ float：由 dtype、运算顺序和数学函数差异决定；
- LUT/fixed：由输入索引量化、输出 code step 和 rounding rule 决定。

`1e-5` 是当前跨语言 fixture 的验收阈值，不是所有模块都应无条件复用的常数。

## Representative Results

| Module | Case | Max abs error | PSNR | Failed values |
|---|---|---:|---:|---:|
| Global TM | Reinhard RGB | 5.96e-8 | 161.30 dB | 0 / 184320 |
| Global TM | Reinhard luma | 1.79e-7 | 158.04 dB | 0 / 184320 |
| Global TM | Filmic luma | 1.79e-7 | 154.29 dB | 0 / 184320 |
| Global TM | S-curve luma | 2.98e-7 | 155.78 dB | 0 / 184320 |
| Tone LUT | Reinhard 10->10 | 1.19e-7 | 158.01 dB | 0 / 184320 |
| Tone LUT | Filmic 12->12 | 8.94e-8 | 163.59 dB | 0 / 184320 |
| Local TM | Reinhard bilateral | 1.79e-7 | 155.92 dB | 0 / 73728 |
| HDR merge | aligned short/long | 4.77e-7 | 137.64 dB | 0 / 73728 |

## Error Sources

- float32 arithmetic order differences
- C++ `std::exp` vs NumPy `exp`
- quantized LUT code converted back to normalized float
- CPF32 write/read preserving float32, while some Python intermediate values may
  temporarily use float64

## Debug Checklist

When Python and C++ do not align:

1. Confirm tensor shape and channel layout.
2. Confirm border policy.
3. Confirm dtype and range.
4. Confirm exposure and curve parameters.
5. Confirm rounding and saturation rules.
6. Check whether reference uses nearest LUT lookup or interpolation.
7. Compare intermediate outputs, not only final RGB.
8. Reject NaN/Inf before interpreting max error or failed count.
