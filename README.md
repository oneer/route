# Soft ISP — From RAW to RGB, One Pixel at a Time

[中文版本](README_CN.md)

A self-directed learning repository for mastering the full Image Signal Processing (ISP) pipeline — from sensor physics to C++ desktop tools. Built for software engineers transitioning into AI-ISP algorithm roles.

## Repository Map

```
route/
├── docs/
│   └── soft_isp_desktop_design.md   # C++ desktop Soft ISP workbench design doc
├── soft_isp_stage1/                 # Stage 1: Python Soft-ISP learning project
├── study-roadmap/                   # 10-month AI-ISP career learning roadmap
└── README.md
```

### [docs/](docs/) — Design Document

The [Soft ISP Desktop Design Document](docs/soft_isp_desktop_design.md) specifies a C++ desktop workbench for interactive ISP exploration:

- RAW/DNG → staged pipeline → inspect every intermediate result
- Modify per-stage parameters and observe effects in real time
- Swap or extend algorithm modules
- Export final sRGB or any intermediate buffer

Architecture covers: render graph, data model (RAW/non-linear/display nodes), UI layout, color management via OpenColorIO, EXIF round-tripping, and CI/testing strategy (GoogleTest, OpenImageIO, perceptual diff tolerance). Phase 1 targets Qt + CPU float pipeline with preview/full-res separation.

### [soft_isp_stage1/](soft_isp_stage1/) — Stage 1 Learning Project

A hands-on Python Soft-ISP Pipeline — read real DNG files, implement every traditional ISP module yourself (BLC, DPC, LSC, Demosaic, AWB, CCM, Gamma), compare against rawpy references, and write structured reports.

**Status:** Week 1 complete (RAW statistics, histograms, ROI analysis across 5 FiveK samples). Weeks 2-6 cover front-end correction, demosaic/AWB, color/tone, IQA, and final report.

See [soft_isp_stage1/README.md](soft_isp_stage1/README.md) for details.

### [study-roadmap/](study-roadmap/) — Career Learning Roadmap

A 10-month, project-driven curriculum designed for someone with existing ISP engineering experience (Python/C++ pipeline maintenance, fixed-point conversion, multi-channel refactoring) who needs to upgrade from "can align outputs and adapt code" to "can explain algorithms, design experiments, evaluate image quality, and deploy AI-ISP models."

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
python scripts/01_inspect_raw.py data/raw/S01_a0001-jmac_DSC1459.dng
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
| Future C++ workbench | C++17, Qt 6, OpenColorIO, GoogleTest, OpenImageIO |

## Future Stages

| Stage | Focus | Language |
|---|---|---|
| 1 (current) | Traditional ISP pipeline fundamentals | Python |
| 2 | AI-driven RAW denoising / low-light enhancement | Python + PyTorch |
| 3 | C++ high-performance ISP library | C++ |
| 4 | CUDA acceleration + TensorRT/NCNN deployment + desktop workbench | C++ / CUDA |

## License

This is a personal learning portfolio. All original code is available for reference and educational use.
