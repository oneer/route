# Week 5 NAFNet-lite Analysis

This report checks whether NAFNet-lite is correctly implemented, shape-compatible, and meaningfully compared against Week 3 baselines.

| Run | Model | Width | Loss | Steps | Params | Shape | Best PSNR | Best SSIM | Gap vs DnCNN L1 | Gap vs DnCNN L2 |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
| paired_rgb_sidd_tiny_nafnet_lite_l1_300 | nafnet_lite | 8 | l1 | 300 | 19995 | (2, 3, 128, 128) -> (2, 3, 128, 128) | 26.8194@250 | 0.73509@300 | -8.8140 | -8.7162 |
| paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | nafnet_lite | 16 | l1 | 1000 | 104307 | (2, 3, 128, 128) -> (2, 3, 128, 128) | 33.3269@1000 | 0.86223@1000 | -2.3065 | -2.2087 |
| paired_rgb_sidd_tiny_dncnn_l2_2000 | dncnn | features=32 | mse | 2000 | 29507 | (2, 3, 128, 128) -> (2, 3, 128, 128) | 35.5356@1800 | 0.88367@1800 | -0.0978 | 0.0000 |
| paired_rgb_sidd_tiny_dncnn_l1_2000 | dncnn | features=32 | l1 | 2000 | 29507 | (2, 3, 128, 128) -> (2, 3, 128, 128) | 35.6334@2000 | 0.88839@1800 | 0.0000 | 0.0978 |
| paired_rgb_sidd_tiny_unet_l1_1000 | unet | base=16 | l1 | 1000 | 118307 | (2, 3, 128, 128) -> (2, 3, 128, 128) | 30.4453@1000 | 0.88003@1000 | -5.1881 | -5.0903 |

## NAFNet-lite Structure Checks

- `paired_rgb_sidd_tiny_nafnet_lite_l1_300`: enc=[1, 1], dec=[1, 1], middle=1, naf_blocks=5, gates=10
- `paired_rgb_sidd_tiny_nafnet_lite_l1_1000`: enc=[1, 1], dec=[1, 1], middle=2, naf_blocks=6, gates=12

## Reading Notes

- Shape compatibility means each model can be trained with pixel-wise restoration loss.
- The 300-step width=8 NAFNet-lite run is a smoke test, not a capability conclusion.
- The 1000-step width=16 NAFNet-lite run shows clear learning, but still trails DnCNN on this tiny split.
- A fairer next NAFNet-lite experiment would keep width=16 and extend to 2000 steps or compare Charbonnier loss.
