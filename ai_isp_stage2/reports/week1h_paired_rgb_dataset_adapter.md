# Week 1H: Paired RGB Dataset Adapter

This step moves the training pipeline one layer closer to real RGB denoise data.

It does not train on SIDD yet. Instead, it adds the missing engineering piece needed before SIDD: loading paired noisy/clean images from folders.

## Why This Matters

Toy RGB denoise generates data in code:

```text
clean patch -> synthetic noise -> noisy patch
```

Real paired RGB denoise data is different:

```text
noisy image file + matching clean image file -> crop pair -> model
```

If the training loop can only generate toy data, then moving to SIDD would require rewriting the data path later. The right next step is to make the training code accept both:

- procedural toy data;
- paired image folders.

## What Was Added

### Dataset

Added:

```text
ai_isp/data/paired_image_dataset.py
```

It reads two directories:

```text
clean_dir/
  pair_001.png
  pair_002.png

noisy_dir/
  pair_001.png
  pair_002.png
```

Files are matched by filename. Each sample returns:

```python
{
    "noisy": noisy_patch,
    "clean": clean_patch,
    "sigma": 0.0,
}
```

The crop is deterministic from `seed + index`, so experiments stay reproducible.

### Training Config Switch

The training engine now supports:

```yaml
data:
  dataset: paired_image
```

The existing toy configs still use the default:

```yaml
data:
  dataset: toy_rgb
```

or omit `dataset` entirely.

### Smoke Dataset Generator

Added:

```bash
python ai_isp_stage2/scripts/03_prepare_paired_rgb_smoke.py
```

It builds a tiny paired folder under:

```text
ai_isp_stage2/runs/paired_rgb_smoke/
  clean/
  noisy/
```

The clean images come from existing repository images. The noisy images are generated with Gaussian noise. This is only a smoke test for file-based paired data loading, not a real denoise benchmark.

## Commands Run

Prepare paired data:

```bash
python ai_isp_stage2/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
```

Measure noisy-input baseline:

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_smoke_dncnn_l2.yaml
```

Train:

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_smoke_dncnn_l2.yaml
```

## Results

Input noisy quality:

| Dataset | Input PSNR | Input SSIM |
|---|---:|---:|
| paired RGB smoke | 22.1273 | 0.28203 |

Training result:

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 40 | 0.003542 | 24.6907 | 0.40875 |
| 80 | 0.001021 | 30.1269 | 0.73376 |
| 120 | 0.000557 | 32.9687 | 0.89384 |

Runtime:

```text
24.18s
```

## How To Replace This With SIDD Later

The future SIDD config should keep the same shape:

```yaml
data:
  dataset: paired_image
  patch_size: 128
  train_size: 10000
  val_size: 1000
  train:
    noisy_dir: datasets/sidd/train/noisy
    clean_dir: datasets/sidd/train/clean
  val:
    noisy_dir: datasets/sidd/val/noisy
    clean_dir: datasets/sidd/val/clean
```

The key requirement is filename pairing:

```text
noisy/0001.png <-> clean/0001.png
```

If the original dataset uses a different naming scheme, add a small preparation script that creates this normalized folder layout.

## Reading

This step is important because it separates two concerns:

- model training logic;
- dataset file format.

The model, loss, optimizer, checkpointing, metrics, and visualization did not need a rewrite. Only the dataset object changed. That is the right abstraction boundary for moving from toy data to real paired RGB data.

## Next

The next useful step is to write a SIDD subset preparation guide or script. It should normalize the official SIDD file layout into:

```text
datasets/sidd/train/noisy
datasets/sidd/train/clean
datasets/sidd/val/noisy
datasets/sidd/val/clean
```

After that, the same `paired_image` config can train on real smartphone RGB denoise pairs.
