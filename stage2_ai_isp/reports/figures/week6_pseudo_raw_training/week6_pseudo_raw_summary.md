# Week 6 Pseudo RAW/RGGB Training Summary

This summary compares the RGB denoise baseline with the pseudo RGGB 4-channel baseline.

| Label | Run | Dataset | Channels | Effective spatial | Params | Input PSNR/SSIM | Best PSNR | Best SSIM | Gain PSNR/SSIM |
|---|---|---|---:|---|---:|---:|---:|---:|---:|
| rgb_300 | paired_rgb_sidd_tiny_dncnn_l2_300 | paired_image | 3 | 128x128 | 29507 | 26.7302/0.52412 | 32.7717@250 | 0.77100@300 | 6.0415/0.24688 |
| pseudo_rggb_300 | pseudo_raw_sidd_tiny_dncnn_l2_300 | paired_pseudo_raw | 4 | 64x64 pack from 128x128 RGB crop | 30084 | 26.6785/0.50447 | 31.7157@300 | 0.77400@300 | 5.0372/0.26953 |

## Notes

- The pseudo RGGB path is RAW-like, not real sensor RAW.
- Pseudo RGGB converts each RGB crop into a 4-channel RGGB pack, so the model input has 4 channels and half spatial resolution.
- RGB and pseudo RGGB PSNR values are not a perfect apples-to-apples image-domain comparison, but they verify that the RAW-shaped path is trainable.
- The key Week 6 acceptance criterion is that the pseudo RGGB run produces metrics and checkpoints and exceeds its own noisy input baseline.
