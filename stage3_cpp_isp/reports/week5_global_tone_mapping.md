# Week 5: Global Tone Mapping

## 1. Learning Goal

Week 5 builds the global tone mapping module for the Stage 3 C++ ISP project.
The goal is to understand tone mapping as dynamic-range compression, not as
manual image tuning.

Implemented path:

```text
HDR-like linear RGB input
-> percentile exposure normalization
-> Reinhard / filmic / S-curve global tone curve
-> RGB per-channel or luminance-preserving application
-> optional display gamma for visualization
-> Python-C++ alignment and benchmark
```

## 2. Background and Problem Definition

RAW or linear RGB values can represent scene-referred radiance with values far
above display range. A normal SDR display or 8-bit image expects a bounded
display-referred value, usually in `[0, 1]` before gamma encoding.

Tone mapping solves:

- highlight compression
- mid-tone contrast placement
- shadow visibility
- clipping reduction

It is different from gamma:

- Tone mapping maps scene-referred dynamic range into display-referred range.
- Gamma is a display/perceptual encoding step applied after the scene has
  already been mapped into a displayable range.

Input:

- linear RGB or single-channel float image
- values may be greater than 1
- expected non-negative range

Output:

- float image in `[0, 1]`
- same shape and channel count

## 3. Algorithms

### 3.1 Percentile Exposure

Before applying a global tone curve, Week 5 estimates an exposure scale from
the high luminance percentile:

```text
exposure = target / percentile(Y, p)
```

For RGB input:

```text
Y = 0.2126 R + 0.7152 G + 0.0722 B
```

This avoids letting a single extreme highlight define the whole exposure.

### 3.2 Reinhard Curve

```text
f(x) = x / (1 + x)
```

Properties:

- simple and monotonic
- compresses highlights smoothly
- can make images look low-contrast or gray if exposure is not chosen well

### 3.3 Filmic Curve

Week 5 uses a Hable-style filmic curve:

```text
f(x) = ((x(Ax + CB) + DE) / (x(Ax + B) + DF)) - E/F
```

The result is normalized by a white point. This gives a softer shoulder than
plain Reinhard and is useful for understanding film-like highlight roll-off.

### 3.4 S-Curve

The S-curve is applied on normalized input:

```text
f(x) = normalized sigmoid(contrast * (x - midpoint))
```

It boosts mid-tone contrast, but values near 0 or 1 can compress strongly.
Because it uses `exp`, it is also a good setup for Week 6 LUT optimization.

### 3.5 RGB vs Luminance-Preserving TM

Per-channel RGB:

```text
R' = f(exposure * R)
G' = f(exposure * G)
B' = f(exposure * B)
```

Luminance-preserving:

```text
Y  = luma(R, G, B)
Y' = f(exposure * Y)
scale = Y' / max(Y, eps)
RGB' = RGB * scale
```

Luminance-preserving tone mapping is often better for keeping hue ratios stable.

## 4. Implementation

New C++ files:

- `include/cpp_isp/tone_mapping.hpp`
- `src/tone_mapping.cpp`
- `tests/test_tone_mapping.cpp`
- `tools/run_tone_mapping.cpp`
- `benchmarks/bench_tone_mapping.cpp`

New Python files:

- `python_ref/tone_mapping_ref.py`
- `python_ref/run_week5_tone_mapping.py`

The implementation is intentionally float-only. LUT and fixed-point conversion
belong to Week 6.

## 5. Data and Visualization

Week 5 uses a synthetic HDR-like linear RGB scene with:

- smooth color gradients
- a strong sun-like highlight
- a bright window-like region
- a shadow patch
- low-amplitude texture

This synthetic scene is better than a normal clipped PNG for this week because
it preserves values greater than 1 and makes dynamic-range compression visible.

Tone curves:

![Tone curves](figures/week5/week5_tone_curves.png)

Visual comparison:

![Tone mapping comparison](figures/week5/week5_tone_mapping_comparison.png)

Luminance histogram:

![Luminance histograms](figures/week5/week5_luminance_histograms.png)

## 6. Test Method

CTest covers:

- curve monotonicity
- Reinhard known values
- percentile exposure
- luminance-preserving RGB ratio
- gamma correction

Result:

```text
100% tests passed, 0 tests failed out of 6
```

## 7. Python-C++ Alignment

The Python script writes CPF32 input and golden references. C++ `run_tone_mapping`
runs the same curves and writes CPF32 outputs. Alignment is checked with
`compare_with_reference`.

Alignment result:

