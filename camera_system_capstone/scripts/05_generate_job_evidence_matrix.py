#!/usr/bin/env python3
"""Generate the Qualcomm 3083325 evidence matrix and capstone report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import (
    EVIDENCE_FIELDS,
    build_evidence_rows,
    read_csv,
    render_capstone_report,
    write_csv,
    write_supporting_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "job_evidence_matrix.csv")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports" / "qualcomm_3083325_capstone_report.md",
    )
    args = parser.parse_args()
    iq_rows = read_csv(ROOT / "outputs" / "iq_summary.csv")
    system_rows = read_csv(ROOT / "outputs" / "system_profile_summary.csv")
    multicamera_rows = read_csv(ROOT / "outputs" / "multicamera_summary.csv")
    evidence = build_evidence_rows(iq_rows, system_rows, multicamera_rows)
    write_csv(args.output, EVIDENCE_FIELDS, evidence)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_capstone_report(evidence), encoding="utf-8")
    write_supporting_reports(args.report.parent, evidence)
    print(f"job_evidence_matrix={args.output} rows={len(evidence)} report={args.report}")


if __name__ == "__main__":
    main()
