# stage3_cpp_isp — C++ High-Performance ISP Library

Stage 3 ports key ISP algorithms from Python reference to production-style C++17.
Every module follows the same loop:

```text
Python reference → C++ implementation → alignment test → benchmark → report
```

**Status:** Stage 3 integrated baseline done (Week 0–8).

## Project Structure

```
stage3_cpp_isp/
├── cmake/                         # CMake modules (compiler options, sanitizers)
├── configs/                       # Reproducible reference pipeline settings
│   └── default.yaml
├── include/cpp_isp/               # Public headers
│   ├── cpf32.hpp                  #   CPF32 binary tensor format I/O
│   ├── image.hpp                  #   Multi-channel image container
│   ├── border.hpp                 #   Border handling (mirror / replicate)
│   ├── fixed_point.hpp            #   Fixed-point helpers for quantized ISP paths
│   ├── denoise.hpp                #   Denoise algorithms (Gaussian, box, bilateral)
│   ├── tone_mapping.hpp           #   Global tone mapping operators
│   ├── tone_lut.hpp               #   Tone curve LUT approximation
│   ├── local_tone_mapping.hpp     #   Base/detail local tone mapping
│   ├── hdr_merge.hpp              #   Aligned short/long HDR toy merge
│   ├── pipeline.hpp               #   Reusable denoise / HDR / TM pipeline API
│   └── metrics.hpp                #   PSNR, max/mean error, RMSE
├── src/                           # Implementation
│   ├── cpf32.cpp
│   ├── image.cpp
│   ├── border.cpp
│   ├── fixed_point.cpp
│   ├── denoise_basic.cpp          #   Gaussian / box denoise
│   ├── bilateral_denoise.cpp      #   Bilateral grid & LUT-accelerated variant
│   ├── tone_mapping.cpp           #   Reinhard / Filmic / S-curve / percentile
│   ├── tone_lut.cpp               #   10/12/14-bit tone curve LUT apply
│   ├── local_tone_mapping.cpp     #   Box/bilateral base local tone mapping
│   ├── hdr_merge.cpp              #   Saturation-aware aligned HDR merge
│   ├── pipeline.cpp               #   Integrated pipeline implementation
│   └── metrics.cpp
├── tests/                         # GoogleTest alignment tests
│   ├── test_smoke.cpp
│   ├── test_image.cpp
│   ├── test_border.cpp
│   ├── test_denoise_basic.cpp
│   ├── test_bilateral_denoise.cpp
│   ├── test_tone_mapping.cpp
│   ├── test_fixed_point.cpp
│   ├── test_tone_lut.cpp
│   ├── test_local_tone_mapping.cpp
│   └── test_hdr_merge.cpp
├── benchmarks/                    # Google Benchmark performance harness
│   ├── bench_smoke.cpp
│   ├── bench_bilateral.cpp
│   ├── bench_denoise.cpp
│   ├── bench_tone_mapping.cpp
│   ├── bench_tone_lut.cpp
│   ├── bench_local_tone_mapping.cpp
│   └── bench_pipeline.cpp
├── tools/                         # Standalone utilities
│   ├── compare_with_reference.cpp #   CPF32 file diff tool (max err, RMSE, PSNR, fail count)
│   ├── run_bilateral_lut.cpp     #   Bilateral LUT precompute + apply
│   ├── run_tone_mapping.cpp      #   Tone mapping apply + save
│   ├── run_tone_lut.cpp          #   Tone LUT apply + save
│   ├── run_local_tone_mapping.cpp#   Local TM apply + save
│   ├── run_hdr_merge.cpp         #   Aligned HDR merge + save
│   ├── run_pipeline.cpp          #   Denoise / HDR / TM integrated pipeline
│   └── dump_intermediate.cpp     #   Dump source / denoised / tone / final CPF32 tensors
├── python_ref/                    # Python reference implementations
│   ├── make_test_vectors.py       #   Week 0: synthetic test vectors (small / 1080P / 4K)
│   ├── visualize_week1_layout.py  #   Week 1: image layout inspection
│   ├── noise_model_ref.py         #   Week 2: Poisson-Gaussian noise model
│   ├── run_week2_noise_denoise.py #   Week 2: noise model + basic denoise
│   ├── denoise_ref.py             #   Week 3: bilateral / small NLM reference
│   ├── hdr_merge_ref.py           #   Aligned HDR merge reference
│   ├── compare_outputs.py         #   CPF32 metrics + optional error map
│   ├── run_week3_bilateral_nlm.py #   Week 3: bilateral + NLM pipeline
│   ├── run_week3_sidd_real_data.py#   Week 3: SIDD real data bridge
│   ├── run_week4_denoise_performance.py # Week 4: denoise benchmark analysis
│   ├── tone_mapping_ref.py        #   Week 5: tone mapping reference
│   ├── run_week5_tone_mapping.py  #   Week 5: tone mapping pipeline
│   ├── run_week6_tone_lut_fixed.py#   Week 6: LUT/fixed analysis
│   ├── run_week7_ltm_hdr_toy.py  #   Week 7: LTM + HDR toy analysis
│   └── run_week8_pipeline_summary.py # Week 8: integrated pipeline summary
├── reports/                       # Weekly reports and figures
│   ├── week0_project_setup.md
│   ├── week1_image_layout.md
│   ├── week2_raw_noise_and_basic_denoise.md
│   ├── week3_bilateral_nlm_denoise.md
│   ├── week3_sidd_real_data_bridge.md
│   ├── week4_toolchain_and_baseline.md
│   ├── week4_denoise_performance.md
│   ├── week5_global_tone_mapping.md
│   ├── week6_tone_lut_fixed.md
│   ├── week7_ltm_hdr_toy.md
│   ├── week8_pipeline_integration.md
│   ├── stage3_report.md
│   ├── alignment_report.md
│   ├── denoise_algorithm_report.md
│   ├── tone_mapping_algorithm_report.md
│   ├── hdr_toy_report.md
│   ├── performance_report.md
│   ├── stage3_interview_notes.md
│   └── figures/                   #   week0/ through week7/ output figures
├── data/
│   ├── week5_alignment/           #   Week 5: Python/C++ alignment CPF32 files
│   ├── week6_alignment/           #   Week 6: LUT Python/C++ alignment CPF32 files
│   ├── week7_alignment/           #   Week 7: LTM/HDR Python-C++ alignment
│   ├── week8_pipeline/            #   Week 8: integrated pipeline CPF32 files
│   └── real_cases/sidd_tiny/      #   SIDD tiny subset for real-data testing
└── CMakeLists.txt
```

