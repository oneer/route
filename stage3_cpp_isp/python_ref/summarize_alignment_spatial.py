"""汇总 C++/Python 对齐的空间误差，用 CSV 形式服务 alignment report。"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "figures" / "alignment_spatial_summary.csv"


def read_cpf32(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        if f.readline().strip() != b"CPF32":
            raise ValueError(f"invalid CPF32 magic: {path}")
        width, height, channels = map(int, f.readline().decode("ascii").split())
        data = np.frombuffer(f.read(), dtype="<f4")
    expected = width * height * channels
    if data.size != expected:
        raise ValueError(f"payload mismatch: {path}")
    return data.reshape(height, width, channels)


def summarize(name: str, reference_path: Path, candidate_path: Path) -> dict[str, object]:
    reference = read_cpf32(reference_path)
    candidate = read_cpf32(candidate_path)
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch for {name}")

    error = np.abs(candidate.astype(np.float64) - reference.astype(np.float64))
    flat_index = int(np.argmax(error))
    y, x, c = np.unravel_index(flat_index, error.shape)
    border_mask = np.zeros(error.shape[:2], dtype=bool)
    border_mask[[0, -1], :] = True
    border_mask[:, [0, -1]] = True
    border_values = error[border_mask]
    interior_values = error[~border_mask]
    border_mean = float(np.mean(border_values)) if border_values.size else 0.0
    interior_mean = float(np.mean(interior_values)) if interior_values.size else 0.0
    concentration = "border" if border_mean > interior_mean * 2.0 else "not_border_concentrated"

    return {
        "case": name,
        "height": error.shape[0],
        "width": error.shape[1],
        "channels": error.shape[2],
        "max_abs_error": float(error[y, x, c]),
        "max_y": y,
        "max_x": x,
        "max_c": c,
        "border_mean_abs_error": border_mean,
        "interior_mean_abs_error": interior_mean,
        "nonzero_values": int(np.count_nonzero(error)),
        "concentration": concentration,
    }


def main() -> None:
    cases = [
        (
            "week4_bilateral_lut",
            ROOT / "data/week4_alignment/week4_bilateral_python_ref.cpf32",
            ROOT / "data/week4_alignment/week4_bilateral_cpp_lut.cpf32",
        ),
        (
            "week4_bilateral_tile",
            ROOT / "data/week4_alignment/week4_bilateral_python_ref.cpf32",
            ROOT / "data/week4_alignment/week4_bilateral_cpp_tile.cpf32",
        ),
        (
            "week4_bilateral_rows",
            ROOT / "data/week4_alignment/week4_bilateral_python_ref.cpf32",
            ROOT / "data/week4_alignment/week4_bilateral_cpp_rows.cpf32",
        ),
        (
            "week4_bilateral_tiles",
            ROOT / "data/week4_alignment/week4_bilateral_python_ref.cpf32",
            ROOT / "data/week4_alignment/week4_bilateral_cpp_tiles.cpf32",
        ),
        (
            "week5_reinhard_rgb",
            ROOT / "data/week5_alignment/week5_python_reinhard_rgb.cpf32",
            ROOT / "data/week5_alignment/week5_cpp_reinhard_rgb.cpf32",
        ),
        (
            "week5_reinhard_luma",
            ROOT / "data/week5_alignment/week5_python_reinhard_luma.cpf32",
            ROOT / "data/week5_alignment/week5_cpp_reinhard_luma.cpf32",
        ),
        (
            "week5_filmic_luma",
            ROOT / "data/week5_alignment/week5_python_filmic_luma.cpf32",
            ROOT / "data/week5_alignment/week5_cpp_filmic_luma.cpf32",
        ),
        (
            "week5_scurve_luma",
            ROOT / "data/week5_alignment/week5_python_scurve_luma.cpf32",
            ROOT / "data/week5_alignment/week5_cpp_scurve_luma.cpf32",
        ),
        (
            "week6_reinhard_10_10",
            ROOT / "data/week6_alignment/week6_python_reinhard_10_10.cpf32",
            ROOT / "data/week6_alignment/week6_cpp_reinhard_10_10.cpf32",
        ),
        (
            "week6_reinhard_12_12",
            ROOT / "data/week6_alignment/week6_python_reinhard_12_12.cpf32",
            ROOT / "data/week6_alignment/week6_cpp_reinhard_12_12.cpf32",
        ),
        (
            "week6_filmic_lut",
            ROOT / "data/week6_alignment/week6_python_filmic_12_12.cpf32",
            ROOT / "data/week6_alignment/week6_cpp_filmic_12_12.cpf32",
        ),
        (
            "week6_scurve_12_12",
            ROOT / "data/week6_alignment/week6_python_scurve_12_12.cpf32",
            ROOT / "data/week6_alignment/week6_cpp_scurve_12_12.cpf32",
        ),
        (
            "week7_local_tone_mapping",
            ROOT / "data/week7_alignment/week7_python_ltm_bilateral.cpf32",
            ROOT / "data/week7_alignment/week7_cpp_ltm_bilateral.cpf32",
        ),
        (
            "week7_hdr_merge",
            ROOT / "data/week7_alignment/week7_python_hdr_merge.cpf32",
            ROOT / "data/week7_alignment/week7_cpp_hdr_merge.cpf32",
        ),
    ]
    rows = [summarize(name, reference, candidate) for name, reference, candidate in cases]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
