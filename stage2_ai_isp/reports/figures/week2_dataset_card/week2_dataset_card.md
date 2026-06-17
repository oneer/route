# Week 2 Dataset Card: SIDD tiny paired RGB

## Purpose

This subset verifies the real paired RGB data path before larger AI-ISP experiments. It is used to check noisy/clean pairing, image size consistency, noisy-input baseline, and small-step denoise training.

## Source

- Dataset root: `stage2_ai_isp/datasets/sidd_tiny`
- Source dataset: SIDD Small sRGB, cropped into a tiny local subset.
- Manifest rows: 100
- Unique source scenes: 100

## Split Summary

| Split | Noisy | Clean | Matched | Unmatched noisy | Unmatched clean | Sizes | Mean pair PSNR | Mean abs diff |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| train | 80 | 80 | 80 | 0 | 0 | 512x512 | 28.2521 | 0.034589 |
| val | 20 | 20 | 20 | 0 | 0 | 512x512 | 26.5687 | 0.041222 |

## Checks

- Noisy and clean files should have identical names inside each split.
- Matched count should equal noisy and clean count.
- Unmatched noisy / clean counts should be zero.
- Image sizes should be consistent within each split.
- Mean pair PSNR is a full-crop data sanity metric, not a trained model result.