## Core Library (`include/cpp_isp/`)

| Module | Header | Description |
|---|---|---|
| CPF32 I/O | `cpf32.hpp` | Float32 binary tensor format for Python ↔ C++ alignment |
| Image | `image.hpp` | Multi-channel image container, linear `[0,1]` range |
| Border | `border.hpp` | Mirror and replicate border extensions |
| Denoise | `denoise.hpp` | Gaussian, box, bilateral, range-LUT, tile/thread variants |
| Tone Mapping | `tone_mapping.hpp` | Reinhard, Filmic (Naughty Dog), S-curve, percentile |
| Tone LUT / Fixed | `tone_lut.hpp`, `fixed_point.hpp` | Quantized tone curve LUT and fixed-point helpers |
| Local TM / HDR | `local_tone_mapping.hpp`, `hdr_merge.hpp` | Base/detail LTM and aligned short/long HDR toy merge |
| Pipeline | `pipeline.hpp` | Reusable denoise / HDR / TM / gamma execution API |
| Metrics | `metrics.hpp` | Max error, mean error, RMSE, PSNR, failed pixel count |

## Week-by-Week Status

| Week | Topic | Status | Key Deliverable |
|---|---|---|---|
| 0 | Project skeleton & verification baseline | ✅ Done | CMake + CPF32 + smoke test/bench + synthetic test vectors + `compare_with_reference` tool |
| 1 | Image layout & border handling | ✅ Done | `Image`, `Border` classes + alignment tests + layout inspection |
| 2 | RAW noise model & basic denoise | ✅ Done | Poisson-Gaussian noise model, Gaussian/box denoise, C++ implementation + alignment |
| 3 | Bilateral & NLM denoise + SIDD bridge | ✅ Done | Bilateral (direct + LUT), small Python NLM reference, SIDD real-data bridge from Stage 2 |
| 4 | Denoise performance benchmarking | ✅ Done | Toolchain baseline, full benchmark suite (small / 1080P / 4K), performance report |
| 5 | Global tone mapping | ✅ Done | Reinhard, Filmic (Naughty Dog), S-curve, percentile; CPF32 alignment; benchmark |
| 6 | Tone curve LUT / fixed-point | ✅ Done | 10/12/14-bit LUT, fixed-point helpers, float-vs-LUT error, banding check, benchmark |
| 7 | Local tone mapping / HDR toy merge | ✅ Done | Base/detail LTM, halo analysis, aligned short/long merge, HDR→TM pipeline |
| 8 | Integration and reports | ✅ Done | `pipeline.hpp`, `run_pipeline`, `bench_pipeline`, final report, algorithm reports, alignment/performance reports, interview notes |

