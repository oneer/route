# Week 8 Failure Taxonomy

This table turns crop-level evidence into actionable debugging hypotheses.

| Run | Crop MAE | Failure Type | Evidence | Likely Reason | Next Step |
|---|---:|---|---|---|---|
| paired_rgb_sidd_tiny_dncnn_l2_2000 | 0.029846 | baseline smoothing / residual local error | DnCNN L2 is strong globally; Crop MAE is below or near the group median. | MSE aligns with PSNR but can slightly smooth uncertain texture. | Compare against DnCNN L1 and crop-level visual details rather than relying only on PSNR. |
| paired_rgb_sidd_tiny_dncnn_l1_2000 | 0.028497 | strong baseline / residual local error | DnCNN L1 has the best global metrics, but crop error is still non-zero. | Residual denoise fits the task well, but local texture and color differences remain due to tiny data and simple loss. | Use it as the current baseline; inspect error map before deciding whether Charbonnier or more data is worthwhile. |
| paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 | 0.014191 | context-limited denoise | Patch64 has competitive SSIM but lower PSNR than patch128. | Smaller patch sees less spatial context, which can limit pixel-accurate restoration on texture/edge regions. | Use patch64 for quick ablation, but keep patch128 for final-quality runs. |
| paired_rgb_sidd_tiny_unet_l1_1000 | 0.036193 | local texture or color residual | UNet can keep structural similarity high, but crop MAE is relatively high. | Encoder-decoder structure preserves coarse structure, but direct-output training may leave pixel/color residual in local crops. | Inspect texture/edge crops; compare residual-output UNet or add local/color-aware analysis. |
| paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | 0.030536 | under-trained modern block / residual noise | NAFNet-lite improves over input baseline but still trails the strongest DnCNN run. | The simplified NAFNet-lite setting uses limited data and 1000 steps, without full official training strategy. | Extend NAFNet-lite to 2000 steps or test Charbonnier loss before judging the architecture. |
| low_light_sidd_tiny_unet_l1_300 | 0.036040 | dark-region enhancement / over-smoothing | Low-light crop has high local error while the task also changes exposure. | The model must brighten, denoise, and preserve color at the same time; synthetic low-light degradation is harder than plain denoise. | Add exposure/noise-specific IQ metrics, inspect dark ROI, and compare brightness/color statistics before changing model size. |

## Reading Notes

- This taxonomy is a first-pass diagnosis from crop metrics and run identity.
- It must be read together with `failure_case_crop_sheet.png` and the Week 4 error maps.
- The goal is not to prove a final cause, but to decide the next experiment without guessing blindly.
