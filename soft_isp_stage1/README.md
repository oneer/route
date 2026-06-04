# Soft-ISP Stage 1 — RAW Foundation & Traditional ISP Pipeline

[中文版本](README_CN.md)

A hands-on, explainable Python Soft-ISP Pipeline built from scratch. This project reads real RAW/DNG files and implements the full traditional ISP chain — black level correction, defect pixel correction, lens shading correction, demosaicing, auto white balance, color correction matrix, and gamma/tone mapping — with per-module statistics, visualizations, and comparison against rawpy reference outputs.

## Why This Exists

Most ISP tutorials stop at theory or provide opaque "black box" library calls. This project forces you to:

- Read real sensor data and understand what every number in a RAW file means.
- Implement each ISP module yourself so you can explain its math, assumptions, failure modes, and parameter effects.
- Compare your output against rawpy/LibRaw references and articulate every difference.
- Build the habit of writing structured reports (not just code) that are interview-ready.

## Project Structure

```
soft_isp_stage1/
├── configs/
│   └── default.yaml              # Pipeline module toggles and parameters
├── data/
│   ├── raw/                      # Input DNG/RAW files (gitignored)
│   └── references/               # rawpy-processed sRGB reference PNGs
├── materials/
│   ├── stage1_start_here.md      # 6-week roadmap and daily instructions
│   ├── module_study_template.md  # Template for studying each ISP module
│   ├── raw_sample_manifest.md    # RAW sample registry with download URLs
│   ├── resources.md              # Master index of papers, courses, datasets
│   ├── books/                    # Reference book list
│   ├── datasets/                 # FiveK index + auto-generated metadata table
│   ├── notes/                    # Paper reading template
│   ├── open_source/              # OpenISP / Infinite-ISP study guide
│   ├── papers/                   # Key papers (Karaimer & Brown, HDR+, SID, +)
│   └── slides/                   # Stanford EE367, Cornell CS6640 lecture PDFs
├── notebooks/                    # Jupyter notebooks (reserved)
├── reports/
│   ├── stage1_report.md          # Final stage 1 report template
│   ├── README.md                 # Report index
│   ├── week1/                    # Week 1: RAW stats, ROI, summary
│   ├── week2/                    # Week 2: BLC, DPC, summary
│   ├── week3/                    # Week 3: Demosaic, AWB, summary
│   ├── interview/                # Interview prep materials
│   ├── figures/                  # Generated histogram + ROI preview PNGs
│   └── raw_stats/                # Per-sample JSON metadata dumps
├── scripts/
│   ├── 01_inspect_raw.py         # Dump RAW metadata + per-channel stats as JSON
│   ├── 02_generate_rawpy_references.py  # Generate rawpy sRGB reference PNGs
│   ├── 03_dump_raw_metadata_table.py    # Build Markdown metadata summary table
│   ├── 04_plot_raw_histogram.py  # Plot dual-panel RAW + Bayer-channel histograms
│   ├── 05_analyze_raw_roi.py     # Auto-select dark/midtone/highlight ROIs
│   ├── 06_apply_blc.py           # Apply Black Level Correction
│   ├── 07_apply_dpc.py           # Apply Defect Pixel Correction
│   ├── 08_apply_demosaic.py      # Apply Demosaicing (bilinear / OpenCV)
│   ├── 09_apply_awb.py           # Apply Auto White Balance
│   ├── 10_apply_ccm.py           # Apply Color Correction Matrix
│   ├── 11_apply_gamma.py         # Apply Gamma encoding
│   ├── 12_apply_tone_mapping.py  # Apply Tone Mapping (Reinhard / percentile)
│   ├── 13_write_week4_summary.py # Generate Week 4 summary and comparison figures
│   ├── 14_apply_lsc.py           # Apply Lens Shading Correction (radial / mesh)
│   ├── 15_evaluate_pipeline.py   # Full pipeline evaluation with IQA metrics
│   ├── 16_close_mastery_gaps.py  # Week 6 mastery gap closure experiments
│   ├── week4_common.py           # Shared utilities for Week 4 scripts
│   └── download_fivek_starter.ps1  # Download 5 MIT-Adobe FiveK starter DNGs
├── soft_isp/
│   ├── __init__.py               # Package init
│   ├── stats.py                  # Core utilities: Bayer inference, stats, splitting
│   ├── orientation.py            # CFA pattern orientation detection
│   ├── blc.py                    # Black Level Correction
│   ├── dpc.py                    # Defect Pixel Correction (static / gradient)
│   ├── lsc.py                    # Lens Shading Correction (radial / mesh)
│   ├── demosaic.py               # Demosaicing (bilinear + OpenCV)
│   ├── awb.py                    # Auto White Balance (Gray World + ROI-based)
│   ├── ccm.py                    # Color Correction Matrix (least-squares 3×3)
│   └── tone.py                   # Gamma encoding + Tone Mapping
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Environment Setup

```bash
# Clone and enter the project
cd soft_isp_stage1

