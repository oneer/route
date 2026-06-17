# Week 6: Tone Curve LUT and Fixed-Point Helpers

## 1. Learning Goal

Week 6 turns the Week 5 float tone mapping curves into a deployment-oriented
approximation path. The goal is not to invent a new tone style. The goal is to
understand how ISP firmware or hardware can replace expensive curve evaluation
with quantized lookup tables while keeping the error measurable.

Implemented path:

```text
linear RGB / HDR-like input
-> percentile exposure from Week 5
-> float reference tone curve
-> input quantization to 10 / 12 / 14 bit LUT index
-> output quantization to 8 / 10 / 12 / 16 bit code
-> optional luminance-preserving RGB reconstruction
-> Python-C++ alignment, error analysis, banding check, benchmark
```

## 2. Background and Problem Definition

Global tone mapping curves are nonlinear. Reinhard and filmic curves use several
floating point operations per pixel, and S-curve uses `exp`. On large frames,
especially 4K, this can be expensive. A LUT replaces:

```text
y = f(x)
```

with:

```text
code_in  = round(clamp(x, 0, input_max) / input_max * (2^input_bits - 1))
code_out = LUT[code_in]
y        = code_out / (2^output_bits - 1)
```

The engineering question becomes:

- how many input bits are enough
- how many output bits avoid obvious banding
- how much speed is gained
- where quantization error is visible

## 3. Input and Output Definition

Input:

- float32 planar image using the project `ImageBuffer<float>` layout
- linear RGB or single-channel signal
- values are non-negative and may exceed 1 before tone mapping
- LUT domain is `[0, input_max]`, set to `8.0` for HDR-like Week 5 scenes

Output:

- float32 image in `[0, 1]`
- values represent quantized LUT output converted back to normalized float
- optional luminance-preserving mode maps `Y` through the LUT and rescales RGB

## 4. Implementation

New C++ files:

- `include/cpp_isp/fixed_point.hpp`
- `src/fixed_point.cpp`
- `include/cpp_isp/tone_lut.hpp`
- `src/tone_lut.cpp`
- `tests/test_fixed_point.cpp`
- `tests/test_tone_lut.cpp`
- `tools/run_tone_lut.cpp`
- `benchmarks/bench_tone_lut.cpp`

New Python file:

- `python_ref/run_week6_tone_lut_fixed.py`

The fixed-point helper includes:

- `float_to_fixed`
- `fixed_to_float`
- `round_shift`
- `max_value_for_bits`
- `saturate_to_bits`

The LUT class caches `input_max_code`, `output_max_code`, and scale factors so
the per-pixel hot path stays small:

```text
clamped = clamp(value, 0, input_max)
code    = uint32(clamped * input_scale + 0.5)
output  = lut[min(code, input_max_code)] * output_inv_scale
```

This matters: the first implementation used heavier per-pixel helper calls and
was slower than the float path. After caching constants and simplifying index
generation, the S-curve LUT path became much faster than evaluating `exp` per
pixel.

## 5. Test Method

CTest covers:

- fixed-point round-trip
- signed `round_shift`
- unsigned saturation to bit depth
- invalid fixed-point parameters
- LUT size and known Reinhard values
- LUT input-domain clamping
- float vs LUT tone mapping error on odd-sized RGB input
- invalid LUT parameters

Result:

```text
100% tests passed, 0 tests failed out of 8
```

## 6. Python-C++ Alignment

The Python script writes a CPF32 HDR-like input and Python LUT outputs. C++
`run_tone_lut` runs the same LUT configuration and writes CPF32 outputs.
Alignment is checked with `compare_with_reference`.

| curve | mode | input bits | output bits | max abs error | PSNR | failed values |
|---|---|---:|---:|---:|---:|---:|
| Reinhard | luma | 10 | 10 | 1.19e-7 | 158.01 dB | 0 / 184320 |
| Reinhard | luma | 12 | 12 | 1.79e-7 | 157.70 dB | 0 / 184320 |
| Filmic | luma | 12 | 12 | 8.94e-8 | 163.59 dB | 0 / 184320 |
| S-curve | luma | 12 | 12 | 1.79e-7 | 158.67 dB | 0 / 184320 |

These are implementation alignment errors, not float-vs-LUT approximation
errors. The remaining differences are from float arithmetic order and CPF32
rounding.

## 7. LUT Size Ablation

Float curve vs LUT approximation, sampled on `[0, 8]`, output fixed at 12 bit:

| curve | input bits | max abs error | mean abs error | PSNR |
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

