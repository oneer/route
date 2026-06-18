# Stage 2 Engineering Summary

This report upgrades the Week 9 leaderboard into a job-facing engineering table.

CSV: `stage2_ai_isp/reports/figures/week10_engineering_summary/stage2_engineering_summary.csv`

| Task | Run | Model | Channels | Params | Checkpoint MB | PSNR | SSIM |
|---|---|---|---:|---:|---:|---:|---:|
| week4_sidd_tiny_standard_eval | paired_rgb_sidd_tiny_dncnn_l2_2000 | dncnn | 3 | 29507 | 0.351 | 35.5356 | 0.88367 |
| week4_sidd_tiny_standard_eval | paired_rgb_sidd_tiny_unet_l1_1000 | unet | 3 | 118307 | 1.380 | 30.4453 | 0.88003 |
| week4_sidd_tiny_standard_eval | paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | nafnet_lite | 3 | 104307 | 1.329 | 33.3269 | 0.86223 |
| week7_low_light_eval | low_light_sidd_tiny_unet_l1_300 | unet | 3 | 118307 | 1.380 | 24.7821 | 0.81468 |

## Frozen DnCNN Test And Deployment Evidence

| Evidence | Result |
|---|---:|
| Held-out test pairs | 20 |
| Full-image test PSNR | 37.0044 dB |
| Full-image test SSIM | 0.91110 |
| ONNX size | 0.114 MB |
| PyTorch vs ONNX max abs error | 2.38419e-7 |
| ONNX Runtime Python CPU mean latency, 512×512 | 72.1614 ms |
| ONNX Runtime C++ CPU mean latency, 512×512 | 70.3157 ms |

Historical Week 0-9 SSIM values used the earlier approximate implementation.
The frozen test result above uses the current 11×11 Gaussian-window protocol.

## Interview Use

- Use PSNR/SSIM to discuss restoration quality.
- Use params and checkpoint size to discuss deployability.
- Use channel count to distinguish RGB and RAW-like experiments.
- C++ evidence is an ONNX Runtime CPU smoke test, not production deployment.
