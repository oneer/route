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
│   └── download_fivek_starter.ps1  # Download 5 MIT-Adobe FiveK starter DNGs
├── soft_isp/
│   ├── __init__.py               # Package init
│   └── stats.py                  # Core utilities: Bayer inference, stats, splitting
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

## Core Library (`soft_isp/`)

The `soft_isp` package provides shared utilities imported by all scripts:

| Function | File | Description |
|---|---|---|
| `bayer_pattern_from_rawpy()` | `stats.py` | Infer standard Bayer string (RGGB/BGGR/GRBG/GBRG) from rawpy metadata |
| `describe_array()` | `stats.py` | Compute shape, dtype, min, max, mean, std, p01, p50, p99 for any array |
| `split_bayer()` | `stats.py` | Split Bayer mosaic into R, Gr, Gb, B sub-arrays via stride slicing |

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
| RAW sample download script | Done | PowerShell script for 5 FiveK starter DNGs |
| RAW metadata inspection | Done | `01_inspect_raw.py` + 5 per-sample JSON dumps |
| Reference image generation | Done | `02_generate_rawpy_references.py` + 5 reference PNGs |
| Metadata summary table | Done | `03_dump_raw_metadata_table.py` → Markdown table |
| Histogram plots | Done | S01, S03, S05 histograms with black/white level annotations |
| ROI analysis | Done | Dark/midtone/highlight ROIs for S01, S03, S05 with JSON + preview |
| Week 1 report | Done | `reports/week1/raw_statistics.md` + `reports/week1/roi_analysis.md` |
| BLC module | Pending | Week 2 |
| DPC module | Pending | Week 2 |
| LSC module | Pending | Week 2 |
| Demosaic module | Pending | Week 3 |
| AWB module | Pending | Week 3 |
| CCM module | Pending | Week 4 |
| Gamma/Tone module | Pending | Week 4 |
| IQA + final report | Pending | Week 5-6 |

## License

This project is part of a personal learning portfolio. All original code is available for reference and educational use.
