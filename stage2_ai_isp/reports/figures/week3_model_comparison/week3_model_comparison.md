# Week 3 Model Comparison

This table summarizes real paired RGB denoise runs on the SIDD tiny subset.

Input noisy baseline: PSNR `26.7302`, SSIM `0.52412`.

| Group | Run | Model | Loss | Residual | Patch | Steps | Params | Checkpoint MB | Best PSNR | Best SSIM | PSNR gain | SSIM gain |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| short_300 | paired_rgb_sidd_tiny_dncnn_l2_300 | dncnn | mse | True | 128 | 300 | 29507 | 0.351 | 32.7717@250 | 0.77100@300 | 6.0415 | 0.24688 |
| short_300 | paired_rgb_sidd_tiny_unet_l1_300 | unet | l1 | False | 128 | 300 | 118307 | 1.380 | 28.2856@300 | 0.85951@300 | 1.5554 | 0.33539 |
| short_300 | paired_rgb_sidd_tiny_nafnet_lite_l1_300 | nafnet_lite | l1 | False | 128 | 300 | 19995 | 0.343 | 26.8194@250 | 0.73509@300 | 0.0892 | 0.21097 |
| standard | paired_rgb_sidd_tiny_dncnn_l2_2000 | dncnn | mse | True | 128 | 2000 | 29507 | 0.351 | 35.5356@1800 | 0.88367@1800 | 8.8054 | 0.35955 |
| loss_ablation | paired_rgb_sidd_tiny_dncnn_l1_2000 | dncnn | l1 | True | 128 | 2000 | 29507 | 0.351 | 35.6334@2000 | 0.88839@1800 | 8.9032 | 0.36427 |
| patch_ablation | paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 | dncnn | mse | True | 64 | 2000 | 29507 | 0.351 | 35.2304@1600 | 0.88455@1800 | 8.5002 | 0.36043 |
| standard | paired_rgb_sidd_tiny_unet_l1_1000 | unet | l1 | False | 128 | 1000 | 118307 | 1.380 | 30.4453@1000 | 0.88003@1000 | 3.7151 | 0.35591 |
| standard | paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | nafnet_lite | l1 | False | 128 | 1000 | 104307 | 1.329 | 33.3269@1000 | 0.86223@1000 | 6.5967 | 0.33811 |

## Reading Notes

- `short_300` checks whether each model can learn on the real paired RGB subset.
- `standard` is better for model-capability comparison.
- `loss_ablation` compares DnCNN L1 vs L2 under the same 2000-step setting.
- `patch_ablation` compares patch 64 vs patch 128 for DnCNN L2.
- A run is useful only if it exceeds the noisy input baseline and has a plausible visualization.
