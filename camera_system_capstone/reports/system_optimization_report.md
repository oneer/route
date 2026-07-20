# System optimization report

## Verified result

- 14/14 CTest passed; synthetic calibration/fusion aligned; fusion p50/p90 = 17.558/18.795 ms at 1080P.
- ORT CUDA I/O Binding inference p50/p90=3.296/3.754 ms; e2e p50/p90=10.477/11.047 ms; RAM=614.61 MiB; copies=1 H2D / 0 intermediate D2H / 1 final D2H.
- Correctness is compared with ORT CPU in Stage 4; peak RAM is `614.61 MiB`.
- Transfer contract: `1 H2D / 0 intermediate D2H / 1 final D2H`.

## Boundary

The desktop RTX 4060 Ti result excludes file I/O. Preprocess is still CPU NumPy followed by one H2D; custom CUDA preprocess pointer binding, Nsight validation, per-process VRAM, Snapdragon/NPU latency, and mobile power remain `not_run`.
