# Week 8 Failure Taxonomy

This table turns crop-level evidence into actionable debugging hypotheses.

| Run | Crop MAE | Failure Type | Evidence | Likely Reason | Next Step |
|---|---:|---|---|---|---|
| paired_rgb_sidd_tiny_dncnn_l2_2000 | 0.030962 | moderate local error | Top-error crop MAE is 0.97x the group median. | Automatic metrics show severity, not semantic cause. | Inspect the ROI and label it as flat/edge/texture/dark/color/alignment before proposing a fix. |
| paired_rgb_sidd_tiny_dncnn_l1_2000 | 0.029725 | moderate local error | Top-error crop MAE is 0.93x the group median. | Automatic metrics show severity, not semantic cause. | Inspect the ROI and label it as flat/edge/texture/dark/color/alignment before proposing a fix. |
| paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 | 0.031930 | moderate local error | Top-error crop MAE is 1.00x the group median. | Automatic metrics show severity, not semantic cause. | Inspect the ROI and label it as flat/edge/texture/dark/color/alignment before proposing a fix. |
| paired_rgb_sidd_tiny_unet_l1_1000 | 0.036859 | high local error | Top-error crop MAE is 1.15x the group median. | The numeric evidence locates a difficult ROI but cannot identify whether the cause is texture, color, alignment, data, loss, or model capacity. | Inspect the exact ROI and full-image error map, assign a human failure label, then design one controlled experiment. |
| paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | 0.031238 | moderate local error | Top-error crop MAE is 0.98x the group median. | Automatic metrics show severity, not semantic cause. | Inspect the ROI and label it as flat/edge/texture/dark/color/alignment before proposing a fix. |
| low_light_sidd_tiny_unet_l1_300 | 0.037169 | dark-region enhancement / over-smoothing | Low-light crop has high local error while the task also changes exposure. | The model must brighten, denoise, and preserve color at the same time; synthetic low-light degradation is harder than plain denoise. | Add exposure/noise-specific IQ metrics, inspect dark ROI, and compare brightness/color statistics before changing model size. |

## Reading Notes

- This taxonomy is a first-pass diagnosis from crop metrics and run identity.
- It must be read together with `failure_case_crop_sheet.png` and the Week 4 error maps.
- The goal is not to prove a final cause, but to decide the next experiment without guessing blindly.
