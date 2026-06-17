# Stage 3 Performance Report

## Scope

This report summarizes CPU Release benchmark behavior for Stage 3 modules.
The goal is to understand bottlenecks, not to claim production-ready speed.

## Tone Mapping

| Method | Curve | Mode | Size | Time ms |
|---|---|---|---:|---:|
| float | Reinhard | luma | 1920x1080 | 50.117 |
| LUT 12->12 | Reinhard | luma | 1920x1080 | 47.524 |
| float | S-curve | luma | 1920x1080 | 350.182 |
| LUT 12->12 | S-curve | luma | 1920x1080 | 58.136 |
| float | S-curve | luma | 3840x2160 | 1404.841 |
| LUT 12->12 | S-curve | luma | 3840x2160 | 205.724 |

Interpretation:

- Reinhard is already cheap, so LUT speedup is modest.
- S-curve benefits strongly because the LUT removes per-pixel `exp`.
- Luminance-preserving mapping still pays for luma, division, and RGB scaling.

## Local Tone Mapping

| Base filter | Radius | Size | Time ms |
|---|---:|---:|---:|
| box | 5 | 640x360 | 362.176 |
| box | 9 | 640x360 | 1004.940 |
| bilateral | 3 | 640x360 | 1910.705 |
| bilateral | 5 | 640x360 | 4456.885 |
| box | 5 | 1920x1080 | 3330.083 |
| bilateral | 1 | 1920x1080 | 3016.261 |

Interpretation:

- direct local filters scale with `(2r+1)^2`
- bilateral adds range weight computation per neighbor
- naive LTM is useful for correctness and halo analysis, but needs guided
  filter, bilateral grid, pyramid, SIMD, threading, or GPU acceleration for
  deployment

## Integrated Pipeline

Small synthetic 160x96 scene:

| Case | Pipeline ms |
|---|---:|
| gaussian + global TM | 43.24 |
| gaussian + LUT TM | 25.36 |
| gaussian + local TM | 103.72 |
| HDR merge + local TM | 126.64 |

This confirms the expected shape: local base estimation dominates the small
pipeline, while LUT TM is cheaper than float global TM in this setup.

## Next Optimization Targets

- Replace direct LTM base with guided filter or bilateral grid.
- Add row/tile threading for local base estimation.
- Use tile/halo decomposition for cache-friendly local filters.
- Add SIMD or CUDA for per-pixel tone/LUT paths.
- Add interpolated LUT only if error/visual quality demands it.
