# Stage 2 Upgrade Plan

## Goal

Upgrade Stage 2 from a PyTorch AI-ISP learning baseline into a more job-ready
AI-ISP engineering project:

```text
traditional ISP understanding
-> paired RGB restoration training
-> pseudo RAW / RGGB bridge
-> ablation and IQ analysis
-> ONNX / C++ inference smoke test
-> portfolio report
```

## Current Baseline

| Area | Evidence |
|---|---|
| Data | SIDD tiny 80/20 noisy-clean paired RGB subset |
| Training | Config-driven DnCNN / UNet / NAFNet-lite runs |
| Metrics | PSNR / SSIM summaries |
| Visualization | triplet images, error maps, failure crops |
| Summary | Week 9 leaderboard and interview notes |

Final Stage 2 leaderboard:

| Task | Run | Best PSNR | Best SSIM |
|---|---|---:|---:|
| SIDD tiny denoise | DnCNN residual | 35.5356 | 0.88367 |
| SIDD tiny denoise | UNet | 30.4453 | 0.88003 |
| SIDD tiny denoise | NAFNet-lite | 33.3269 | 0.86223 |
| Synthetic low-light | UNet | 24.7821 | 0.81468 |

## Track A: Pseudo RAW / RGGB

Purpose: move beyond pure RGB denoise and make the project closer to AI-ISP.

Implemented entry points:

```text
ai_isp/data/pseudo_raw.py
ai_isp/data/paired_pseudo_raw_dataset.py
configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
scripts/12_preview_pseudo_raw_dataset.py
```

Run:

```bash
python stage2_ai_isp/scripts/12_preview_pseudo_raw_dataset.py
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
```

Acceptance:

```text
RGGB preview figure exists
4-channel DnCNN training runs
metrics.csv and best_psnr.pth are generated
```

## Track B: Ablation

Purpose: show algorithm judgement instead of only model execution.

Recommended table:

| Model | Data | Loss | Patch | Steps | Params | PSNR | SSIM | Latency |
|---|---|---|---:|---:|---:|---:|---:|---:|

Minimum experiments:

```text
DnCNN L1 vs L2
patch 64 vs 128
300 vs 1000 vs 2000 steps
RGB vs pseudo RGGB
```

## Track C: ONNX / C++

Purpose: cover the C/C++ and deployment requirements common in ISP jobs.

Implemented entry points:

```text
deployment/export_onnx.py
deployment/cpp_onnx_infer/
deployment/README.md
```

Acceptance:

```text
ONNX export succeeds
C++ inference runs on one SIDD noisy image
latency is recorded
output image is saved
```

## Track D: IQ Metrics

Purpose: connect the project to ISP tuning language.

Planned metrics:

```text
sharpness: Laplacian variance
noise: flat-region standard deviation
exposure: under/over-exposure ratio
color cast: channel mean balance
```

These are not a replacement for Imatest or iQ-Analyzer, but they make the
project easier to discuss with ISP tuning interviewers.

## Resume Positioning

Use this positioning:

```text
AI-ISP image restoration and deployment baseline project
```

Avoid claiming:

```text
mass-production camera tuning
Qualcomm/MTK/HiSilicon ISP platform experience
full industrial RAW ISP system
```

## 3-Year Hiring Bar

For a 3-year social-hiring resume, Stage 2 should not be presented as a simple
training demo. The target bar is:

```text
data construction
-> model baseline
-> objective and visual evaluation
-> failure analysis
-> RAW-like extension
-> deployment smoke test
```

Minimum evidence before using the stronger resume wording:

| Evidence | Status | Why it matters |
|---|---|---|
| SIDD paired RGB leaderboard | Done | proves restoration baseline ability |
| Pseudo RAW/RGGB preview | Done | connects RGB restoration to AI-ISP input shape |
| Pseudo RAW/RGGB training metrics | Next | proves the RAW-like path is trainable |
| ONNX export | Next | proves model can leave PyTorch |
| C++ OpenCV DNN inference | Next | proves deployment-facing engineering |
| Unified PSNR/SSIM/latency table | Next | proves algorithm tradeoff judgement |

Recommended resume wording after completing the next items:

```text
Built an AI-ISP restoration and deployment validation baseline covering paired
RGB denoise, pseudo RAW/RGGB experiments, PSNR/SSIM and failure-case analysis,
and ONNX/C++ inference smoke testing.
```

See `reports/stage2_3year_portfolio_upgrade.md` for the Chinese resume and
interview version.
