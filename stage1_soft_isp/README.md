# Stage 1: RAW Foundations and Explainable Soft-ISP

[中文](README_CN.md)

Stage 1 builds practical understanding of RAW data, traditional ISP modules, verification, and debugging. The repository contains completed reference implementations and historical experiment reports, but mastery must be demonstrated through exercises, tests, and an independent reimplementation.

## Start Here

1. [Prerequisites](materials/prerequisites.md)
2. [Environment setup](materials/environment_setup.md)
3. [Learning route](materials/stage1_start_here.md)
4. [Exercises](exercises/README.md)
5. [Debugging guide](materials/debugging_guide.md)

## Verified Quick Start

```powershell
cd stage1_soft_isp
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
python scripts/17_run_pipeline.py data/raw/T01_a0006-IMG_2787.dng
```

The config-driven pipeline reads [configs/default.yaml](configs/default.yaml), supports module switches, and saves inspectable intermediate summaries.

Real DNG metadata is tracked separately from rendering assumptions. Regenerate and validate the machine-readable contract after changing RAW samples:

```powershell
python scripts/19_generate_raw_metadata_manifest.py
```

The contract records file hashes, dimensions, Bayer layout, black/white levels, orientation, white balance and color matrices. ISO/exposure remain explicitly unknown until a separate EXIF audit is added.

## Learning Pipeline

```text
RAW -> BLC -> DPC -> learning LSC -> Bilinear Demosaic
    -> Gray World AWB -> approximate metadata CCM
    -> percentile/Reinhard Tone -> Gamma -> preview
```

Important boundaries:

- rawpy output is a mature rendering reference, not ground truth;
- LSC, DPC, AWB, and CCM are explainable learning baselines, not production calibration;
- OpenCV edge-aware demosaicing is a comparison baseline, not AHD;
- metrics measure similarity to the selected reference, not absolute image quality.

## Project Areas

- `soft_isp/`: small algorithm implementations and the unified pipeline.
- `scripts/`: historical per-module experiments plus `17_run_pipeline.py`.
- `tests/`: synthetic unit tests.
- `exercises/`: answer-free tasks, debugging challenges, and final project.
- `materials/`: prerequisites, setup, debugging, resources, and study templates.
- `reports/`: completed experiment archive; consult it after attempting exercises.

## Multi-file Commands on PowerShell

Scripts 04–09 expand globs internally:

```powershell
python scripts/04_plot_raw_histogram.py "data/raw/T*.dng"
python scripts/05_analyze_raw_roi.py "data/raw/T*.dng"
```

## Completion Standard

You have completed Stage 1 only when you can:

- inspect an unfamiliar DNG and explain its data contract;
- implement and test the core modules without copying the reference;
- predict parameter changes before running them;
- diagnose Bayer, range, orientation, and color-order bugs;
- rebuild a simplified configurable pipeline in a clean directory;
- explain one failure case and the tradeoffs of the selected algorithm.

See [the final project](exercises/final_project.md) and [Git evidence guide](materials/git_evidence_guide.md).

## Data and Optional OpenISP Dependencies

The 14 FiveK DNG files, generated PNGs, and PDFs are currently tracked using Git LFS. Run `git lfs pull` after cloning.

The main project uses `requirements.txt`. OpenISP reference modules that import SciPy use `requirements-openisp.txt`.
