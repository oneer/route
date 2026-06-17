# Stage 3 Final Report: C++ ISP Algorithm Engineering

## 1. Project Goal

Stage 3 builds a C++17 ISP algorithm engineering project around:

- RAW-like denoise
- global tone mapping
- tone curve LUT / fixed-point approximation
- local tone mapping
- aligned HDR toy merge
- Python-C++ alignment, tests, benchmarks, reports, and interview expression

The project is aimed at a three-year ISP algorithm engineer interview story:
not image testing, not pure IQ tuning, but algorithm implementation,
verification, performance analysis, and engineering tradeoff explanation.

## 2. Implemented Pipeline

The integrated Week 8 tool is:

```text
tools/run_pipeline.cpp
```

Supported single-input path:

```text
linear / RAW-like input
-> optional denoise: none / box / gaussian
-> tone: global / local / LUT
-> optional gamma
-> CPF32 output
```

Supported HDR path:

```text
short exposure + long exposure
-> aligned HDR merge
-> optional denoise
-> tone: global / local / LUT
-> optional gamma
-> CPF32 output
```

Example:

```powershell
.\stage3_cpp_isp\build\run_pipeline.exe single `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\week8_global.cpf32 `
  gaussian global reinhard 0.22 2.2
```

## 3. Module Summary

| Module | Main files | What it demonstrates |
|---|---|---|
| Image / Border / CPF32 | `image.hpp`, `border.hpp`, `cpf32.hpp` | Layout, stride, border policy, cross-language tensors |
| Denoise | `denoise.hpp`, `denoise_basic.cpp`, `bilateral_denoise.cpp` | Gaussian / box / bilateral / LUT bilateral, noise-detail tradeoff |
| Global TM | `tone_mapping.hpp`, `tone_mapping.cpp` | Reinhard, filmic, S-curve, percentile exposure, luma-preserving mapping |
| Tone LUT / Fixed | `tone_lut.hpp`, `fixed_point.hpp` | 10/12/14-bit LUT, quantization error, banding, speedup |
| Local TM | `local_tone_mapping.hpp` | base/detail decomposition, halo risk, bilateral vs box base |
| HDR toy | `hdr_merge.hpp` | aligned short/long exposure merge and HDR-to-SDR chain |
| Pipeline | `run_pipeline.cpp` | combined denoise / HDR / TM execution path |

## 4. Correctness and Tests

The project uses:

- CTest unit tests
- CPF32 Python-C++ alignment
- synthetic edge, gradient, highlight, HDR-like scenes
- visual comparison sheets and metrics CSV

Latest result:

```text
100% tests passed, 0 tests failed out of 10
```

## 5. Key Alignment Results

| Week | Module | Max abs error | Failed values |
|---|---|---:|---:|
| Week 5 | Global TM Reinhard RGB | 5.96e-8 | 0 / 184320 |
| Week 5 | Global TM Filmic luma | 1.79e-7 | 0 / 184320 |
| Week 6 | Tone LUT Filmic 12->12 | 8.94e-8 | 0 / 184320 |
| Week 7 | Local TM Reinhard bilateral | 1.79e-7 | 0 / 73728 |
| Week 7 | HDR aligned short/long merge | 4.77e-7 | 0 / 73728 |

These values show implementation alignment, not aesthetic quality. The goal is
to prove that the C++ modules match the Python reference before discussing
visual tradeoffs.

## 6. Pipeline Demonstration

Week 8 generates four integrated outputs:

- gaussian denoise + global Reinhard TM
- gaussian denoise + Reinhard LUT TM
- gaussian denoise + local Reinhard TM
- HDR merge + local Reinhard TM

![Week8 pipeline comparison](figures/week8/week8_pipeline_comparison.png)

Selected pipeline metrics on the 160x96 synthetic scene:

| case | mean luma | p95 luma | clip fraction | pipeline ms |
|---|---:|---:|---:|---:|
| global | 0.4006 | 0.6240 | 0.0000 | 43.24 |
| LUT | 0.4006 | 0.6241 | 0.0000 | 25.36 |
| local | 0.4006 | 0.6241 | 0.0000 | 103.72 |
| HDR local | 0.3982 | 0.6191 | 0.0000 | 126.64 |

## 7. Performance Summary

Tone mapping:

- 4K S-curve float luma: about `1404.841 ms`
- 4K S-curve LUT luma: about `205.724 ms`
- reason: LUT avoids per-pixel `exp`

Local tone mapping:

- box r5 1080P: about `3330 ms`
- direct bilateral r1 1080P: about `3016 ms`
- direct bilateral r5 640x360: about `4457 ms`

Conclusion: global TM and LUT TM are practical CPU baselines; naive local TM is
correct and useful for learning but not deployable without acceleration.

## 8. Known Limitations

- No real RAW Bayer pipeline is integrated into `run_pipeline`.
- HDR merge assumes perfect alignment and no moving objects.
- Local TM uses direct box/bilateral base estimation, not guided filter,
  bilateral grid, pyramid, SIMD, or multithreading.
- Tone LUT uses nearest indexing, not interpolation or dithering.
- The pipeline uses fixed command-line parameters rather than a config file.
- Stage 3 focuses on CPU C++ baselines; CUDA/TensorRT/NCNN deployment belongs to
  Stage 4.

## 9. Resume Bullets

- Built a C++17 ISP algorithm engineering project covering RAW-like denoise,
  global/local tone mapping, tone curve LUT/fixed-point approximation, and
  aligned HDR toy merge.
- Implemented Python reference to C++ alignment using a custom CPF32 tensor
  format, with unit tests for image layout, border handling, denoise, tone
  mapping, LUT, local TM, and HDR merge.
- Implemented Reinhard / filmic / S-curve tone mapping and 10/12/14-bit LUT
  approximation; measured float-vs-LUT error, banding risk, and 1080P/4K
  performance.
- Implemented base/detail local tone mapping and aligned short/long HDR merge,
  analyzed halo risk, saturation-aware weights, and HDR-to-SDR display mapping.
- Built an integrated `run_pipeline` tool supporting denoise, HDR merge, global
  TM, LUT TM, local TM, gamma output, and reproducible benchmark/report outputs.

## 10. Stage 4 Handoff

Stage 4 should reuse:

- CPF32 tensors as correctness fixtures
- C++ ImageBuffer and module API conventions
- 1080P / 4K CPU baselines
- Week 8 pipeline outputs as reference behavior

Good Stage 4 next steps:

- CUDA implementation for tone LUT and separable filters
- faster local TM via guided filter / bilateral grid
- ONNX / TensorRT / NCNN deployment bridge for learned denoise or learned ISP
- compare AI module outputs against Stage 3 deterministic baselines
