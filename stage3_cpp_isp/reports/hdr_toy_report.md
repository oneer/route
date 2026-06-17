# HDR Toy Merge Report

## 1. Background and Problem Definition

Stage 3 implements an aligned two-exposure HDR toy merge. The goal is to
understand the relationship between exposure fusion, radiance reconstruction,
and Tone Mapping without building a full commercial HDR+ burst pipeline.

This stage intentionally excludes motion alignment, optical flow, ghost removal,
and multi-frame burst selection.

## 2. Input, Output, Range

Inputs:

- short exposure CPF32 image
- long exposure CPF32 image
- same width, height, channels, and alignment
- float32 linear values
- reference exposures: short `0.18`, long `0.72`

Output:

- merged linear HDR-like CPF32 image
- values may exceed `[0, 1]`
- usually followed by global or local Tone Mapping

## 3. Algorithm

For each pixel, Stage 3 computes quality weights:

```text
short_quality = underexposure_weight(max(short_rgb))
long_quality  = saturation_weight(max(long_rgb))
short_radiance = short / short_exposure
long_radiance  = long / long_exposure
merged = (short_quality * short_radiance + long_quality * long_radiance)
         / (short_quality + long_quality + eps)
```

Short exposure protects highlights; long exposure keeps better shadow signal.
The quality weights avoid trusting saturated long-exposure highlights or
underexposed short-exposure shadows.

## 4. Implementation Details

Main files:

- `python_ref/hdr_merge_ref.py`
- `python_ref/run_week7_ltm_hdr_toy.py`
- `src/hdr_merge.cpp`
- `include/cpp_isp/hdr_merge.hpp`
- `tests/test_hdr_merge.cpp`
- `tools/run_hdr_merge.cpp`
- `tools/run_pipeline.cpp`

The HDR merge is also available through the reusable `pipeline.hpp` API, so the
integrated pipeline can call HDR merge before denoise and Tone Mapping.

## 5. Test Method

Tests cover:

- weight function behavior
- matching shapes
- invalid parameter rejection
- simple short/long merge behavior
- Python-C++ alignment on a synthetic HDR-like fixture

The independent Python reference in `hdr_merge_ref.py` can regenerate aligned
CPF32 references and preview images.

## 6. Alignment and Error Analysis

Representative result from `alignment_report.md`:

| Module | Case | Max abs error | PSNR | Failed values |
|---|---|---:|---:|---:|
| HDR merge | aligned short/long | 4.77e-7 | 137.64 dB | 0 / 73728 |

Expected error sources:

- float32 vs Python temporary precision
- max-channel quality weight matching
- exposure parameter mismatch
- saturation/underexposure threshold mismatch

## 7. Visual Results

Key figures:

- `reports/figures/week7/week7_short_exposure.png`
- `reports/figures/week7/week7_long_exposure.png`
- `reports/figures/week7/week7_hdr_merge_pipeline.png`
- `reports/figures/week8/week8_pipeline_hdr_local.png`

The short exposure retains highlight structure, while the long exposure contains
stronger shadow signal. The merged output still needs Tone Mapping because its
linear dynamic range is wider than a normal display range.

## 8. Performance Data

HDR merge itself is a simple per-pixel weighted blend. In the integrated Week 8
small scene, `HDR merge + local TM` took about `126.64 ms`, and the local tone
mapping base estimation dominates that number.

For production, HDR merge cost is usually not the only concern; alignment,
motion handling, and ghost rejection are harder.

## 9. Limitations

- Assumes perfect exposure alignment.
- No moving objects or ghost handling.
- Uses max-channel saturation/underexposure heuristics.
- Does not estimate a camera response function.
- Uses synthetic exposure pairs rather than calibrated RAW brackets.

## 10. Interview Recap

> I implemented a simplified aligned dual-exposure HDR merge. Short exposure is
> trusted more in highlights, long exposure is trusted more in shadows, and the
> merged linear result is passed into Tone Mapping for display. I explicitly
> limited Stage 3 to aligned toy HDR and can explain why motion alignment and
> ghost removal are separate production problems.
