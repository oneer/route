# GPU device pipeline

The newly measured ORT CUDA I/O Binding row binds input and output as CUDA OrtValues and performs only the final host copy. The input is still prepared by NumPy on CPU and copied once to the device; the custom CUDA normalize output is not directly bound.

## Verified contract

- one H2D for the normalized input;
- zero intermediate D2H;
- device-bound ORT input and output;
- one final D2H for quality/output consumption.

## Measured result

- Correctness vs ORT CPU: max/mean absolute error `2.682e-07` / `2.149e-08`.
- Inference p50/p90: `3.296` / `3.754 ms`.
- Host-to-final-host e2e p50/p90 (file I/O excluded): `10.477` / `11.047 ms`.
- Sampled process peak RAM: `614.61 MiB`; per-process VRAM is blank because WDDM/nvidia-smi did not expose it.

## Unfinished direct path

The installed CUDA 12.6 toolchain rejects VS 2026, and this environment has no GPU array library that can expose the existing preprocess device pointer to Python ORT. CUDA preprocess -> inference shared buffer/stream and Nsight agreement remain `not_run`.
