# Week 8: Pipeline Integration and Stage 3 Summary

## 1. Learning Goal

Week 8 integrates the Stage 3 modules into a single runnable pipeline and starts
the final report set:

- `run_pipeline.cpp`
- `pipeline.hpp` / `pipeline.cpp`
- `bench_pipeline.cpp`
- `dump_intermediate.cpp`
- `stage3_report.md`
- `alignment_report.md`
- `denoise_algorithm_report.md`
- `tone_mapping_algorithm_report.md`
- `hdr_toy_report.md`
- `performance_report.md`
- `stage3_interview_notes.md`

## 2. Pipeline

Single input path:

```text
input
-> denoise: none / box / gaussian
-> tone: global / local / LUT
-> gamma
-> output
```

HDR path:

```text
short + long exposure
-> aligned HDR merge
-> denoise
-> tone
-> gamma
-> output
```

The tool is intentionally command-line based and compact. A config system can be
added later, but Week 8 keeps the implementation easy to inspect. The reference
settings are recorded in `configs/default.yaml`; the C++ tools still take
explicit command-line arguments for reproducibility.

## 3. Generated Outputs

![Pipeline comparison](figures/week8/week8_pipeline_comparison.png)

Pipeline metrics:

| case | mean luma | p95 luma | clip fraction | pipeline ms |
|---|---:|---:|---:|---:|
| global | 0.4006 | 0.6240 | 0.0000 | 43.24 |
| LUT | 0.4006 | 0.6241 | 0.0000 | 25.36 |
| local | 0.4006 | 0.6241 | 0.0000 | 103.72 |
| HDR local | 0.3982 | 0.6191 | 0.0000 | 126.64 |

## 4. How to Run

```powershell
python .\stage3_cpp_isp\python_ref\run_week8_pipeline_summary.py
ctest --test-dir .\stage3_cpp_isp\build --output-on-failure
.\stage3_cpp_isp\build\bench_pipeline.exe
```

Direct pipeline example:

```powershell
.\stage3_cpp_isp\build\run_pipeline.exe single `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\week8_global.cpf32 `
  gaussian global reinhard 0.216 2.2
```

## 5. Week 8 Outcome

The project now has a coherent Stage 3 story:

- correctness: Python-C++ alignment and CTest
- algorithms: denoise, TM, LUT/fixed, LTM, HDR toy
- performance: 1080P/4K tone benchmarks, LTM bottleneck analysis, and
  integrated pipeline benchmark entry
- presentation: final report, alignment report, performance report, interview
  notes, algorithm reports, and resume bullets

## 6. Output Debugging Flow

When the final image is wrong, do not start by changing Tone Mapping parameters:

```text
source
  -> denoised
  -> tone_mapped
  -> output (gamma)
```

Run `dump_intermediate` and compare the first stage that diverges:

```powershell
.\stage3_cpp_isp\build\dump_intermediate.exe `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\debug `
  gaussian global reinhard 0.216 2.2
```

Diagnosis order:

1. `source` wrong: CPF32 shape/HWC conversion/range problem.
2. `denoised` first wrong: stride, border, radius or sigma mismatch.
3. `tone_mapped` first wrong: exposure, curve, luma-vs-RGB or LUT rounding.
4. only `output` wrong: gamma or output-range problem.
5. only image edge wrong: compare exact reflect/replicate mapping.
6. scattered NaN/Inf: stop; non-finite input is outside the current contract.

This is the reusable Stage 4 interface baseline: fixed input tensor, explicit
intermediate names, one comparator, and a first-divergence rule.

## 7. Next Step

The next stage should move toward Stage 4 deployment:

- reuse CPF32 fixtures
- port hot per-pixel modules to CUDA or another backend
- compare deployed outputs against Stage 3 CPU references
- keep performance and correctness baselines fixed
