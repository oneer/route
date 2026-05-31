# Week 1F: Sensor-Like Shot / Read Noise

This experiment adds a simple sensor-like noise model to the toy RGB denoise pipeline.

## Why

The earlier toy task used additive Gaussian noise:

```text
noisy = clean + gaussian_noise
```

That is useful for sanity checks, but real sensors are not purely signal-independent. A minimal next step is:

```text
noisy = clean + shot_noise(clean) + read_noise
```

Shot noise grows with signal intensity. Read noise is closer to a fixed electronic noise floor.

## Implementation

Added `add_shot_read_noise()` in `ai_isp/data/degradations.py`.

The dataset now reads `data.noise.type`:

- `gaussian`: existing behavior
- `shot_read`: signal-dependent shot noise plus signal-independent read noise

Existing Gaussian configs remain compatible because the training code still defaults to `type: gaussian`.

## Setup

| Item | Value |
|---|---:|
| Config | `toy_rgb_denoise_dncnn_l2_shot_read.yaml` |
| Model | DnCNN residual |
| Loss | L2 / MSE |
| Patch size | 64 |
| Steps | 300 |
| Train samples | 512 |
| Val samples | 32 |
| Shot range | 0.001-0.008 |
| Read range | 0.005-0.020 |
| Wall time | 16.31s |

Command:

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_shot_read.yaml
```

## Results

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 50 | 0.002801 | 26.3886 | 0.56549 |
| 100 | 0.001510 | 28.3465 | 0.66396 |
| 150 | 0.000813 | 31.7414 | 0.85285 |
| 200 | 0.000615 | 32.6577 | 0.90570 |
| 250 | 0.000627 | 32.9465 | 0.91702 |
| 300 | 0.000474 | 33.3091 | 0.92704 |

For reference, the earlier Gaussian patch-64 L2 run ended at:

| Noise | Final val PSNR | Final val SSIM |
|---|---:|---:|
| Gaussian | 31.5874 | 0.89452 |
| Shot / read | 33.3091 | 0.92704 |

## Reading

This shot/read setting is not automatically "harder" than the Gaussian baseline. With the chosen ranges, the model reaches higher PSNR and SSIM than the Gaussian patch-64 run. That means the noise strength is not perfectly matched between the two experiments.

The useful result is engineering-oriented: the pipeline can now switch noise models from config, and the validation loop still works without changing training code.

## Artifacts

- `runs/toy_rgb_denoise_dncnn_l2_shot_read/metrics.csv`
- `runs/toy_rgb_denoise_dncnn_l2_shot_read/vis/step_0300.png`

## Next

The next controlled step should calibrate noise strength. A good target is to tune Gaussian sigma and shot/read ranges so the noisy-input PSNR is comparable before training. After that, model comparisons become more meaningful.
