# IQ system report

## Verified evidence

- 14 public DNG sample(s); 3 controlled tuning decisions; clipping, ROI SNR, DR and MTF proxies.
- Manifest hashes and repository-relative paths are validated before aggregation.
- Tuning decisions use a declared problem → hypothesis → parameter sweep → metric → rejection loop.

| Case | Selected value | PSNR | SSIM | Delta E proxy |
|---|---|---:|---:|---:|
| awb_filter | 0/100 | 27.997 | 0.9883 | 6.115 |
| bilateral_sigma | 0.100 | 34.501 | 0.8876 | 3.389 |
| tone_highlight | percentile/99 | 18.195 | 0.9449 | 10.164 |

## Boundary

The 14 inputs are public DNGs. Natural-image ROI SNR/DR/MTF and full-image Delta E are proxies, not lab chart measurements. Self-captured ColorChecker, flat-field, slanted-edge, and Sensor RAW tuning remain `not_run`.
