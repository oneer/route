"""Job evidence CSV and final report schema tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
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
    render_supporting_reports,
    write_csv,
)


class ReportSchemaTests(unittest.TestCase):
    def test_evidence_matrix_has_required_status_and_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            iq = generate_iq_summary(root / "iq.csv")
            multicamera = generate_multicamera_summary(root / "multicamera.csv")
            system = generate_system_profile_summary(root / "system.csv")
            rows = build_evidence_rows(iq, system, multicamera)
            write_csv(root / "evidence.csv", EVIDENCE_FIELDS, rows)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["status"] and row["boundary"] for row in rows))
        self.assertEqual(
            next(row for row in rows if row["jd_requirement"].startswith("Multi"))["status"],
            "verified_synthetic",
        )

    def test_supporting_reports_cover_all_interview_evidence_areas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            iq = generate_iq_summary(root / "iq.csv")
            multicamera = generate_multicamera_summary(root / "multicamera.csv")
            system = generate_system_profile_summary(root / "system.csv")
            reports = render_supporting_reports(build_evidence_rows(iq, system, multicamera))
        self.assertEqual(
            set(reports),
            {
                "iq_system_report.md",
                "multicamera_report.md",
                "system_optimization_report.md",
                "failure_case_report.md",
            },
        )
        self.assertTrue(all("Boundary" in content or "边界" in content for content in reports.values()))

    def test_report_contains_all_twelve_sections_and_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            iq = generate_iq_summary(root / "iq.csv")
            multicamera = generate_multicamera_summary(root / "multicamera.csv")
            system = generate_system_profile_summary(root / "system.csv")
            report = render_capstone_report(build_evidence_rows(iq, system, multicamera))
        for number in range(1, 13):
            self.assertIn(f"## {number}.", report)
        self.assertIn("not_run", report)
        self.assertIn("不代表商业量产", report)
        self.assertNotIn("Snapdragon 实测", report)


if __name__ == "__main__":
    unittest.main()
