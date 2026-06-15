# cpp_isp_stage3

C++ ISP algorithm engineering project for stage 3.

The project focuses on RAW denoise, tone mapping, local tone mapping, and a
small aligned HDR merge toy pipeline. Each module should keep the same loop:

```text
Python reference -> C++ implementation -> alignment test -> benchmark -> report
```

## Week 0 status

Week 0 builds the project skeleton and verification baseline:

- CMake project structure.
- Smoke test and smoke benchmark entry points.
- `CPF32` binary tensor format for Python/C++ alignment.
- Synthetic test vectors for small, 1080P, and 4K inputs.
- C++ output comparison tool with max error, mean error, RMSE, PSNR, and failed pixel count.
- Week 0 setup report.

## Data format

`CPF32` is a tiny project-local float32 tensor format:

```text
CPF32
<width> <height> <channels>
<raw little-endian float32 payload>
```

Values are expected to be linear normalized data in `[0, 1]` unless a later
module explicitly documents another range.

## Typical commands

Configure with the local MinGW/CMake/Ninja toolchain used on this machine:

```powershell
$env:PATH="D:\Env\QT\Tools\CMake_64\bin;D:\Env\QT\Tools\Ninja;D:\Env\MinGW32\mingw\bin;$env:PATH"
cmake -S .\cpp_isp_stage3 -B .\cpp_isp_stage3\build -G Ninja -DCMAKE_CXX_COMPILER="D:/Env/MinGW32/mingw/bin/g++.exe" -DCMAKE_BUILD_TYPE=Release
cmake --build .\cpp_isp_stage3\build
ctest --test-dir .\cpp_isp_stage3\build --output-on-failure
```

Generate Week 0 vectors:

```powershell
python .\cpp_isp_stage3\python_ref\make_test_vectors.py
```

Bridge the existing Stage 2 SIDD tiny sRGB dataset into Stage 3 reports:

```powershell
python .\cpp_isp_stage3\python_ref\run_week3_sidd_real_data.py
```

Run Week 4 denoise performance analysis after building C++ targets:

```powershell
.\cpp_isp_stage3\build\bench_denoise.exe --full | Tee-Object -FilePath .\cpp_isp_stage3\reports\figures\week4_denoise_benchmark_full.csv
python .\cpp_isp_stage3\python_ref\run_week4_denoise_performance.py
```

Compare two files:

```powershell
.\build\tools\compare_with_reference.exe reference.cpf32 output.cpf32 1e-6
```

The current verified local toolchain is Qt CMake/Ninja plus
`D:\Env\MinGW32\mingw\bin\g++.exe`.
