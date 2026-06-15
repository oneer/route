# Week 4: Denoise Performance Engineering and 4K Analysis

## 1. Learning Goal

Week 4 turns the Week 3 bilateral denoise module from an algorithm prototype
into a measurable engineering component. The goal is not to chase the fastest
possible bilateral filter, but to build a correctness-preserving optimization
loop:

```text
scalar bilateral
-> range LUT
-> tile traversal
-> row / tile parallel execution
-> Python-C++ alignment
-> 256 / 1080P / 4K benchmark
-> interview-ready performance explanation
```

## 2. Problem Definition

Input:

- Single-channel float image in `[0, 1]`.
- Replicate border.
- Radius `r = 2`, spatial sigma `1.5`, range sigma `0.08`.
- Range LUT size `512`.

Output:

- Same shape float image in `[0, 1]`.
- Each output pixel is written exactly once.

The bilateral filter is expensive because every output pixel performs a
neighborhood traversal, and each neighbor needs both spatial and range weights:

```text
out(p) = sum_q Ws(p, q) * Wr(Ip - Iq) * Iq
         / sum_q Ws(p, q) * Wr(Ip - Iq)
```

For radius 2, each pixel visits 25 neighbors. At 4K, that is about
`3840 * 2160 * 25 = 207M` neighbor samples per frame, before counting channels
or extra arithmetic.

## 3. Implementation

Added C++ APIs:

- `bilateral_filter_range_lut_tiled`
- `bilateral_filter_range_lut_threaded_rows`
- `bilateral_filter_range_lut_threaded_tiles`

The implementation keeps one shared rectangular kernel:

```text
bilateral_lut_rect(input, output, y0:y1, x0:x1)
```

The optimized variants only change the traversal schedule:

- Untiled LUT: full image rectangle.
- Tiled LUT: a sequence of tile rectangles.
- Row split: each worker owns a row band.
- Tile split: workers pull tile rectangles from an atomic counter.

Halo handling:

- No temporary tile buffer is created.
- Every tile writes only its own interior rectangle.
- Neighbor reads are still from the original full input image.
- Therefore halo is logically `radius`, and correctness is preserved by
  reading across tile boundaries.

On this MinGW.org GCC 9.2 toolchain, `std::thread` is unavailable, so the
worker launcher uses a thin Windows `_beginthreadex` wrapper. The algorithm API
is not tied to that launcher.

## 4. Unit Tests

Week 4 extends `test_bilateral_denoise` with a non-even image size:

```text
23x19 input
tile size 7x5 / 8x6
thread count 3 / 4
```

The test compares:

- LUT baseline
- tiled LUT
- row-threaded LUT
- tile-threaded LUT

Acceptance threshold:

```text
max per-pixel difference <= 1e-6
```

CTest result:

```text
100% tests passed, 0 tests failed out of 5
```

## 5. Python-C++ Alignment

The Python reference creates a `64x64` synthetic edge/texture CPF32 input and
computes the golden bilateral LUT output. C++ then runs four modes:

- `lut`
- `tile`
- `rows`
- `tiles`

Alignment summary:

| mode | max abs error | mean abs error | PSNR | failed values |
|---|---:|---:|---:|---:|
| lut | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |
| tile | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |
| rows | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |
| tiles | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |

This proves that the Week 4 traversal and threading changes do not change the
algorithm output beyond float accumulation-level error.

## 6. Benchmark Results

Toolchain:

- CMake 3.30.5
- Ninja 1.12.1
- MinGW.org GCC 9.2.0
- Release build

Full benchmark CSV:

- `reports/figures/week4/week4_denoise_benchmark_full.csv`

Key results:

| size | method | threads | time ms | speedup |
|---|---|---:|---:|---:|
| 256x256 | direct | 1 | 170.265 | 1.00 |
| 256x256 | LUT | 1 | 120.504 | 1.00 |
| 256x256 | LUT vs direct | 1 | 120.504 | 1.41 |
| 1920x1080 | LUT | 1 | 3969.032 | 1.00 |
| 1920x1080 | tile split | 8 | 683.066 | 5.81 |
| 3840x2160 | LUT | 1 | 16084.102 | 1.00 |
| 3840x2160 | tile split | 8 | 2611.992 | 6.16 |

