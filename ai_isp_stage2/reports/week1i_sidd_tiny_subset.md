# Week 1I: Tiny SIDD-Style Paired RGB Subset

This step prepares the first real-data entry point after the paired RGB smoke test.

No real dataset is committed here. The goal is to normalize an external paired RGB denoise dataset into the folder layout already supported by `PairedImageDenoiseDataset`.

## Target Layout

```text
ai_isp_stage2/datasets/sidd_tiny/
  train/
    noisy/
    clean/
  val/
    noisy/
    clean/
```

Files must be paired by filename inside each split:

```text
train/noisy/pair_00001.png <-> train/clean/pair_00001.png
val/noisy/pair_00001.png   <-> val/clean/pair_00001.png
```

## Added Script

```bash
python ai_isp_stage2/scripts/04_prepare_paired_rgb_subset.py \
  --source-noisy-dir path/to/source/noisy \
  --source-clean-dir path/to/source/clean \
  --output-dir ai_isp_stage2/datasets/sidd_tiny \
  --train-count 80 \
  --val-count 20 \
  --size 512
```

The script recursively scans both source roots, matches pairs with a filename key that ignores common denoise tokens such as `noisy`, `clean`, `gt`, `srgb`, and `rgb`, then writes normalized `pair_XXXXX.png` files.

Use `--size 0` to keep original image size. Use a positive size to resize the short side and center-crop a square image.

## Training Config

Added:

```text
configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

It points to:

```text
datasets/sidd_tiny/train/noisy
datasets/sidd_tiny/train/clean
datasets/sidd_tiny/val/noisy
datasets/sidd_tiny/val/clean
```

Training command after the subset exists:

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

Noisy-input baseline command:

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

## Success Criteria

- The preparation script writes matching train and val noisy/clean files.
- `02_measure_noise_baseline.py` can read the prepared dataset without shape or pairing errors.
- `01_train_toy_rgb.py` reaches the first validation step and writes `metrics.csv`.

## Local Verification

The new subset script was smoke-tested with three local image pairs named like SIDD RGB pairs:

```text
NOISY_SRGB_0001.jpg <-> GT_SRGB_0001.jpg
```

Command:

```bash
python ai_isp_stage2/scripts/04_prepare_paired_rgb_subset.py --source-noisy-dir ai_isp_stage2/runs/prepare_subset_smoke_source/noisy --source-clean-dir ai_isp_stage2/runs/prepare_subset_smoke_source/clean --output-dir ai_isp_stage2/runs/prepare_subset_smoke_output --train-count 2 --val-count 1 --size 128
```

Result:

```text
train/noisy/pair_00001.png
train/clean/pair_00001.png
train/noisy/pair_00002.png
train/clean/pair_00002.png
val/noisy/pair_00001.png
val/clean/pair_00001.png
```

The existing paired RGB smoke training path was also re-run locally:

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 40 | 0.003541 | 24.6943 | 0.40882 |
| 80 | 0.001015 | 30.2105 | 0.73756 |
| 120 | 0.000558 | 32.9381 | 0.89218 |

## Next

Once a real subset is prepared locally, run the noisy-input baseline first. Then run the 500-step DnCNN residual config and compare model output against the noisy-input PSNR/SSIM.