# Install dependencies (Python 3.9+)
pip install -r requirements.txt
```

### 2. Download RAW Samples

**Option A — PowerShell (Windows):**

```powershell
.\scripts\download_fivek_starter.ps1
```

**Option B — Manual:**

Download 5 DNG files from the [MIT-Adobe FiveK dataset](https://data.csail.mit.edu/graphics/fivek/) into `data/raw/`. Refer to `materials/raw_sample_manifest.md` for the exact file list and URLs.

### 3. Generate Reference Outputs

```bash
# Generate rawpy sRGB reference PNGs for all DNG files
python scripts/02_generate_rawpy_references.py
```

### 4. Inspect Your First RAW File

```bash
# Dump full metadata and channel statistics as JSON
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
```

### 5. Plot Histograms

```bash
# Generate dual-panel histograms (global + per-channel) for one or more files
python scripts/04_plot_raw_histogram.py data/raw/*.dng
```

### 6. Analyze ROIs

```bash
# Auto-select and analyze dark, midtone, and highlight ROIs
python scripts/05_analyze_raw_roi.py data/raw/*.dng
```

## Dependencies

| Package | Purpose |
|---|---|
| `numpy` | Array operations, statistics |
| `opencv-python` | Image I/O, color space conversions |
| `rawpy` | RAW/DNG file reading (libraw bindings) |
| `matplotlib` | Histogram and figure plotting |
| `scikit-image` | SSIM, advanced image metrics |
| `colour-science` | Color science calculations |
| `pyyaml` | Pipeline config parsing |
| `imageio` | Reference image writing |

## Scripts

All scripts are in `scripts/` and numbered in recommended execution order.

| # | Script | Input | Output | Purpose |
|---|---|---|---|---|
| 01 | `inspect_raw.py` | DNG path + optional `--pattern` | JSON to stdout | Full metadata dump: black/white levels, Bayer pattern, per-channel statistics |
| 02 | `generate_rawpy_references.py` | All `*.dng` in `data/raw/` | PNGs in `data/references/` | Generate rawpy sRGB reference images (the "answer key") |
| 03 | `dump_raw_metadata_table.py` | All `S*.dng` in `data/raw/` | Markdown table | Quick-reference metadata summary for the dataset |
| 04 | `plot_raw_histogram.py` | One or more DNG paths | PNGs in `reports/figures/` | Dual-panel log-scale histograms with black/white level markers |
| 05 | `analyze_raw_roi.py` | One or more DNG paths | PNG + JSON + MD report | Auto-select dark/midtone/highlight ROIs, generate annotated previews and statistics |
| 06 | `apply_blc.py` | DNG path + config | BLC-corrected RAW + before/after comparison | Apply black level subtraction, histogram comparison |
| 07 | `apply_dpc.py` | DNG path + config | DPC-corrected RAW + defect mask overlay | Static + gradient-based defect pixel detection and repair |
| 08 | `apply_demosaic.py` | DNG path + config | RGB image + comparison PNG | Bilinear and OpenCV demosaicing with visual comparison |
| 09 | `apply_awb.py` | DNG path + config | White-balanced RGB + before/after comparison | Gray World and ROI-based AWB |
| 10 | `apply_ccm.py` | DNG path + config | Color-corrected RGB + comparison PNG | Least-squares 3×3 CCM with Delta E metrics |
| 11 | `apply_gamma.py` | DNG path + config | Gamma-encoded RGB + comparison PNG | Standard sRGB gamma and custom gamma curves |
| 12 | `apply_tone_mapping.py` | DNG path + config | Tone-mapped RGB + comparison PNG | Reinhard and percentile-based tone mapping |
| 13 | `write_week4_summary.py` | Pipeline output files | Summary Markdown + composite comparison figure | Generate Week 4 comprehensive summary with full pipeline comparison |
| 14 | `apply_lsc.py` | DNG path + config | LSC-corrected RAW + falloff comparison | Radial and mesh-based lens shading correction |
| 15 | `evaluate_pipeline.py` | DNG paths + config | IQA metrics table + per-module ablation | Full pipeline PSNR/SSIM/MAE evaluation against rawpy reference |
| 16 | `close_mastery_gaps.py` | DNG paths + config | Enhanced module outputs + comparison reports | Week 6 mastery gap closure: static DPC, mesh LSC, OpenCV demosaic, ROI AWB, CCM Delta E, sRGB S-curve |

## Core Library (`soft_isp/`)

The `soft_isp` package provides shared utilities and ISP module implementations:

| Module | File | Description |
|---|---|---|
| Stats & utilities | `stats.py` | Bayer pattern inference, array statistics, Bayer channel splitting |
| Orientation | `orientation.py` | CFA pattern orientation detection |
| BLC | `blc.py` | Black level subtraction with per-channel offset support |
| DPC | `dpc.py` | Static (threshold) and gradient-based defect pixel correction |
| LSC | `lsc.py` | Radial falloff and mesh-based lens shading correction |
| Demosaic | `demosaic.py` | Bilinear interpolation and OpenCV-based demosaicing |
| AWB | `awb.py` | Gray World and ROI-based auto white balance |
| CCM | `ccm.py` | Least-squares 3×3 color correction matrix with Delta E evaluation |
| Gamma / Tone | `tone.py` | sRGB Gamma encoding, Reinhard and percentile tone mapping |

## Learning Roadmap (6 Weeks)

See `materials/stage1_start_here.md` for the detailed week-by-week plan.

| Week | Focus | Key Deliverable |
|---|---|---|
| 0.5 | Environment + sample download + first RAW read | 5 DNGs in `data/raw/` |
| 1 | RAW sensor intuition: metadata, histograms, ROIs | `reports/week1/raw_statistics.md`, histogram PNGs |
| 2 | Front-end corrections: BLC, DPC, LSC | Per-module notes + before/after comparisons |
| 3 | Demosaic + AWB | Working bilinear/AHD demosaic, gray-world AWB |
| 4 | CCM + Gamma + Tone Mapping | Complete end-to-end pipeline output |
| 5 | IQA, ablation, report | PSNR/SSIM/DeltaE table, rawpy comparison, failure analysis |
| 6 | Polish + interview prep | Final report, per-module interview answers |

Each ISP module must answer 7 questions (from `materials/module_study_template.md`):

1. What is the exact input (data domain, range, shape)?
2. What is the exact output?
3. What physical or perceptual problem does this module solve?
4. What are the core assumptions and when do they break?
5. How does each parameter affect the output (with visual examples)?
6. How do you verify this module is correct (independent of downstream modules)?
7. What are the failure scenarios and how do you detect them?

## Data Conventions

- **Input RAW/DNG files** → `data/raw/` (gitignored — large binaries)
- **Reference outputs** (rawpy, Lightroom, LibRaw) → `data/references/`
- **Generated figures** (histograms, ROI previews, comparison images) → `reports/figures/`
- **Per-sample statistics** → `reports/raw_stats/`
- **Weekly reports** → `reports/`

## Current Deliverables

| Deliverable | Status | Description |
|---|---|---|
| RAW sample download script | ✅ Done | PowerShell script for FiveK starter DNGs |
| RAW metadata inspection | ✅ Done | `01_inspect_raw.py` + T01-T14 per-sample JSON dumps |
| Reference image generation | ✅ Done | `02_generate_rawpy_references.py` + T01-T14 reference PNGs |
| Metadata summary table | ✅ Done | `03_dump_raw_metadata_table.py` → Markdown table |
| Histogram plots | ✅ Done | S01, S03, S05 histograms with black/white level annotations |
| ROI analysis | ✅ Done | Dark/midtone/highlight ROIs for S01, S03, S05 with JSON + preview |
| Week 1 report | ✅ Done | `reports/week1/raw_statistics.md` + `reports/week1/roi_analysis.md` |
| BLC module | ✅ Done | `soft_isp/blc.py` + `scripts/06_apply_blc.py` + `reports/week2/blc_report.md` |
| DPC module | ✅ Done | `soft_isp/dpc.py` + `scripts/07_apply_dpc.py` + `reports/week2/dpc_report.md` |
| LSC module | ✅ Done | `soft_isp/lsc.py` + `scripts/14_apply_lsc.py` + `reports/week2/lsc_report.md` |
| Demosaic module | ✅ Done | `soft_isp/demosaic.py` + `scripts/08_apply_demosaic.py` + `reports/week3/demosaic_report.md` |
| AWB module | ✅ Done | `soft_isp/awb.py` + `scripts/09_apply_awb.py` + `reports/week3/awb_report.md` |
| CCM module | ✅ Done | `soft_isp/ccm.py` + `scripts/10_apply_ccm.py` + `reports/week4/ccm_report.md` |
| Gamma module | ✅ Done | `soft_isp/tone.py` + `scripts/11_apply_gamma.py` + `reports/week4/gamma_report.md` |
| Tone Mapping module | ✅ Done | `soft_isp/tone.py` + `scripts/12_apply_tone_mapping.py` + `reports/week4/tone_mapping_report.md` |
| Week 4 summary | ✅ Done | `scripts/13_write_week4_summary.py` + `reports/week4/summary.md` |
| Pipeline evaluation | ✅ Done | `scripts/15_evaluate_pipeline.py` + `reports/week5/iqa_ablation_report.md` |
| Mastery gap closure | ✅ Done | `scripts/16_close_mastery_gaps.py` + `reports/week6/mastery_gap_closure_report.md` |
| Stage 1 final report | ✅ Done | `reports/stage1_report.md` |
| Interview prep | ✅ Done | `reports/interview/isp_algorithm_questions_week1_3.md` + `reports/interview/isp_interview_deep_notes_week1_4.md` |

## License

This project is part of a personal learning portfolio. All original code is available for reference and educational use.
