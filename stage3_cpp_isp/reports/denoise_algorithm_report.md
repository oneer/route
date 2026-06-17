# Denoise Algorithm Report

## 1. Background and Problem Definition

Stage 3 denoise focuses on RAW-like linear data before heavy nonlinear
processing. The goal is not to tune a pleasing image, but to implement and
verify classical denoise modules, then explain the quality and performance
tradeoffs.

The implemented scope is:

- synthetic Poisson-Gaussian noise generation in Python
- box and Gaussian baseline filters in C++
- direct bilateral filter in C++
- range-LUT bilateral approximation
- tile and row/tile-threaded bilateral variants for performance study
- small NLM Python reference for understanding only

NLM is kept as an extension concept because a direct patch-search version is too
expensive for a practical 1080P/4K CPU baseline.

## 2. Input, Output, Range

Input tensors use CPF32:

```text
width x height x channels, float32, linear range usually [0, 1]
```

Output has the same shape and dtype. Border handling is explicit; denoise tests
use replicate or reflect depending on the experiment.

## 3. Algorithms

Box filter:

```text
out(p) = mean(input(q)), q in local window
```

Gaussian filter:

```text
out(p) = sum_q G_sigma(||p-q||) input(q) / sum_q G_sigma(||p-q||)
```

Bilateral filter:

```text
out(p) = sum_q Ws(p,q) Wr(Ip-Iq) Iq / sum_q Ws(p,q) Wr(Ip-Iq)
Ws = exp(-||p-q||^2 / (2 sigma_s^2))
Wr = exp(-(Ip-Iq)^2 / (2 sigma_r^2))
```

The range-LUT version replaces repeated `exp` calls in `Wr` with a table lookup.
It is an engineering approximation, so it must be validated against the direct
float implementation.

## 4. Implementation Details

Main files:

- `python_ref/noise_model_ref.py`
- `python_ref/denoise_ref.py`
- `src/denoise_basic.cpp`
- `src/bilateral_denoise.cpp`
- `include/cpp_isp/denoise.hpp`
- `tests/test_denoise_basic.cpp`
- `tests/test_bilateral_denoise.cpp`
- `benchmarks/bench_denoise.cpp`
- `benchmarks/bench_bilateral.cpp`

The C++ implementation keeps image layout explicit through `ImageView` and
`ImageBuffer`. The bilateral performance path includes direct scalar, range-LUT,
tiled, threaded rows, and threaded tiles. The tile experiments use radius as the
logical halo dependency.

## 5. Test Method

Tests cover:

- identity and basic smoothing behavior
- constant inputs
- border access
- direct bilateral vs LUT approximation
- tile/threaded variants matching the single-image LUT output

Week 4 also writes `reports/figures/week4/week4_python_cpp_alignment.csv` to
track Python-C++ error on the bilateral fixture.

## 6. Alignment and Error Analysis

Representative alignment is stored in:

- `data/week4_alignment/week4_bilateral_python_ref.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_lut.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_tile.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_rows.cpf32`
- `data/week4_alignment/week4_bilateral_cpp_tiles.cpf32`

Expected error sources:

- float32 arithmetic order
- Python float64 temporary values
- direct `exp` vs LUT interpolation/quantization
- border policy mismatch

For denoise, visual closeness is not enough. A wrong border policy may only
affect a thin image ring but can later be amplified by sharpening or local tone
mapping.

## 7. Visual Results

Key figures:

- `reports/figures/week2/week2_noise_denoise_grid.png`
- `reports/figures/week2/week2_noise_std_curve.png`
- `reports/figures/week3/week3_bilateral_grid.png`
- `reports/figures/week3/week3_nlm_small_crop.png`
- `reports/figures/week3_sidd_real/week3_sidd_real_comparison.png`

These figures show the expected progression: simple filters suppress noise but
blur edges, bilateral keeps strong edges better, and NLM is useful for intuition
but not adopted as the main CPU implementation.

## 8. Performance Data

Main benchmark output:

- `reports/figures/week4/week4_denoise_benchmark_full.csv`
- `reports/figures/week4/week4_thread_speedup.png`
- `reports/figures/week4/week4_tile_sensitivity.png`

The performance story is:

- direct bilateral is compute-heavy because every neighbor uses range weighting
- range LUT reduces expensive math but memory access still dominates at 4K
- tile/thread speedup depends on cache locality and scheduling overhead
- more threads do not guarantee linear speedup

## 9. Limitations

- The project uses RAW-like float tensors, not a full Bayer RAW pipeline.
- No temporal denoise is implemented.
- NLM is only a Python reference crop experiment.
- No SIMD/NEON/AVX path is implemented in Stage 3.
- Texture preservation is evaluated with simple metrics and crops, not a full IQ
  lab protocol.

## 10. Interview Recap

> I implemented Gaussian and bilateral RAW-like denoise baselines in C++ and
> verified them against Python references using CPF32 tensors. The bilateral
> module uses spatial and range weights to preserve edges, and I added a
> range-LUT approximation plus tile/thread benchmarks to analyze 1080P/4K
> bottlenecks. NLM is covered as a small Python reference to explain patch
> similarity and complexity, but I did not present it as a realtime CPU module.

