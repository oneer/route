# Stage 1: RAW Foundations and Explainable Soft-ISP

[中文](README_CN.md)

Stage 1 builds practical understanding of RAW data, traditional ISP modules, verification, and debugging. The repository contains completed reference implementations and historical experiment reports, but mastery must be demonstrated through exercises, tests, and an independent reimplementation.

## Qualcomm Interview Track

- [Job ID 3083325 readiness and gap audit](../study-roadmap/高通3083325-Camera-ISP-Algorithm-System-Engineer定向提升报告.md#十四2026-07-19-面试就绪审计与二次补强)
- [Week 6: 3A timing, Staggered HDR, Quad Bayer and TNR interview module](reports/week6/mastery_gap_closure_report.md#16-高通岗位补强从单帧-soft-isp-到连续-camera-系统)
- [Cross-stage Camera Systems capstone](../camera_system_capstone/reports/qualcomm_3083325_capstone_report.md)

The new interview material improves conceptual readiness only. Self-captured RAW, dark/flat/ColorChecker/slanted-edge data, continuous 3A/TNR, and Snapdragon evidence remain explicitly unverified.

## Start Here

1. [Prerequisites](materials/prerequisites.md)
2. [Environment setup](materials/environment_setup.md)
3. [Learning route](materials/stage1_start_here.md)
4. [Exercises](exercises/README.md)
5. [Debugging guide](materials/debugging_guide.md)
6. [Report navigation](reports/README.md)
7. [References](reports/references.md)

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
- `tests/`: 35 synthetic unit tests, including LSC gain/clip, orientation/ROI transforms, calibration contracts, and IQ proxy sanity checks.
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

For report-based study, follow [the weekly report navigation](reports/README.md) and use [the tutorial audit](reports/stage1_tutorial_audit.md) to verify that every conclusion has an input contract, runnable command, intermediate artifact, failure analysis, and evidence boundary. The reports are reference tutorials; completing them still requires running the exercises and explaining one result without reading the supplied answer.

## Data and Optional OpenISP Dependencies

The 14 FiveK DNG files, generated PNGs, and PDFs are currently tracked using Git LFS. Run `git lfs pull` after cloning.

The main project uses `requirements.txt`. OpenISP reference modules that import SciPy use `requirements-openisp.txt`.

## Camera IQ role backfill

Run `python scripts/20_evaluate_camera_iq.py` for manifest-driven exposure
percentiles, clipping, natural-image ROI SNR, approximate dynamic range, and
MTF50 proxy output. Run `python scripts/21_calibrate_colorchecker.py <patch.csv>`
to fit a 3x3 CCM from measured/reference linear-RGB patches.

Run `python scripts/22_run_tuning_sweep.py` to reproduce three controlled
AWB-filter, bilateral-denoise, and tone/highlight parameter sweeps. The command
writes the full metric table plus selected settings and three rejected failure
cases. It uses deterministic perturbations of a public-DNG sRGB rendering so it
validates the tuning workflow without claiming self-captured Camera tuning.

The tracked public DNG result is proxy evidence, not self-captured lab IQ. The
ColorChecker template is not evidence until real measured patches are supplied.
