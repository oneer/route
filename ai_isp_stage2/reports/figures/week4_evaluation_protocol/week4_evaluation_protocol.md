# Week 4 Evaluation Protocol Summary

Input noisy baseline: PSNR `26.7302`, SSIM `0.52412`.

| Eval | Run | Best PSNR | Best SSIM | PSNR gain | SSIM gain | PSNR rank | SSIM rank | Note |
|---|---|---:|---:|---:|---:|---:|---:|---|
| short_300 | paired_rgb_sidd_tiny_dncnn_l2_300 | 32.7717@250 | 0.77100@300 | 6.0415 | 0.24688 | 1 | 2 | Best PSNR and best SSIM occur at different steps |
| short_300 | paired_rgb_sidd_tiny_unet_l1_300 | 28.2856@300 | 0.85951@300 | 1.5554 | 0.33539 | 2 | 1 | PSNR/SSIM broadly aligned |
| short_300 | paired_rgb_sidd_tiny_nafnet_lite_l1_300 | 26.8194@250 | 0.73509@300 | 0.0892 | 0.21097 | 3 | 3 | Best PSNR and best SSIM occur at different steps |
| standard | paired_rgb_sidd_tiny_dncnn_l2_2000 | 35.5356@1800 | 0.88367@1800 | 8.8054 | 0.35955 | 1 | 1 | PSNR/SSIM broadly aligned |
| standard | paired_rgb_sidd_tiny_unet_l1_1000 | 30.4453@1000 | 0.88003@1000 | 3.7151 | 0.35591 | 3 | 2 | PSNR/SSIM broadly aligned |
| standard | paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | 33.3269@1000 | 0.86223@1000 | 6.5967 | 0.33811 | 2 | 3 | PSNR/SSIM broadly aligned |
| ablation | paired_rgb_sidd_tiny_dncnn_l2_2000 | 35.5356@1800 | 0.88367@1800 | 8.8054 | 0.35955 | 2 | 3 | PSNR/SSIM broadly aligned |
| ablation | paired_rgb_sidd_tiny_dncnn_l1_2000 | 35.6334@2000 | 0.88839@1800 | 8.9032 | 0.36427 | 1 | 1 | Best PSNR and best SSIM occur at different steps |
| ablation | paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 | 35.2304@1600 | 0.88455@1800 | 8.5002 | 0.36043 | 3 | 2 | Best PSNR and best SSIM occur at different steps |
| ablation | paired_rgb_sidd_tiny_unet_l1_1000 | 30.4453@1000 | 0.88003@1000 | 3.7151 | 0.35591 | 5 | 4 | PSNR/SSIM broadly aligned |
| ablation | paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | 33.3269@1000 | 0.86223@1000 | 6.5967 | 0.33811 | 4 | 5 | PSNR/SSIM broadly aligned |

## How To Use

- If PSNR and SSIM ranks disagree, inspect the triplet contact sheet and error map before choosing a model.
- If best PSNR and best SSIM occur at different steps, keep both metric rows in the report and avoid relying only on the last checkpoint.
- A model must exceed the noisy input baseline before it can be considered useful.
