# Week 7: Local Tone Mapping and Aligned HDR Toy Merge

## 1. Learning Goal

Week 7 extends global tone mapping into two related topics:

- Local Tone Mapping (LTM): preserve local detail by compressing a smooth base
  layer instead of applying one global curve to the whole image.
- HDR toy merge: combine already aligned short/long exposure images into an
  HDR-like linear radiance image, then connect it back to Tone Mapping.

This week intentionally does not implement motion alignment, ghost removal, or
commercial HDR+. The goal is an interview-ready engineering baseline with clear
input/output definitions, Python-C++ alignment, tests, visual artifacts, and
performance analysis.

## 2. Background and Problem Definition

Global tone mapping maps every pixel using the same curve:

```text
Y' = f(exposure * Y)
RGB' = RGB * Y' / max(Y, eps)
```

It is simple and stable, but it can struggle when one image contains a bright
window and dark foreground. Local tone mapping estimates a low-frequency base
layer:

```text
Y = base * detail
base' = f(exposure * base)
Y' = base' * detail^detail_strength
RGB' = RGB * Y' / max(Y, eps)
```

The benefit is better local contrast control. The risk is halo: if the base
layer crosses strong edges, reconstructing detail around those edges can create
bright or dark rims.

HDR merge solves a different problem. A long exposure keeps shadows clean but
clips highlights. A short exposure protects highlights but is noisy/dark in
shadows. For an already aligned toy pair:

```text
short_radiance = short_image / short_exposure
long_radiance  = long_image  / long_exposure
HDR = weighted_average(short_radiance, long_radiance)
```

Then HDR still needs tone mapping because the merged radiance can exceed display
range.

## 3. Input and Output Definition

Local TM input:

- float32 linear RGB or single-channel image
- values may exceed 1 before display mapping
- output is float32 `[0, 1]`

HDR merge input:

- `short_image`: short exposure LDR image in `[0, 1]`
- `long_image`: long exposure LDR image in `[0, 1]`
- same width, height, channels, and alignment
- known scalar exposure times

HDR merge output:

- float32 HDR-like linear radiance
- values may exceed 1
- must be followed by global or local tone mapping for display

## 4. Algorithms

### 4.1 Base Layer

Week 7 supports two base filters:

- Box base: simple local average, fast to understand, but crosses edges and can
  create halo.
- Bilateral base: weights by spatial distance and luminance difference, reducing
  cross-edge leakage.

Box:

```text
base(p) = mean(Y(q)), q in window(p)
```

Bilateral:

```text
base(p) = sum_q Gs(||p-q||) * Gr(Y(q)-Y(p)) * Y(q)
          / sum_q Gs(||p-q||) * Gr(Y(q)-Y(p))
```

### 4.2 Local Reconstruction

```text
detail = Y / max(base, eps)
mapped_base = curve(exposure * base)
mapped_y = clamp(mapped_base * detail^detail_strength, 0, 1)
RGB_out = clamp(RGB * mapped_y / max(Y, eps), 0, 1)
```

`detail_strength < 1` damps texture and halo risk. `detail_strength = 1`
preserves detail more aggressively.

### 4.3 HDR Weights

Long exposure weight is reduced near saturation:

```text
w_long = 1, if max(long_rgb) <= saturation_threshold
w_long = (1 - max(long_rgb)) / (1 - saturation_threshold), otherwise
```

Short exposure weight is reduced in very dark regions:

```text
w_short = 1, if max(short_rgb) >= underexposure_threshold
w_short = max(short_rgb) / underexposure_threshold, otherwise
```

Merged radiance:

```text
HDR = (w_short * short / short_exposure + w_long * long / long_exposure)
      / (w_short + w_long + eps)
```

## 5. Implementation

New C++ files:

- `include/cpp_isp/local_tone_mapping.hpp`
- `src/local_tone_mapping.cpp`
- `include/cpp_isp/hdr_merge.hpp`
- `src/hdr_merge.cpp`
- `tests/test_local_tone_mapping.cpp`
- `tests/test_hdr_merge.cpp`
- `tools/run_local_tone_mapping.cpp`
- `tools/run_hdr_merge.cpp`
- `benchmarks/bench_local_tone_mapping.cpp`

New Python file:

- `python_ref/run_week7_ltm_hdr_toy.py`

The implementation reuses existing project concepts:

- `ImageBuffer<float>` and `ImageView`
- `BorderPolicy::Reflect`
- Week 5 tone curves through `apply_tone_curve`
- CPF32 for Python-C++ alignment

## 6. Test Method

CTest covers:

- constant input produces constant base layer
- LTM keeps output display-bounded and preserves highlight ordering
- bilateral base leaks less across a step edge than box base
- HDR weight helper functions
- aligned short/long merge recovers radiance when neither frame is clipped
- saturated long exposure defers to short exposure radiance

Result:

```text
100% tests passed, 0 tests failed out of 10
```

## 7. Python-C++ Alignment

Alignment uses a 192x128 HDR-like synthetic scene and CPF32 outputs.

| module | case | max abs error | PSNR | failed values |
|---|---|---:|---:|---:|
| Local TM | Reinhard bilateral | 1.79e-7 | 155.92 dB | 0 / 73728 |
| HDR merge | aligned short/long | 4.77e-7 | 137.64 dB | 0 / 73728 |

