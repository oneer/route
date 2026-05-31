# Week 1G: Noise Strength Calibration

This experiment calibrates the synthetic Gaussian noise and shot/read noise settings before comparing model results.

## Why

Week 1F showed that the first shot/read run reached better validation metrics than the Gaussian run. That did not necessarily mean shot/read noise was easier in general; it meant the noise strengths were not matched.

This step measures noisy-input quality first:

```text
input PSNR = PSNR(noisy, clean)
input SSIM = SSIM(noisy, clean)
```

Only after the input difficulty is close should model results be compared.

## Tooling

Added:

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config <config.yaml>
```

The script builds the validation dataset from each config and reports noisy-input PSNR/SSIM without training.

## Input Calibration

| Config | Noise | Input PSNR | Input SSIM |
|---|---|---:|---:|
| `toy_rgb_denoise_dncnn_l2_loss.yaml` | Gaussian | 24.2068 | 0.46247 |
| `toy_rgb_denoise_dncnn_l2_shot_read.yaml` | Shot/read original | 25.9799 | 0.53497 |
| `toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml` | Shot/read calibrated | 24.2036 | 0.45582 |

Calibrated shot/read range:

| Parameter | Range |
|---|---:|
| `shot` | 0.002-0.011 |
| `read` | 0.007-0.028 |

This matches Gaussian input PSNR within `0.0032 dB`.

## Training Results

Both runs use DnCNN residual, L2/MSE loss, patch size 64, 512 train samples, 32 validation samples, and 300 steps.

| Noise | Wall time | Final train loss | Final val PSNR | Final val SSIM |
|---|---:|---:|---:|---:|
| Gaussian | 15.86s | 0.000739 | 31.5874 | 0.89452 |
| Shot/read calibrated | 15.63s | 0.000613 | 32.1824 | 0.91118 |

Validation curve:

| Step | Gaussian PSNR | Gaussian SSIM | Calibrated PSNR | Calibrated SSIM |
|---:|---:|---:|---:|---:|
| 50 | 25.0667 | 0.51077 | 24.8409 | 0.49532 |
| 100 | 28.1588 | 0.68446 | 27.7019 | 0.65377 |
| 150 | 30.6674 | 0.85365 | 30.8698 | 0.84888 |
| 200 | 31.0260 | 0.87585 | 31.5581 | 0.89406 |
| 250 | 31.2477 | 0.88484 | 31.6513 | 0.90450 |
| 300 | 31.5874 | 0.89452 | 32.1824 | 0.91118 |

## Reading

After matching input PSNR, the calibrated shot/read run still ends higher than the Gaussian run. This suggests the model handles this simple signal-dependent noise pattern well on the synthetic RGB dataset.

The conclusion is still limited. These patches are generated procedurally, not sampled from real camera data. The useful engineering result is that future noise experiments now have a baseline measurement step, so comparisons do not silently mix model quality with different input difficulty.

## Artifacts

- `configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml`
- `scripts/02_measure_noise_baseline.py`
- `runs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated/metrics.csv`
- `runs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated/vis/step_0300.png`

## Next

The next step should move from procedural RGB patches toward real RGB denoise data, such as a tiny SIDD-style paired RGB subset, while keeping this noisy-input baseline measurement.