| curve | mode | max abs error | PSNR | failed values |
|---|---|---:|---:|---:|
| Reinhard | RGB | 5.96e-8 | 161.30 dB | 0 / 184320 |
| Reinhard | luma | 1.79e-7 | 158.04 dB | 0 / 184320 |
| Filmic | luma | 1.79e-7 | 154.29 dB | 0 / 184320 |
| S-curve | luma | 2.98e-7 | 155.78 dB | 0 / 184320 |

The small differences come from float math and library implementations of
`exp` / arithmetic order.

## 8. ROI Metrics

Selected ROI observations:

| method | highlight mean | shadow mean | clip fraction |
|---|---:|---:|---:|
| linear clipped | 0.7548 | 0.1679 | 0.0129 |
| Reinhard RGB | 0.4310 | 0.1420 | 0.0000 |
| Reinhard luma | 0.4358 | 0.1436 | 0.0000 |
| Filmic luma | 0.2513 | 0.0628 | 0.0000 |
| S-curve luma | 0.8063 | 0.0499 | 0.0151 |

Interpretation:

- Reinhard removes clipping and compresses highlight energy strongly.
- Filmic is more conservative in this exposure setup and produces a darker
  display image.
- S-curve increases contrast but can push highlights close to saturation.

## 9. Benchmark

C++ Release benchmark:

| curve | mode | size | time ms |
|---|---|---:|---:|
| Reinhard | RGB | 1920x1080 | 66.004 |
| Reinhard | luma | 1920x1080 | 46.936 |
| Filmic | luma | 1920x1080 | 61.000 |
| S-curve | luma | 1920x1080 | 330.219 |
| Reinhard | RGB | 3840x2160 | 259.933 |
| Reinhard | luma | 3840x2160 | 190.576 |
| Filmic | luma | 3840x2160 | 247.998 |
| S-curve | luma | 3840x2160 | 1307.219 |

Performance notes:

- Global TM is much cheaper than bilateral denoise because it is per-pixel and
  has no neighborhood traversal.
- S-curve is slower because it uses `exp` per pixel.
- Week 6 should move curve evaluation into LUT/fixed-point form.

## 10. Research Notes

Implemented this week:

- Reinhard, filmic, and S-curve global curves
- percentile exposure
- luminance-preserving RGB tone mapping
- Python-C++ alignment
- 1080P / 4K benchmark

Extension reading:

- Reinhard et al. framed photographic tone reproduction around mapping scene
  luminance to display luminance while preserving photographic appearance.
- Filmic curves are common in rendering pipelines because the shoulder gives a
  more gradual highlight roll-off than simple clipping.
- Gamma correction is not a replacement for tone mapping; it is a nonlinear
  encoding/decoding operation around display response and perception.

Sources:

- Tone mapping overview: https://en.wikipedia.org/wiki/Tone_mapping
- Gamma correction overview: https://en.wikipedia.org/wiki/Gamma_correction
- Reinhard paper page: https://www.cs.utah.edu/~reinhard/cdrom/
- Hable filmic tone mapping discussion: http://filmicworlds.com/blog/filmic-tonemapping-operators/
- ACES filmic approximation discussion: https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/

## 11. Limitations

- No LUT or fixed-point approximation yet.
- No local tone mapping; global curves cannot independently recover local
  shadow and highlight detail.
- No color appearance model or display calibration.
- Synthetic HDR-like data is useful for analysis, but not a replacement for
  calibrated HDR sensor data.
- S-curve currently assumes normalized input and can clip if exposure is too
  aggressive.

## 12. Interview Recap

You can say:

> Week5 implemented global tone mapping in a C++ ISP engineering style. I
> implemented Reinhard, filmic, and S-curve tone curves, percentile exposure,
> and luminance-preserving RGB mapping. I used Python as golden reference and
> compared CPF32 outputs from C++; the max error was below 3e-7 with zero failed
> pixels under 2e-5. I also produced curve plots, HDR-like visual comparisons,
> luminance histograms, ROI metrics, and 1080P/4K benchmarks. The main lesson is
> that tone mapping solves dynamic-range compression, while gamma is a display
> encoding step. S-curve is much slower because of exp, which motivates Week6
> LUT/fixed-point implementation.

Common follow-up answers:

- Tone mapping should operate on linear scene-referred values before gamma.
- Per-channel RGB TM can shift hue; luminance-preserving TM better maintains
  channel ratios.
- Reinhard is robust but can look flat.
- Filmic has a softer shoulder and more photographic highlight roll-off.
- S-curve boosts mid-tone contrast but can saturate highlights and is expensive
  without LUT.
