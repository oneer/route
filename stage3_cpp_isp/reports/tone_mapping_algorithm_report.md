# Tone Mapping Algorithm Report

## 1. Background and Problem Definition

Tone Mapping compresses scene-referred linear values into a displayable range.
Stage 3 separates Tone Mapping from Gamma: Tone Mapping handles dynamic range
compression, while Gamma is an output encoding step.

The implemented scope is:

- global Reinhard, filmic, and S-curve operators
- RGB per-channel and luminance-preserving mapping
- percentile exposure helper
- Tone curve LUT approximation
- fixed-point helper functions
- banding and quantization error analysis

## 2. Input, Output, Range

Input is CPF32 float, usually linear RGB or single-channel linear luminance. HDR
test scenes may exceed `[0, 1]` before tone compression. Output is CPF32 float,
normally mapped to `[0, 1]` before optional gamma.

## 3. Algorithms

Reinhard:

```text
y = x / (1 + x)
```

Filmic curve:

```text
y = ((x * (a*x + c*b) + d*e) / (x * (a*x + b) + d*f)) - e/f
```

S-curve:

```text
y = 1 / (1 + exp(-contrast * (x - midpoint)))
```

Luminance-preserving mapping:

```text
Y = dot(RGB, [0.2126, 0.7152, 0.0722])
Y' = tone_curve(Y * exposure)
RGB' = RGB * Y' / max(Y, eps)
```

LUT approximation maps quantized input code to output code, then converts back
to normalized float. Stage 3 uses nearest lookup so the error source is easy to
explain.

## 4. Implementation Details

Main files:

- `python_ref/tone_mapping_ref.py`
- `python_ref/run_week5_tone_mapping.py`
- `python_ref/run_week6_tone_lut_fixed.py`
- `src/tone_mapping.cpp`
- `src/tone_lut.cpp`
- `src/fixed_point.cpp`
- `include/cpp_isp/tone_mapping.hpp`
- `include/cpp_isp/tone_lut.hpp`
- `include/cpp_isp/fixed_point.hpp`
- `tests/test_tone_mapping.cpp`
- `tests/test_tone_lut.cpp`
- `tests/test_fixed_point.cpp`
- `benchmarks/bench_tone_mapping.cpp`
- `benchmarks/bench_tone_lut.cpp`

The implementation keeps curve choice, exposure, luminance preservation, and
LUT bit depth explicit. That makes it easier to discuss precision and deployment
tradeoffs.

## 5. Test Method

Tests cover:

- monotonic tone curve behavior
- shape validation
- gamma behavior
- invalid parameter rejection
- LUT code range and float output range
- fixed-point round, shift, and saturate helpers

Python-C++ alignment is recorded for global TM and LUT variants.

## 6. Alignment and Error Analysis

Representative results from `alignment_report.md`:

| Module | Case | Max abs error | Failed values |
|---|---|---:|---:|
| Global TM | Reinhard RGB | 5.96e-8 | 0 / 184320 |
| Global TM | Filmic luma | 1.79e-7 | 0 / 184320 |
| Global TM | S-curve luma | 2.98e-7 | 0 / 184320 |
| Tone LUT | Reinhard 10->10 | 1.19e-7 | 0 / 184320 |
| Tone LUT | Filmic 12->12 | 8.94e-8 | 0 / 184320 |

Expected error sources:

- NumPy temporary float64 vs C++ float32
- `std::exp` vs NumPy `exp`
- LUT quantization
- nearest lookup rather than interpolation
- output quantization converted back to float

## 7. Visual Results

Key figures:

- `reports/figures/week5/week5_tone_curves.png`
- `reports/figures/week5/week5_tone_mapping_comparison.png`
- `reports/figures/week5/week5_luminance_histograms.png`
- `reports/figures/week6/week6_lut_error_curves.png`
- `reports/figures/week6/week6_shadow_banding_compare.png`

The visual story is that Reinhard is simple but can flatten contrast, filmic has
a softer highlight shoulder, and S-curve gives stronger midtone contrast but is
more sensitive to banding and clipping.

## 8. Performance Data

From `performance_report.md`:

| Method | Curve | Size | Time ms |
|---|---|---:|---:|
| float | S-curve luma | 1920x1080 | 350.182 |
| LUT 12->12 | S-curve luma | 1920x1080 | 58.136 |
| float | S-curve luma | 3840x2160 | 1404.841 |
| LUT 12->12 | S-curve luma | 3840x2160 | 205.724 |

LUT speedup is strongest for curves that otherwise require expensive functions
such as `exp`. Reinhard is cheaper, so LUT gives less dramatic benefit.

## 9. Limitations

- No dithering is implemented for low-bit output.
- LUT uses nearest lookup rather than interpolation.
- No hardware-specific fixed-point kernel is implemented; fixed helpers validate
  the arithmetic rules only.
- Tone Mapping is evaluated on synthetic HDR-like scenes rather than calibrated
  HDR captures.

## 10. Interview Recap

> I implemented Reinhard, filmic, and S-curve Tone Mapping in C++, including
> luminance-preserving mapping. I then built LUT/fixed-point approximations and
> quantified float-vs-LUT error, banding risk, and 1080P/4K speed. The key
> tradeoff is that LUT removes expensive nonlinear math but introduces
> quantization and possible shadow banding.

