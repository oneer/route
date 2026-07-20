# Stage 1 controlled IQ tuning sweep

Source: `data/references/T01_a0006-IMG_2787_rawpy_srgb.png` (public DNG rawpy sRGB rendering).

This experiment closes the reproducible tuning-loop gap with known synthetic perturbations. It does not replace self-captured scenes, a ColorChecker, a flat field, or a slanted-edge chart.

| Case | Selected parameter | PSNR | SSIM | Delta E 2000 proxy | Texture retention | Highlight clip |
|---|---|---:|---:|---:|---:|---:|
| awb_filter | 0/100 | 27.997 | 0.9883 | 6.115 | 1.007 | 0.1323 |
| bilateral_sigma | 0.100 | 34.501 | 0.8876 | 3.389 | 1.257 | 0.0015 |
| tone_highlight | percentile/99 | 18.195 | 0.9449 | 10.164 | 1.112 | 0.1979 |

## Decision loop

Each case records problem -> hypothesis -> module -> parameter sweep -> metrics -> failure reason -> selected setting. The full machine-readable table is `figures/camera_iq/tuning_sweep.csv`.

## Boundary

Delta E is full-image reference difference, not ColorChecker accuracy. Noise is injected Gaussian RGB noise, not a calibrated sensor noise model. Decisions must be re-tuned on captured Camera scenes.
