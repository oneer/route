# Week 1D: L1 / L2 Loss Compare

This experiment compares L1 loss and L2/MSE loss on the same toy RGB denoise task.

## Setup

Both runs use the same settings except `train.loss` and `experiment.output_dir`.

| Item | Value |
|---|---:|
| Model | DnCNN residual |
| Steps | 300 |
| Patch size | 64 |
| Train samples | 512 |
| Val samples | 32 |
| Noise | Gaussian, sigma 0.03-0.12 |
| Seed | 42 |

Configs:

- `configs/toy_rgb_denoise_dncnn_l1_loss.yaml`
- `configs/toy_rgb_denoise_dncnn_l2_loss.yaml`

Commands:

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l1_loss.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
```

## Results

| Loss | Final train loss | Final val PSNR | Final val SSIM |
|---|---:|---:|---:|
| L1 | 0.020152 | 31.1470 | 0.89850 |
| L2 / MSE | 0.000739 | 31.5874 | 0.89452 |

Validation curve:

| Step | L1 PSNR | L1 SSIM | L2 PSNR | L2 SSIM |
|---:|---:|---:|---:|---:|
| 50 | 24.8449 | 0.49443 | 25.0667 | 0.51077 |
| 100 | 27.8864 | 0.66985 | 28.1588 | 0.68446 |
| 150 | 30.4466 | 0.85876 | 30.6674 | 0.85365 |
| 200 | 30.9554 | 0.88758 | 31.0260 | 0.87585 |
| 250 | 31.0624 | 0.89672 | 31.2477 | 0.88484 |
| 300 | 31.1470 | 0.89850 | 31.5874 | 0.89452 |

## Reading

L2 reaches a higher final PSNR because PSNR is derived from mean squared error, so the training objective is aligned with the validation metric. L1 ends with slightly better SSIM, which suggests it keeps structure a little better in this small synthetic setting.

The two losses are close enough that this result should not be over-read. On this toy task, the practical conclusion is:

- Use L2/MSE when the immediate target is PSNR.
- Keep L1 as a useful baseline when checking structure and visual smoothness.
- Compare final visual triplets before choosing a default for less synthetic noise.

## Artifacts

- `runs/toy_rgb_denoise_dncnn_l1_loss/metrics.csv`
- `runs/toy_rgb_denoise_dncnn_l1_loss/vis/step_0300.png`
- `runs/toy_rgb_denoise_dncnn_l2_loss/metrics.csv`
- `runs/toy_rgb_denoise_dncnn_l2_loss/vis/step_0300.png`

## Next

The next controlled experiment should compare patch size 64 vs 128 while keeping the model and loss fixed.
