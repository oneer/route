# Stage 3 Interview Notes

## 1. One-Minute Project Pitch

I built a C++ ISP algorithm engineering project around RAW-like denoise, tone
mapping, local tone mapping, and a simplified HDR merge. Each module has a
Python reference, C++17 implementation, CPF32 output alignment, CTest coverage,
visual comparison, and benchmark data. The goal was not to tune a pretty image,
but to prove algorithm correctness, quantify error, and explain performance
tradeoffs.

## 2. Denoise Talking Points

- RAW noise can be modeled as shot noise plus read noise.
- Box/Gaussian filters reduce noise but blur edges.
- Bilateral filtering adds range weights, so pixels across strong edges
  contribute less.
- NLM has stronger patch matching intuition but is too expensive as a realtime
  baseline without heavy optimization.
- Denoise quality should be judged with residual maps, edge ROIs, and metrics,
  not only final visual preference.

## 3. Tone Mapping Talking Points

- Tone Mapping maps scene-referred linear values into display-referred range.
- Gamma is a display/perceptual encoding after tone mapping.
- Reinhard is simple and monotonic but can look gray.
- Filmic has a softer shoulder for highlights.
- S-curve can increase mid-tone contrast but is sensitive to clipping and
  banding.
- Luminance-preserving TM maps Y and rescales RGB to reduce hue shifts.

## 4. LUT / Fixed-Point Talking Points

- LUT is suitable for nonlinear curves like gamma/TM because it trades expensive
  math for table lookup.
- LUT speedup depends on the original curve cost. It is large for S-curve because
  it avoids `exp`, small for Reinhard because the formula is cheap.
- Main fixed-point risks are scale mismatch, rounding policy, saturation, and
  banding.
- 12-bit LUTs were accurate enough in this project; low-bit LUTs showed visible
  shadow banding risk.

## 5. Local TM Talking Points

- Local TM decomposes luminance into base and detail.
- Compressing the base while restoring detail preserves local contrast better
  than global TM.
- Box base can create halo because it leaks across high-contrast edges.
- Bilateral base reduces halo risk through range weights, but direct bilateral is
  slow.
- Production LTM usually needs guided filters, bilateral grids, pyramids,
  threading, SIMD, or GPU.

## 6. HDR Talking Points

- HDR merge and tone mapping are different stages.
- Merge reconstructs a wider linear radiance range from exposures.
- Tone mapping maps that HDR range back to display.
- Short exposure protects highlights; long exposure keeps shadow signal.
- Long exposure should be down-weighted near saturation; short exposure should be
  down-weighted in underexposed regions.
- This project assumes aligned frames and does not solve ghosting.

## 7. C++ Engineering Talking Points

- `ImageBuffer`/`ImageView` separate ownership from view access.
- Stride and channel layout are explicit.
- Border policy is part of correctness, not an implementation detail.
- CPF32 keeps Python-C++ alignment reproducible.
- CTest catches unit behavior; visual figures catch perceptual artifacts; CSV
  metrics make the story measurable.

## 8. What I Would Improve Next

- Add config-driven pipeline execution.
- Implement faster LTM base estimation.
- Add tile/halo threading to local filters.
- Add interpolated LUT and dithering.
- Add CUDA / TensorRT / NCNN Stage 4 deployment path.
- Add motion-aware HDR merge or ghost rejection if HDR becomes a main focus.
