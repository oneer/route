# Week 4: Toolchain and Baseline Benchmark

## Goal

Before optimizing denoise kernels, Week 4 first makes the C++ project buildable
and measurable on the local machine. The success criteria are:

- CMake can configure the project with a known compiler.
- Week 0-3 C++ tests pass through CTest.
- Existing smoke and bilateral benchmarks produce baseline timings.

## Local Toolchain

Verified tools:

- CMake: `D:\Env\QT\Tools\CMake_64\bin\cmake.exe`, version 3.30.5
- Ninja: `D:\Env\QT\Tools\Ninja\ninja.exe`, version 1.12.1
- C++ compiler: `D:\Env\MinGW32\mingw\bin\g++.exe`, MinGW.org GCC 9.2.0

The compiler is usable for C++17 and current tests. It appears to be a 32-bit
MinGW.org toolchain, so later large-image and SIMD performance results should
be treated as a local baseline rather than a final production x64 baseline.

## Build Commands

```powershell
$env:PATH="D:\Env\QT\Tools\CMake_64\bin;D:\Env\QT\Tools\Ninja;D:\Env\MinGW32\mingw\bin;$env:PATH"
cmake -S .\cpp_isp_stage3 -B .\cpp_isp_stage3\build -G Ninja -DCMAKE_CXX_COMPILER="D:/Env/MinGW32/mingw/bin/g++.exe" -DCMAKE_BUILD_TYPE=Release
cmake --build .\cpp_isp_stage3\build
ctest --test-dir .\cpp_isp_stage3\build --output-on-failure
```

MinGW executables were linked with `-static-libgcc -static-libstdc++` so CTest
does not depend on runtime DLL discovery through `PATH`.

## Test Result

CTest result:

```text
100% tests passed, 0 tests failed out of 5
```

Covered tests:

- `test_smoke`
- `test_image`
- `test_border`
- `test_denoise_basic`
- `test_bilateral_denoise`

## Baseline Benchmark

Smoke benchmark:

```text
values: 2073600
elapsed_ms: 3.998
```

Bilateral benchmark:

```text
size=128x128 direct_ms=42.349 lut_ms=29.895
size=256x256 direct_ms=183.247 lut_ms=121.258
```

Initial observation:

- The LUT range-weight approximation is already faster than direct `exp`.
- The 256x256 timing is roughly 4x the 128x128 timing, matching the pixel-count
  scaling expected for the same radius and implementation structure.
- This baseline is now suitable for Week 4 tile, cache, and parameter-sweep work.

## Fixes Made During Bring-up

- `ImageView<T>` now supports conversion from mutable view to const view.
- `sample_with_border` now accepts both mutable and const `ImageView` inputs.
- MinGW executable targets link libgcc/libstdc++ statically to make CTest stable.
