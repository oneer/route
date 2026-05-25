# AI-ISP Stage 2

Stage 2 focuses on AI-ISP and image restoration. The first milestone is a small,
reproducible RGB denoise training loop before moving to SIDD, SID, and RAW
low-light tasks.

## Week 0.5 / Week 1 Goal

Run a minimal PyTorch training loop on synthetic RGB denoise data:

```text
clean RGB patch -> synthetic noise -> tiny CNN / DnCNN / UNet -> denoised RGB
```

This is intentionally small. The goal is to verify the engineering loop:

- deterministic toy dataset
- train / validation split
- checkpoint saving
- PSNR / SSIM validation
- noisy / output / target visualization
- config-driven experiment settings

## Setup

```bash
pip install -r requirements.txt
```

## Train Toy RGB Denoise

```bash
python scripts/01_train_toy_rgb.py --config configs/toy_rgb_denoise_tiny.yaml
python scripts/01_train_toy_rgb.py --config configs/toy_rgb_denoise_unet.yaml
python scripts/01_train_toy_rgb.py --config configs/toy_rgb_denoise_dncnn.yaml
```

Outputs are written to `ai_isp_stage2/runs/<experiment_name>/`:

- `checkpoints/last.pth`
- `checkpoints/best_psnr.pth`
- `vis/step_*.png`
- `metrics.csv`

The generated `runs/` directory is ignored by git because it contains checkpoints,
TensorBoard logs, and visualization artifacts.

## Project Layout

```text
ai_isp_stage2/
├── configs/
├── ai_isp/
│   ├── data/
│   ├── engine/
│   ├── metrics/
│   ├── models/
│   └── utils/
├── scripts/
└── reports/
```
