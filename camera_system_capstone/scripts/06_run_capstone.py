#!/usr/bin/env python3
"""Run the CPU-safe Capstone contract and evidence pipeline in one command."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import (
    EVIDENCE_FIELDS,
    build_evidence_rows,
    generate_iq_summary,
    generate_multicamera_summary,
    generate_system_profile_summary,
    render_capstone_report,
    validate_repository,
    write_csv,
    write_supporting_reports,
)


REPO_ROOT = ROOT.parent


def refresh_cpu_safe_stage_outputs() -> None:
    """Run stage-owned generators; Capstone never reimplements their algorithms."""
    commands = [
        [sys.executable, "stage1_soft_isp/scripts/20_evaluate_camera_iq.py"],
        [sys.executable, "stage1_soft_isp/scripts/22_run_tuning_sweep.py"],
        [sys.executable, "stage2_ai_isp/scripts/23_prepare_camera_scene_comparison.py"],
        [sys.executable, "stage2_ai_isp/scripts/24_evaluate_camera_scenes.py"],
        [
            sys.executable,
            "stage2_ai_isp/scripts/25_export_scene_failure_matrix.py",
            "stage2_ai_isp/reports/figures/camera_scene_evaluation/per_sample_metrics.csv",
        ],
        [sys.executable, "stage4_deploy_isp/scripts/14_generate_quality_latency_memory_matrix.py"],
    ]
    for command in commands:
        subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="Refresh CPU-safe stage evidence; do not launch GPU/TensorRT or retrain models.",
    )
    parser.add_argument(
        "--skip-stage-refresh",
        action="store_true",
        help="Only aggregate already tracked stage outputs.",
    )
    args = parser.parse_args()
    if not args.skip_stage_refresh:
        refresh_cpu_safe_stage_outputs()
    errors, warnings = validate_repository()
    validation = {"status": "pass" if not errors else "fail", "errors": errors, "warnings": warnings}
    output_root = ROOT / "outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "asset_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if errors:
        raise SystemExit("\n".join(errors))

    iq_rows = generate_iq_summary(output_root / "iq_summary.csv")
    multicamera_rows = generate_multicamera_summary(output_root / "multicamera_summary.csv")
    system_rows = generate_system_profile_summary(output_root / "system_profile_summary.csv")
    evidence = build_evidence_rows(iq_rows, system_rows, multicamera_rows)
    write_csv(output_root / "job_evidence_matrix.csv", EVIDENCE_FIELDS, evidence)
    report = ROOT / "reports" / "qualcomm_3083325_capstone_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_capstone_report(evidence), encoding="utf-8")
    write_supporting_reports(report.parent, evidence)
    mode = "cpu-only" if args.cpu_only else "tracked-evidence"
    print(f"capstone=pass mode={mode} warnings={len(warnings)} evidence_rows={len(evidence)} report={report}")


if __name__ == "__main__":
    main()
