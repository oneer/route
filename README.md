# Route — AI-ISP Learning Portfolio

[中文版本](README_CN.md)

A self-directed, project-driven learning repository for mastering the full Image Signal Processing (ISP) pipeline — from sensor physics and traditional ISP algorithms to AI-driven image restoration and eventual C++/CUDA deployment. Built for software engineers transitioning into AI-ISP algorithm roles.

## Repository Map

```
route/
├── soft_isp_stage1/       # Stage 1: Traditional ISP pipeline (Python)
├── ai_isp_stage2/         # Stage 2: AI-ISP image restoration (PyTorch)
├── study-roadmap/         # 10-month AI-ISP career learning roadmap
├── README.md
└── README_CN.md
```

### [soft_isp_stage1/](soft_isp_stage1/) — Stage 1: Traditional ISP Pipeline

A hands-on Python Soft-ISP Pipeline — read real DNG files, implement every traditional ISP module yourself (BLC, DPC, LSC, Demosaic, AWB, CCM, Gamma, Tone Mapping), compare against rawpy references, and write structured reports. Also includes a full [OpenISP](https://github.com/cruxopen/openISP) reference implementation for side-by-side algorithm study.

**Status:** Complete. All modules implemented, IQA ablation done, Week 6 mastery gap closure finished. 16 scripts, full pipeline evaluation, and comprehensive weekly reports (Week 1–6).

See [soft_isp_stage1/README.md](soft_isp_stage1/README.md) for details.

### [ai_isp_stage2/](ai_isp_stage2/) — Stage 2: AI-ISP Image Restoration

The second stage shifts from hand-crafted algorithms to learned image restoration. Currently focused on establishing a reliable deep learning training loop with synthetic RGB denoising before moving to real sensor data (SIDD, SID).

**Status:** In progress. Toy RGB denoise baseline with TinyCNN / DnCNN / UNet is running. Training loop, config system, and PSNR/SSIM evaluation pipeline are in place.

See [ai_isp_stage2/README.md](ai_isp_stage2/README.md) for details.

### [study-roadmap/](study-roadmap/) — Career Learning Roadmap

A 10-month, project-driven curriculum across 4 stages, designed for engineers with existing ISP experience who need to level up from "can adapt code" to "can explain algorithms, design experiments, evaluate image quality, and deploy AI-ISP models."

See [study-roadmap/AI-ISP 图像算法工程师 · 社招学习路线.md](study-roadmap/AI-ISP%20图像算法工程师%20·%20社招学习路线.md) for the full plan.

## Why This Exists

Modern camera pipelines are opaque. The ISP inside your phone or camera is a black box optimized by silicon vendors — you can't see intermediate stages, tweak parameters, or understand why a particular pixel ended up with a particular value.

This project takes the opposite approach: every stage is explicit, inspectable, and modifiable. The goal is not to compete with Lightroom or Adobe Camera Raw, but to build a mental model solid enough that you can:

- Read a RAW histogram and diagnose sensor issues before writing any code
- Explain why Demosaic comes after BLC but before AWB — and what breaks if you reorder them
- Tune a parameter and predict which image regions will change and why
- Compare your output against a reference and articulate every gap
- Eventually replace traditional modules with learned ones, knowing exactly what you're replacing

## Getting Started

Start with [soft_isp_stage1/](soft_isp_stage1/) — the Python learning project. It requires no C++ toolchain and produces visual output immediately.

```bash
cd soft_isp_stage1
pip install -r requirements.txt
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
```

If you don't have RAW files yet, use the included download script:

```powershell
.\soft_isp_stage1\scripts\download_fivek_starter.ps1
```

## Project Philosophy

1. **Physics before code.** Understand what the sensor measures before writing a single line of ISP logic.
2. **Implement before importing.** Write your own BLC, Demosaic, AWB before reaching for library functions. You can't explain what you haven't built.
3. **Visualize everything.** Histograms, ROI overlays, difference maps. If you can't see it, you can't debug it.
4. **Compare relentlessly.** Every module output gets compared against rawpy/LibRaw references. Every difference gets explained.
5. **Write reports, not just code.** A notebook full of experiments with no written conclusions is not a deliverable.

## Technology Stack

| Layer | Tools |
|---|---|
| RAW I/O | rawpy (libraw), imageio |
| Array processing | NumPy, OpenCV |
| Visualization | Matplotlib |
| Metrics | scikit-image (SSIM), colour-science (Delta E) |
| Configuration | YAML |
| Deep learning | PyTorch, torchvision |
| Future C++ workbench | C++17, Qt 6, OpenColorIO, GoogleTest, OpenImageIO |

## Stages

| Stage | Focus | Language | Status |
|---|---|---|---|
| 1 | Traditional ISP pipeline fundamentals | Python | Complete |
| 2 | AI-driven image restoration & denoising | Python + PyTorch | In progress |
| 3 | C++ high-performance ISP library | C++ | Planned |
| 4 | CUDA acceleration + TensorRT/NCNN deployment | C++ / CUDA | Planned |

## License

This is a personal learning portfolio. All original code is available for reference and educational use.