The errors are implementation differences only. They are far below a display
visible threshold and mainly come from float arithmetic order.

## 8. Visual Results

Global TM vs local TM:

![Local TM comparison](figures/week7/week7_ltm_global_comparison.png)

HDR toy pipeline:

![HDR merge pipeline](figures/week7/week7_hdr_merge_pipeline.png)

The HDR figure shows:

- short exposure: highlight-safe but dark
- long exposure: brighter shadows but clipped highlights
- short/long weight maps
- merged HDR radiance after global TM
- merged HDR radiance after local TM

## 9. ROI and Halo Observations

Selected luminance statistics:

| method | mean luma | p95 luma | clip fraction | edge-band std |
|---|---:|---:|---:|---:|
| Global | 0.1530 | 0.3632 | 0.0000 | 0.1429 |
| LTM box | 0.1535 | 0.3653 | 0.0000 | 0.1428 |
| LTM bilateral | 0.1530 | 0.3633 | 0.0000 | 0.1430 |

In this synthetic setup the LTM parameters are conservative, so the global and
local outputs stay close. This is intentional: the goal is to demonstrate a
controlled base/detail implementation before pushing aggressive local contrast.

Halo risk:

- Box base can cross strong edges, so detail reconstruction may create local
  rims near highlight boundaries.
- Bilateral base reduces cross-edge leakage, but direct bilateral is much more
  expensive.
- Increasing `detail_strength` increases local contrast and halo risk.

## 10. Benchmark

C++ Release benchmark:

| base filter | radius | size | time ms |
|---|---:|---:|---:|
| box | 5 | 640x360 | 340.577 |
| box | 9 | 640x360 | 847.893 |
| bilateral | 3 | 640x360 | 1757.533 |
| bilateral | 5 | 640x360 | 4465.713 |
| box | 5 | 1920x1080 | 3304.228 |
| bilateral | 1 | 1920x1080 | 3632.998 |

Interpretation:

- Direct LTM is expensive because every pixel visits a local window and then
  reconstructs RGB.
- Bilateral base is much slower than box base because each neighbor needs
  spatial and range weights.
- Radius has quadratic cost: `(2r + 1)^2` samples per pixel.
- This naive Week 7 implementation is correct and explainable, but not a
  production-speed LTM.

## 11. Research Notes

Implemented this week:

- base/detail local tone mapping with box and bilateral base
- halo-oriented comparison and base preview
- aligned two-exposure HDR toy merge
- saturation-aware and underexposure-aware weights
- HDR output connected back to global and local TM

Extended reading, not fully implemented:

- Durand and Dorsey, "Fast Bilateral Filtering for the Display of High-Dynamic-
  Range Images" motivates bilateral base/detail decomposition for HDR display:
  https://people.csail.mit.edu/fredo/PUBLI/Siggraph2002/
- Debevec and Malik, "Recovering High Dynamic Range Radiance Maps from
  Photographs" is the classic multi-exposure HDR radiance work:
  https://www.pauldebevec.com/Research/HDR/
- Mertens, Kautz, and Van Reeth exposure fusion explains a practical alternative
  to explicit HDR radiance reconstruction:
  https://www.tommertens.com/old-academic/exposure_fusion/index.html
- Hasinoff et al., HDR+ is useful for understanding burst HDR and mobile low
  light pipelines, but Week 7 does not reproduce burst alignment or merge:
  `stage1_soft_isp/materials/papers/Hasinoff_2016_HDRPlus_Burst_Photography.pdf`

## 12. Limitations

- HDR merge assumes perfect alignment. Moving objects would ghost.
- No camera response calibration is implemented; exposure relation is a simple
  scalar toy model.
- No noise model is used in HDR weights, so short-frame dark noise is only
  approximated by underexposure weighting.
- Local TM uses direct box/bilateral windows, so performance is not deployable at
  1080P/4K.
- No guided filter, bilateral grid, mip pyramid, or tile/halo optimized LTM is
  implemented yet.

## 13. Interview Recap

Useful three-year ISP algorithm engineer wording:

- "I implemented local tone mapping as base/detail decomposition. The base is
  compressed by a tone curve, then detail is multiplied back with a tunable
  strength."
- "Box base is easy but can create halo across high-contrast edges. Bilateral
  base reduces edge leakage using range weights, but the direct implementation is
  much slower."
- "HDR merge and tone mapping solve different problems. Merge reconstructs a
  wider linear radiance range; tone mapping maps that range back to display."
- "The toy HDR merge assumes aligned short/long frames. Long exposure is down-
  weighted near saturation, and short exposure is down-weighted in dark regions."
- "For production, I would replace direct bilateral LTM with a faster guided
  filter, bilateral grid, pyramid, or tile/halo implementation, and add ghost
  detection for moving regions."

## 14. Next Week

Week 8 should integrate the modules into a small runnable pipeline:

```text
linear / RAW-like input
-> optional denoise
-> optional HDR merge
-> global TM / local TM
-> gamma / output
```

It should also start consolidating the final reports: alignment, algorithm
summary, performance summary, and interview notes.
