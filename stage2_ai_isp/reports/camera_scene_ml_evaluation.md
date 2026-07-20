# Camera-scene ML evaluation

Frozen evaluation split: 10 public SIDD paired sRGB crops (`val` pair_00011..pair_00020). Source scenes are disjoint from training according to the tracked dataset audit.

| Method | Samples | PSNR | PSNR gain | SSIM | Texture retention | Color bias | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| dncnn_ort_fp32 | 10 | 32.968 | 6.788 | 0.7202 | 1.271 | 0.00363 | 5 |
| no_denoise | 10 | 26.180 | 0.000 | 0.4414 | 3.430 | 0.00590 | 10 |
| stage1_bilateral | 10 | 28.926 | 2.745 | 0.5722 | 2.170 | 0.00571 | 7 |

## Grouping

Results are grouped by the real SIDD source device code retained in `source_scene`; per-sample rows also retain ISO. This is more traceable than an invented semantic scene label, but it is not a self-captured Camera feature test set.

## Failure taxonomy

The deterministic evaluator can emit `quality_regression`, `color_shift`, `over_smoothing`, `edge_loss`, and `excess_high_frequency`. The last label is a residual-noise/oversharpening diagnostic flag, not automatic proof of halo; the CSV reports observed counts without forcing examples into a class.

## Boundary

DnCNN operates on rendered paired sRGB. It is an RGB restoration feature, not a Bayer/linear Sensor RAW AI-ISP. FP16 is omitted from this image-quality table because a complete frozen-split FP16 output set is not tracked.