The S-curve is most sensitive near its steep mid-tone section. Low input bit
depth causes larger local jumps even when the average error is not large.

![LUT error curves](figures/week6/week6_lut_error_curves.png)

## 8. Banding Check

Week 6 uses a shadow gradient because banding is easiest to see where the signal
changes slowly and has few available output codes. The 8-bit LUT introduces
visible steps in the amplified error map. The 10-bit and 12-bit versions reduce
that risk.

![Shadow banding comparison](figures/week6/week6_shadow_banding_compare.png)

Example S-curve LUT result on the Week 5 HDR-like scene:

![S-curve LUT scene](figures/week6/week6_scurve_lut_scene.png)

## 9. Benchmark

C++ Release benchmark:

| method | curve | mode | size | time ms |
|---|---|---|---:|---:|
| float | Reinhard | luma | 1920x1080 | 50.117 |
| LUT 12->12 | Reinhard | luma | 1920x1080 | 47.524 |
| float | Filmic | luma | 1920x1080 | 69.585 |
| LUT 12->12 | Filmic | luma | 1920x1080 | 49.933 |
| float | S-curve | luma | 1920x1080 | 350.182 |
| LUT 12->12 | S-curve | luma | 1920x1080 | 58.136 |
| float | Reinhard | luma | 3840x2160 | 223.545 |
| LUT 12->12 | Reinhard | luma | 3840x2160 | 210.099 |
| float | Filmic | luma | 3840x2160 | 263.099 |
| LUT 12->12 | Filmic | luma | 3840x2160 | 229.784 |
| float | S-curve | luma | 3840x2160 | 1404.841 |
| LUT 12->12 | S-curve | luma | 3840x2160 | 205.724 |

Interpretation:

- LUT helps most for curves with expensive math. S-curve avoids per-pixel `exp`
  and speeds up by about 6.8x at 4K.
- Reinhard is already cheap, so LUT gives only a small gain.
- Luminance-preserving mode still needs luma computation, scale division, and
  RGB reconstruction, so the LUT is not the only cost.

## 10. Research Notes

Implemented in this project:

- uniform nearest-index tone curve LUT
- 10 / 12 / 14 bit input experiments
- quantized output code converted back to normalized float
- fixed-point helper functions
- Python-C++ LUT alignment
- banding and error visualization

Extended reading, not fully implemented this week:

- Reinhard et al., "Photographic Tone Reproduction for Digital Images" defines
  the classic photographic tone reproduction problem and relates scene dynamic
  range to display limitations:
  https://www.cs.utah.edu/docs/techreports/2002/pdf/UUCS-02-001.pdf
- John Hable's Filmic Worlds post explains several filmic tone mapping
  operators used in real-time rendering practice:
  https://filmicworlds.com/blog/filmic-tonemapping-operators/
- AMD FidelityFX LPM is a production-oriented luminance preserving mapper. It is
  useful as an advanced reference for deployment-style tone mapping, but this
  week only implements a small educational LUT path:
  https://github.com/GPUOpen-Effects/FidelityFX-LPM

## 11. Limitations

- The LUT uses nearest indexing only. Linear interpolation can reduce error at
  the cost of extra arithmetic.
- The LUT domain is manually chosen as `[0, 8]`. A production ISP would tie this
  to exposure policy and sensor bit depth.
- The output is converted back to float for project alignment. A real hardware
  path would usually keep integer codes between stages.
- No dithering is implemented, so low-bit output can show banding on smooth
  gradients.
- No SIMD or thread-level optimization is used in the LUT module yet.

## 12. Interview Recap

Useful three-year ISP algorithm engineer wording:

- "I implemented a tone curve LUT path and measured both approximation error and
  Python-C++ implementation alignment."
- "For a 12-bit input / 12-bit output LUT, the approximation error is below
  about 1.3e-4 for Reinhard and filmic on the sampled curve domain."
- "LUT speedup depends on the original curve cost. It is huge for S-curve because
  it removes per-pixel `exp`, but small for Reinhard because the float formula is
  already cheap."
- "Banding comes from insufficient output codes or steep curve slopes mapping a
  small input interval to visibly separated output levels."
- "If fixed-point and float do not align, I first check scale definition, rounding
  rule, saturation point, LUT domain, and whether the reference uses nearest or
  interpolated indexing."

## 13. Next Week

Week 7 should move from global curves to local tone mapping and HDR toy merge:

- base/detail decomposition
- halo risk analysis
- aligned short/long exposure merge
- saturation-aware weights
- HDR-like output connected back into global or local tone mapping
