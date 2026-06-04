# Stage 2 Deployment Upgrade

This folder turns the Stage 2 PyTorch restoration baseline into a small
deployment experiment.

## Export ONNX

```bash
python ai_isp_stage2/deployment/export_onnx.py \
  --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml \
  --checkpoint ai_isp_stage2/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth \
  --output ai_isp_stage2/deployment/onnx/dncnn_sidd_tiny.onnx \
  --height 128 \
  --width 128
```

ONNX export uses optional deployment dependencies:

```bash
pip install -r ai_isp_stage2/deployment/requirements.txt
```

## C++ OpenCV DNN Smoke Test

The C++ sample uses OpenCV DNN to run an ONNX model on one RGB image and prints
CPU latency.

```bash
cmake -S ai_isp_stage2/deployment/cpp_onnx_infer -B ai_isp_stage2/deployment/cpp_onnx_infer/build
cmake --build ai_isp_stage2/deployment/cpp_onnx_infer/build --config Release
ai_isp_stage2/deployment/cpp_onnx_infer/build/stage2_onnx_infer \
  ai_isp_stage2/deployment/onnx/dncnn_sidd_tiny.onnx \
  ai_isp_stage2/datasets/sidd_tiny/val/noisy/pair_00001.png \
  ai_isp_stage2/deployment/outputs/pair_00001_restored.png
```

Next target: compare C++ output against PyTorch output and report PSNR/SSIM plus
latency in `reports/week12_onnx_cpp_deployment.md`.
