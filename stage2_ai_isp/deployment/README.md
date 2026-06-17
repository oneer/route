# Stage 2 Deployment Upgrade

This folder turns the Stage 2 PyTorch restoration baseline into a small
deployment experiment.

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

## C++ OpenCV DNN Smoke Test

The C++ sample uses OpenCV DNN to run an ONNX model on one RGB image and prints
CPU latency.

```bash
cmake -S stage2_ai_isp/deployment/cpp_onnx_infer -B stage2_ai_isp/deployment/cpp_onnx_infer/build
cmake --build stage2_ai_isp/deployment/cpp_onnx_infer/build --config Release
stage2_ai_isp/deployment/cpp_onnx_infer/build/stage2_onnx_infer \
  stage2_ai_isp/deployment/onnx/dncnn_sidd_tiny.onnx \
  stage2_ai_isp/datasets/sidd_tiny/val/noisy/pair_00001.png \
  stage2_ai_isp/deployment/outputs/pair_00001_restored.png
```

Next target: compare C++ output against PyTorch output and report PSNR/SSIM plus
latency in `reports/week12_onnx_cpp_deployment.md`.
