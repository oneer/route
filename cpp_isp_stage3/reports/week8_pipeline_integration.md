# Week 8: Pipeline Integration and Stage 3 Summary

## 1. Learning Goal

Week 8 integrates the Stage 3 modules into a single runnable pipeline and starts
the final report set:

- `run_pipeline.cpp`
- `stage3_report.md`
- `alignment_report.md`
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
added later, but Week 8 keeps the implementation easy to inspect.

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
python .\cpp_isp_stage3\python_ref\run_week8_pipeline_summary.py
ctest --test-dir .\cpp_isp_stage3\build --output-on-failure
```

Direct pipeline example:

```powershell
.\cpp_isp_stage3\build\run_pipeline.exe single `
  .\cpp_isp_stage3\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\cpp_isp_stage3\data\week8_pipeline\week8_global.cpf32 `
  gaussian global reinhard 0.216 2.2
```

## 5. Week 8 Outcome

The project now has a coherent Stage 3 story:

- correctness: Python-C++ alignment and CTest
- algorithms: denoise, TM, LUT/fixed, LTM, HDR toy
- performance: 1080P/4K tone benchmarks and LTM bottleneck analysis
- presentation: final report, alignment report, performance report, interview
  notes, and resume bullets

## 6. Next Step

The next stage should move toward Stage 4 deployment:

- reuse CPF32 fixtures
- port hot per-pixel modules to CUDA or another backend
- compare deployed outputs against Stage 3 CPU references
- keep performance and correctness baselines fixed
