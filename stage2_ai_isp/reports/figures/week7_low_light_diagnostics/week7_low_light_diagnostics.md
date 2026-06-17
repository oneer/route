# Week 7 Low-Light Diagnostics

Samples: `20` validation images.
CSV: `stage2_ai_isp/reports/figures/week7_low_light_diagnostics/week7_low_light_diagnostics.csv`

| View | Mean Luma | Luma MAE | Dark Luma MAE | RGB MAE | Under % | Over % | Black Clip % | White Clip % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| low_light_input | 0.1843 | 0.1502 | 0.0715 | 0.1629 | 67.02 | 0.18 | 21.42 | 0.00 |
| model_output | 0.3409 | 0.0249 | 0.0388 | 0.0439 | 0.42 | 1.14 | 0.00 | 0.91 |
| clean_target | 0.3303 | 0.0000 | 0.0000 | 0.0000 | 0.00 | 0.00 | 3.47 | 0.73 |

## Key Reading

- Luma MAE improves by `0.1253` from input to model output.
- Dark-region luma MAE improves by `0.0327`.
- RGB MAE improves by `0.1190`.
- The model output mean luma is `0.3409`, while the clean target mean luma is `0.3303`.
- Under-enhanced pixels drop from `67.02%` to `0.42%`.
- Over-enhanced pixels are `1.14%`, so this run is still more under-enhanced than over-enhanced.

## Interview Use

These diagnostics explain low-light enhancement beyond PSNR/SSIM: the task must recover exposure, suppress dark-region noise, and preserve color. If PSNR improves but dark-region MAE or color MAE remains high, the next experiment should target exposure/noise modeling or color-aware losses rather than only changing the backbone.