![Thread speedup](figures/week4/week4_thread_speedup.png)

Tile-size sensitivity:

![Tile sensitivity](figures/week4/week4_tile_sensitivity.png)

## 7. Analysis

Direct `exp` vs LUT:

- On 256x256, LUT gives about `1.41x` speedup over direct range-weight `exp`.
- Max error versus direct bilateral is around `7.15e-7`, so the LUT
  approximation is effectively invisible at this configuration.

Tile traversal:

- On small `256x256` input, tiling can be slower because scheduling and loop
  overhead dominate.
- On 4K input, tile traversal gives about `1.06x` single-thread speedup for the
  tested tile sizes.
- This is a modest gain because the current kernel still reads directly from
  the full input and does not stage a tile + halo buffer into cache-local
  scratch memory.

Threading:

- On 1080P, 8-thread tile split reaches about `5.81x`.
- On 4K, 8-thread tile split reaches about `6.16x`.
- Efficiency is below ideal because of thread launch overhead, memory traffic,
  scalar arithmetic, and limited hardware scaling.
- 256x256 does not benefit from 8 threads; the workload is too small.

Row split vs tile split:

- Row split is simple and has contiguous writes.
- Tile split gives better load balancing when tiles have uneven cost or future
  algorithms add per-tile decisions.
- For this scalar bilateral kernel, both are valid; benchmark decides.

## 8. Research Notes

Implemented this week:

- Direct bilateral range LUT.
- Tile traversal with implicit halo.
- Row/tile parallel execution.
- Python-C++ alignment and 4K benchmark.

Extension reading:

- Tomasi and Manduchi introduced bilateral filtering as an edge-preserving
  combination of spatial closeness and photometric similarity.
- Durand and Dorsey's fast bilateral filtering work shows that practical fast
  bilateral implementations often approximate or restructure the direct filter
  rather than merely threading the naive loop.
- OpenCV's `parallel_for_` tutorial uses convolution to explain that each
  output pixel can be written by exactly one worker while neighboring pixels are
  read-only, which matches the safety model used here.
- Google Benchmark is still a better long-term choice for stable
  microbenchmarking; this project currently keeps a no-download fallback
  benchmark because the local environment is intentionally lightweight.

Sources:

- OpenCV parallelization tutorial: https://docs.opencv.org/4.x/dc/ddf/tutorial_how_to_use_OpenCV_parallel_for_new.html
- Google Benchmark project: https://github.com/google/benchmark
- Durand and Dorsey, Fast Bilateral Filtering: https://people.csail.mit.edu/fredo/PUBLI/Siggraph2002/DurandBilateral.pdf
- Bilateral filter overview and references: https://en.wikipedia.org/wiki/Bilateral_filter

## 9. Limitations

- Current 4K timings are from a 32-bit MinGW.org GCC 9.2 local toolchain, not a
  production x64 compiler baseline.
- The implementation is scalar; no AVX/NEON/SIMD yet.
- Tile traversal does not copy tile + halo into scratch memory.
- Thread creation happens per call; a real ISP runtime would use a persistent
  thread pool.
- Only single-channel data is benchmarked in Week 4.

## 10. Interview Recap

You can say:

> Week4 focused on denoise performance engineering. I kept the bilateral LUT
> algorithm fixed, then changed traversal and scheduling: serial full image,
> serial tile traversal, row-split threading, and tile-split threading. For
> correctness, I compared all optimized variants against the LUT baseline and
> also aligned C++ output with a Python reference CPF32 golden output. The max
> Python-C++ error was about 3.6e-7 with zero failed values under 1e-5. On this
> local MinGW build, 4K single-thread LUT took about 16.1 seconds, while
> 8-thread tile split took about 2.61 seconds, about 6.16x faster. I can explain
> why this is still not ideal: scalar math, memory traffic, thread overhead, and
> lack of SIMD/thread-pool/scratch-tile optimization.

Common follow-up answers:

- 4K bilateral is slow because each pixel visits many neighbors and computes
  data-dependent range weights.
- Tile halo is needed because output pixels near a tile boundary read neighbors
  outside the tile.
- Optimization correctness is proven by unit tests, Python-C++ alignment, and
  max-error/failed-pixel reports.
- More threads are not always faster because overhead and memory bandwidth can
  dominate, especially on small images.
