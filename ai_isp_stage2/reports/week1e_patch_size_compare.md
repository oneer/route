# Week 1E: Patch Size 64 / 128 Compare

This experiment compares patch size 64 and 128 on the same toy RGB denoise task.

## Setup

Both runs use DnCNN residual with L2/MSE loss. The only intended variable is `data.patch_size`.

| Item | Patch 64 | Patch 128 |
|---|---:|---:|
| Config | `toy_rgb_denoise_dncnn_l2_loss.yaml` | `toy_rgb_denoise_dncnn_l2_patch128.yaml` |
| Model | DnCNN residual | DnCNN residual |
| Loss | L2 / MSE | L2 / MSE |
| Steps | 300 | 300 |
| Train samples | 512 | 512 |
| Val samples | 32 | 32 |
| Noise | Gaussian, sigma 0.03-0.12 | Gaussian, sigma 0.03-0.12 |
| Seed | 42 | 42 |

Commands:

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_patch128.yaml
```

## Results

| Patch size | Wall time | Final train loss | Final val PSNR | Final val SSIM |
|---:|---:|---:|---:|---:|
| 64 | 15.86s | 0.000739 | 31.5874 | 0.89452 |
| 128 | 51.40s | 0.000499 | 33.4745 | 0.93176 |

Validation curve:

| Step | 64 PSNR | 64 SSIM | 128 PSNR | 128 SSIM |
|---:|---:|---:|---:|---:|
| 50 | 25.0667 | 0.51077 | 24.7307 | 0.40555 |
| 100 | 28.1588 | 0.68446 | 28.6054 | 0.61600 |
| 150 | 30.6674 | 0.85365 | 32.1358 | 0.85822 |
| 200 | 31.0260 | 0.87585 | 32.8896 | 0.90487 |
| 250 | 31.2477 | 0.88484 | 32.6052 | 0.92436 |
| 300 | 31.5874 | 0.89452 | 33.4745 | 0.93176 |

## Reading

Patch 128 is much slower because each sample has four times as many pixels as patch 64. The measured runtime is about 3.24x longer in this run.

Patch 128 starts weaker at step 50, but becomes clearly better after step 150. The larger crop gives the model more spatial context and makes validation patches less tiny, so PSNR and SSIM improve by the end.

The practical conclusion is:

- Use patch 64 for quick sanity checks.
- Use patch 128 when comparing final model quality on this toy task.
- Keep runtime in mind before moving to real RGB or RAW datasets.

## Artifacts

- `runs/toy_rgb_denoise_dncnn_l2_loss/metrics.csv`
- `runs/toy_rgb_denoise_dncnn_l2_loss/vis/step_0300.png`
- `runs/toy_rgb_denoise_dncnn_l2_patch128/metrics.csv`
- `runs/toy_rgb_denoise_dncnn_l2_patch128/vis/step_0300.png`

## Next

The next experiment should replace fixed synthetic Gaussian noise with a more sensor-like noise model.