## Data Format

`CPF32` is a project-local float32 tensor format for cross-language verification:

```text
CPF32
<width> <height> <channels>
<raw little-endian float32 payload>
```

Values are linear normalized in `[0, 1]` unless a module explicitly documents another range.

## Learning Roadmap

Each week follows a consistent engineering loop:

1. **Python reference** — Understand the algorithm, verify correctness on synthetic/test data.
2. **C++ implementation** — Port to C++17, matching the reference API and behavior.
3. **Alignment test** — Export CPF32 from both Python and C++; compare with `compare_with_reference` (max error < 1e-5).
4. **Benchmark** — Measure on small (256×256), 1080P, and 4K inputs; identify bottlenecks.
5. **Report** — Document algorithm choices, performance findings, and engineering tradeoffs.

## Build & Test

Local toolchain: Qt CMake + Ninja + MinGW32 g++.

```powershell
# Configure
$env:PATH="D:\Env\QT\Tools\CMake_64\bin;D:\Env\QT\Tools\Ninja;D:\Env\MinGW32\mingw\bin;$env:PATH"
cmake -S .\stage3_cpp_isp -B .\stage3_cpp_isp\build -G Ninja -DCMAKE_CXX_COMPILER="D:/Env/MinGW32/mingw/bin/g++.exe" -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build .\stage3_cpp_isp\build

# Run all tests
ctest --test-dir .\stage3_cpp_isp\build --output-on-failure
```

## Week-by-Week Commands

### Week 0 — Project Setup

```powershell
python .\stage3_cpp_isp\python_ref\make_test_vectors.py
.\stage3_cpp_isp\build\tools\compare_with_reference.exe reference.cpf32 output.cpf32 1e-6
```

### Week 1 — Image Layout

```powershell
python .\stage3_cpp_isp\python_ref\visualize_week1_layout.py
```

### Week 2 — Noise Model & Basic Denoise

```powershell
python .\stage3_cpp_isp\python_ref\run_week2_noise_denoise.py
```

### Week 3 — Bilateral / NLM + SIDD Bridge

```powershell
python .\stage3_cpp_isp\python_ref\run_week3_bilateral_nlm.py
python .\stage3_cpp_isp\python_ref\run_week3_sidd_real_data.py
```

### Week 4 — Denoise Performance

```powershell
.\stage3_cpp_isp\build\bench_denoise.exe --full | Tee-Object -FilePath .\stage3_cpp_isp\reports\figures\week4_denoise_benchmark_full.csv
python .\stage3_cpp_isp\python_ref\run_week4_denoise_performance.py
```

### Week 5 — Global Tone Mapping

```powershell
python .\stage3_cpp_isp\python_ref\run_week5_tone_mapping.py
.\stage3_cpp_isp\build\bench_tone_mapping.exe | Set-Content -Encoding utf8 .\stage3_cpp_isp\reports\figures\week5\week5_tone_mapping_benchmark.csv
```

### Week 6 — Tone LUT / Fixed-Point

```powershell
python .\stage3_cpp_isp\python_ref\run_week6_tone_lut_fixed.py
.\stage3_cpp_isp\build\bench_tone_lut.exe | Set-Content -Encoding utf8 .\stage3_cpp_isp\reports\figures\week6\week6_lut_tone_mapping_benchmark.csv
```

### Week 7 — Local TM / HDR Toy

```powershell
python .\stage3_cpp_isp\python_ref\run_week7_ltm_hdr_toy.py
.\stage3_cpp_isp\build\bench_local_tone_mapping.exe | Set-Content -Encoding utf8 .\stage3_cpp_isp\reports\figures\week7\week7_local_tone_mapping_benchmark.csv
```

### Week 8 — Integrated Pipeline

```powershell
python .\stage3_cpp_isp\python_ref\run_week8_pipeline_summary.py
.\stage3_cpp_isp\build\run_pipeline.exe single .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 .\stage3_cpp_isp\data\week8_pipeline\week8_global.cpf32 gaussian global reinhard 0.216 2.2
```

## Final Reports

- `reports/stage3_report.md`
- `reports/alignment_report.md`
- `reports/denoise_algorithm_report.md`
- `reports/tone_mapping_algorithm_report.md`
- `reports/hdr_toy_report.md`
- `reports/performance_report.md`
- `reports/stage3_interview_notes.md`

## License

This project is part of a personal learning portfolio. All original code is available for reference and educational use.
