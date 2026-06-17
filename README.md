# Route — AI-ISP Learning Portfolio

[中文版本](README_CN.md)

A self-directed, project-driven learning repository for mastering the full Image Signal Processing (ISP) pipeline — from sensor physics and traditional ISP algorithms to AI-driven image restoration and eventual C++/CUDA deployment. Built for software engineers transitioning into AI-ISP algorithm roles.

## Repository Map

```
route/
├── stage1_soft_isp/       # Stage 1: Traditional ISP pipeline (Python)
├── stage2_ai_isp/         # Stage 2: AI-ISP image restoration (PyTorch)
├── stage3_cpp_isp/        # Stage 3: C++ high-performance ISP library
├── stage4_deploy_isp/     # Stage 4: ONNX Runtime C++ deployment
├── isp_tutorial_study/    # ISP tutorial study area (35 chapters, algorithm to RTL)
├── study-roadmap/         # 10-month AI-ISP career learning roadmap
├── README.md
└── README_CN.md
```

### [stage1_soft_isp/](stage1_soft_isp/) — Stage 1: Traditional ISP Pipeline

A hands-on Python Soft-ISP Pipeline — read real DNG files, implement every traditional ISP module yourself (BLC, DPC, LSC, Demosaic, AWB, CCM, Gamma, Tone Mapping), compare against rawpy references, and write structured reports. Also includes a full [OpenISP](https://github.com/cruxopen/openISP) reference implementation for side-by-side algorithm study.

**Status:** Complete. All modules implemented, IQA ablation done, Week 6 mastery gap closure finished. 16 scripts, full pipeline evaluation, and comprehensive weekly reports (Week 1–6).

See [stage1_soft_isp/README.md](stage1_soft_isp/README.md) for details.

### [stage2_ai_isp/](stage2_ai_isp/) — Stage 2: AI-ISP Image Restoration

The second stage shifts from hand-crafted algorithms to learned image restoration. Currently focused on establishing a reliable deep learning training loop with synthetic RGB denoising before moving to real sensor data (SIDD, SID).

**Status:** Complete (Week 0–9). The full pipeline from toy RGB denoise → real SIDD paired RGB → model comparison (DnCNN / UNet / NAFNet-lite) → pseudo RAW / ISP bridge → low-light enhancement → failure case analysis has been executed and documented. Training loop, config system, PSNR/SSIM evaluation pipeline, triplet visualizations, error maps, and a comprehensive stage-2 project summary (including resume and interview talking points) are all in place.

See [stage2_ai_isp/README.md](stage2_ai_isp/README.md) for details.

### [stage3_cpp_isp/](stage3_cpp_isp/) — Stage 3: C++ High-Performance ISP Library

The third stage ports key ISP algorithms from Python reference to production-style C++17, with a strict loop: Python reference → C++ implementation → alignment test → benchmark → report. Uses a custom `CPF32` binary tensor format for cross-language verification.

**Status:** Complete (Week 0–8). Project skeleton, image layout, RAW noise modeling, basic denoise (Gaussian / box / bilateral / NLM), SIDD real-data bridge, denoise performance benchmarking, global tone mapping (Reinhard / Filmic / ACES / percentile), tone LUT with fixed-point quantization, local tone mapping + HDR merge, and full pipeline integration are complete with Python references, alignment tests, benchmarks, and weekly reports.

See [stage3_cpp_isp/README.md](stage3_cpp_isp/README.md) for details.

### [stage4_deploy_isp/](stage4_deploy_isp/) — Stage 4: ONNX Runtime C++ Deployment

The fourth stage takes the Stage 2 AI-ISP restoration model through a reproducible deployment chain: PyTorch → ONNX export → ONNX Runtime Python/C++ inference → TensorRT backend experiments → INT8 quantization → lightweight ISP pre/post integration.

**Status:** In Progress (Week 0–6). PyTorch fixed baseline, ONNX export with output alignment, ONNX Runtime C++ runner, CUDA kernel stubs (normalize / pack_raw), backend profiling, INT8 QDQ quantization with quality analysis, and end-to-end pipeline profiling are complete with weekly reports and artifacts.

See [stage4_deploy_isp/README.md](stage4_deploy_isp/README.md) for details.

### [isp_tutorial_study/](isp_tutorial_study/) — ISP Tutorial Study Area

An independent, structured study area for the [ISP IP Design Tutorial: From Algorithm to RTL](https://zsc.github.io/isp_tutorial/) (35 chapters). Each chapter is expanded with beginner-friendly explanations, principle breakdowns, engineering considerations, experiment suggestions, self-test questions, and reference materials — going far beyond the original web content.

**Coverage:** Traditional ISP fundamentals (Ch. 1–16), industry architectures (Ch. 17–27, covering mobile, automotive, professional, consumer, surveillance, and video ISPs), AI-ISP fusion (Ch. 28–31), verification and deployment (Ch. 32–35).

See [isp_tutorial_study/README.md](isp_tutorial_study/README.md) for the study workflow.

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

Start with [stage1_soft_isp/](stage1_soft_isp/) — the Python learning project. It requires no C++ toolchain and produces visual output immediately.

```bash
cd stage1_soft_isp
pip install -r requirements.txt
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
```

If you don't have RAW files yet, use the included download script:

```powershell
.\stage1_soft_isp\scripts\download_fivek_starter.ps1
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
| C++ workbench | C++17, CMake, Ninja, GoogleTest, Google Benchmark |
| Deployment / inference | ONNX Runtime, CUDA, TensorRT, ONNX, OpenCV (C++) |

## Stages

| Stage | Focus | Language | Status |
|---|---|---|---|
| 1 | Traditional ISP pipeline fundamentals | Python | Complete |
| 2 | AI-driven image restoration & denoising | Python + PyTorch | Complete |
| 3 | C++ high-performance ISP library | C++17 | Complete |
| 4 | ONNX Runtime deployment + CUDA inference | C++ / Python / CUDA | In Progress (Week 0–6) |

## License

This is a personal learning portfolio. All original code is available for reference and educational use.
