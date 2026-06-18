# Stage 2 Deployment Upgrade

This folder turns the Stage 2 PyTorch restoration baseline into a verifiable
deployment experiment. Source code alone is not completion evidence: ONNX,
alignment JSON, C++ output, and latency logs must all exist.

## Export ONNX

```bash
python stage2_ai_isp/deployment/export_onnx.py \
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml \
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth \
  --output stage2_ai_isp/deployment/onnx/dncnn_sidd_tiny.onnx \
  --height 128 \
  --width 128
```

ONNX export uses optional deployment dependencies:

```bash
pip install -r stage2_ai_isp/deployment/requirements.txt
```

The exporter runs `onnx.checker` when the `onnx` package is installed.

## PyTorch / ONNX Runtime Alignment

```bash
python stage2_ai_isp/deployment/validate_onnx.py \
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml \
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth \
  --onnx stage2_ai_isp/deployment/onnx/dncnn_sidd_tiny.onnx \
  --input stage2_ai_isp/datasets/sidd_tiny/test/noisy/pair_00001.png
```

Acceptance:

- `alignment.json` records max/mean absolute error.
- PyTorch and ONNX output images are saved.
- Latency uses warm-up plus repeated runs, not a single forward pass.

## C++ ONNX Runtime Core Validation (No OpenCV Required)

If an OpenCV C++ SDK is unavailable, use this runner to validate the model
execution core. PNG decode/encode stays in Python and is intentionally excluded
from the measured C++ latency.

```bash
python stage2_ai_isp/deployment/prepare_cpp_tensor.py \
  --input stage2_ai_isp/datasets/sidd_tiny/test/noisy/pair_00001.png \
  --output stage2_ai_isp/deployment/outputs/pair_00001_input.f32

cmake -S stage2_ai_isp/deployment/cpp_ort_infer \
  -B stage2_ai_isp/deployment/cpp_ort_infer/build \
  -DONNXRUNTIME_ROOT=D:/Env/onnxruntime/cpu/onnxruntime-win-x64-1.26.0

cmake --build stage2_ai_isp/deployment/cpp_ort_infer/build --config Release

stage2_ai_isp/deployment/cpp_ort_infer/build/Release/stage2_ort_infer.exe \
  stage2_ai_isp/deployment/onnx/dncnn_sidd_tiny.onnx \
  stage2_ai_isp/deployment/outputs/pair_00001_input.f32 \
  stage2_ai_isp/deployment/outputs/pair_00001_cpp_output.f32 5 30 \
  stage2_ai_isp/deployment/outputs/cpp_ort_latency.json

python stage2_ai_isp/deployment/compare_cpp_tensor.py \
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml \
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth \
  --input-image stage2_ai_isp/datasets/sidd_tiny/test/noisy/pair_00001.png \
  --cpp-output stage2_ai_isp/deployment/outputs/pair_00001_cpp_output.f32 \
  --output-dir stage2_ai_isp/deployment/outputs/cpp_ort_alignment
```

On the current Windows workspace, `cpp_ort_infer/build_msvc.bat` initializes the
documented Visual Studio Build Tools and ONNX Runtime SDK paths before running
CMake/Ninja. Update those explicit paths if the toolchain moves.

## C++ OpenCV DNN Smoke Test

The C++ sample uses OpenCV DNN to run an ONNX model on one RGB image and prints
CPU latency.

```bash
cmake -S stage2_ai_isp/deployment/cpp_onnx_infer -B stage2_ai_isp/deployment/cpp_onnx_infer/build
cmake --build stage2_ai_isp/deployment/cpp_onnx_infer/build --config Release
stage2_ai_isp/deployment/cpp_onnx_infer/build/stage2_onnx_infer \
  stage2_ai_isp/deployment/onnx/dncnn_sidd_tiny.onnx \
  stage2_ai_isp/datasets/sidd_tiny/test/noisy/pair_00001.png \
  stage2_ai_isp/deployment/outputs/pair_00001_restored.png \
  5 30
```

Record stdout and compare the C++ PNG against the saved PyTorch/ONNX outputs.
Fill `reports/week12_onnx_cpp_deployment.md`; do not mark Week 12 complete before
all acceptance items in that report are checked.

```bash
python stage2_ai_isp/deployment/compare_backend_outputs.py \
  --reference stage2_ai_isp/deployment/outputs/onnx_alignment/pytorch_output.png \
  --candidate stage2_ai_isp/deployment/outputs/pair_00001_restored.png \
  --output stage2_ai_isp/deployment/outputs/cpp_alignment.json
```
