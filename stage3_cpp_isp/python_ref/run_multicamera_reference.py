#!/usr/bin/env python3
"""Generate synthetic homography reference and explicit failure diagnostics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _project(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    homogeneous = np.column_stack((points, np.ones(len(points))))
    projected = homogeneous @ matrix.T
    return projected[:, :2] / projected[:, 2:3]


def _read_key_values(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["key"]: float(row["value"]) for row in csv.DictReader(handle)}


def _write_key_values(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpp-output", type=Path)
    parser.add_argument("--correspondences", type=Path, default=ROOT / "data" / "multicamera" / "synthetic_correspondences.csv")
    parser.add_argument("--reference", type=Path, default=ROOT / "reports" / "multicamera_geometry_reference.csv")
    parser.add_argument("--alignment", type=Path, default=ROOT / "reports" / "multicamera_geometry_alignment.csv")
    parser.add_argument("--failures", type=Path, default=ROOT / "reports" / "multicamera_failure_cases.csv")
    args = parser.parse_args()

    source = np.array([[0, 0], [100, 0], [0, 80], [100, 80], [50, 20], [30, 60], [80, 40]], dtype=np.float64)
    expected = np.array([[1.02, 0.03, 12.0], [-0.02, 0.98, 7.0], [0.0002, -0.0001, 1.0]], dtype=np.float64)
    destination = _project(expected, source)
    args.correspondences.parent.mkdir(parents=True, exist_ok=True)
    with args.correspondences.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_x", "source_y", "destination_x", "destination_y"])
        writer.writerows(np.column_stack((source, destination)))

    reference, _ = cv2.findHomography(source, destination, method=0)
    reference /= reference[2, 2]
    errors = np.linalg.norm(_project(reference, source) - destination, axis=1)
    _write_key_values(
        args.reference,
        [(f"h{row}{column}", float(reference[row, column])) for row in range(3) for column in range(3)]
        + [("valid_points", float(len(source))), ("mean_reprojection_error_px", float(np.mean(errors))),
           ("rms_reprojection_error_px", float(np.sqrt(np.mean(errors ** 2)))), ("max_reprojection_error_px", float(np.max(errors)))],
    )

    shifted = destination.copy()
    shifted[-1] += np.array([6.0, -4.0])
    shifted_h, _ = cv2.findHomography(source, shifted, method=0)
    parallax_error = np.linalg.norm(_project(shifted_h, source) - shifted, axis=1)
    low_texture = np.array([[0, 0], [1, 0], [2, 0], [3, 0]], dtype=np.float64)
    low_texture_h, _ = cv2.findHomography(low_texture, low_texture, method=0)
    left = np.tile(np.linspace(0.1, 0.9, 64, dtype=np.float32), (32, 1))
    right = left.copy()
    right[10:22, 28:40] = 1.0 - right[10:22, 28:40]
    motion_seam_delta = float(np.mean(np.abs(left[:, 32] - right[:, 32])))
    with args.failures.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["failure_case", "injection", "metric", "value", "diagnosis", "boundary"])
        writer.writerow(["near_parallax", "one correspondence displaced by 6/-4 px", "max_reprojection_error_px", float(np.max(parallax_error)), "single homography cannot explain depth-dependent displacement", "synthetic diagnostic"])
        writer.writerow(["motion_overlap", "local overlap patch changed", "seam_delta", motion_seam_delta, "moving content creates a visible seam/ghost risk", "synthetic diagnostic"])
        writer.writerow(["low_texture", "four collinear correspondences", "homography_available", 0 if low_texture_h is None else 1, "geometry is degenerate and must be rejected", "synthetic diagnostic"])

    if args.cpp_output:
        cpp = _read_key_values(args.cpp_output)
        cpp_h = np.array([[cpp[f"h{row}{column}"] for column in range(3)] for row in range(3)])
        max_matrix_error = float(np.max(np.abs(cpp_h / cpp_h[2, 2] - reference)))
        _write_key_values(args.alignment, [
            ("max_homography_abs_error", max_matrix_error),
            ("cpp_mean_reprojection_error_px", cpp["mean_reprojection_error_px"]),
            ("opencv_mean_reprojection_error_px", float(np.mean(errors))),
            ("threshold", 1.0e-6),
            ("passed", float(max_matrix_error <= 1.0e-6)),
        ])
        if max_matrix_error > 1.0e-6:
            raise SystemExit(f"C++/OpenCV homography mismatch: {max_matrix_error}")
    print(f"correspondences={args.correspondences} failures={args.failures} cpp_checked={bool(args.cpp_output)}")


if __name__ == "__main__":
    main()
