#!/usr/bin/env python3
"""Generate and validate a synthetic Python/C++ fusion golden pair."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def write_cpf32(path: Path, array: np.ndarray) -> None:
    height, width, channels = array.shape
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(f"CPF32\n{width} {height} {channels}\n".encode("ascii"))
        handle.write(np.asarray(array, dtype="<f4").tobytes(order="C"))


def read_cpf32(path: Path) -> np.ndarray:
    with path.open("rb") as handle:
        if handle.readline().strip() != b"CPF32":
            raise ValueError(f"invalid CPF32: {path}")
        width, height, channels = map(int, handle.readline().split())
        return np.frombuffer(handle.read(), dtype="<f4").reshape(height, width, channels)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpp-output", type=Path)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "multicamera")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "multicamera_fusion_alignment.csv")
    args = parser.parse_args()

    height, width = 32, 64
    x = np.linspace(0.1, 0.7, width, dtype=np.float32)
    y = np.linspace(0.0, 0.15, height, dtype=np.float32)[:, None]
    base = x[None, :] + y
    left = np.stack((base, base * 0.8, base * 0.6), axis=2)
    injected_gains = np.array([1.2, 0.8, 1.1], dtype=np.float32)
    right = left / injected_gains.reshape(1, 1, 3)
    x_begin, x_end = 16, 48
    estimated = np.sum(left[:, x_begin:x_end], axis=(0, 1)) / np.sum(right[:, x_begin:x_end], axis=(0, 1))
    matched = np.clip(right * estimated.reshape(1, 1, 3), 0.0, 1.0)
    weights = np.zeros(width, dtype=np.float32)
    weights[x_begin:x_end] = np.arange(x_end - x_begin, dtype=np.float32) / float(x_end - x_begin - 1)
    weights[x_end:] = 1.0
    reference = left * (1.0 - weights[None, :, None]) + matched * weights[None, :, None]

    write_cpf32(args.data_dir / "fusion_left.cpf32", left)
    write_cpf32(args.data_dir / "fusion_right.cpf32", right)
    write_cpf32(args.data_dir / "fusion_python_reference.cpf32", reference)
    rows = [
        ("mean_color_delta_before", float(np.mean(np.abs(np.mean(left[:, x_begin:x_end], axis=(0, 1)) - np.mean(right[:, x_begin:x_end], axis=(0, 1)))))),
        ("mean_color_delta_after", float(np.mean(np.abs(left[:, x_begin:x_end] - matched[:, x_begin:x_end])))),
    ]
    if args.cpp_output:
        cpp = read_cpf32(args.cpp_output)
        error = np.abs(cpp.astype(np.float64) - reference.astype(np.float64))
        rows.extend([
            ("max_cpp_python_abs_error", float(np.max(error))),
            ("mean_cpp_python_abs_error", float(np.mean(error))),
            ("threshold", 1.0e-6),
            ("passed", float(np.max(error) <= 1.0e-6)),
        ])
        if float(np.max(error)) > 1.0e-6:
            raise SystemExit("C++ fusion output does not align with Python reference")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        writer.writerows(rows)
    print(f"fusion_reference={args.data_dir / 'fusion_python_reference.cpf32'} cpp_checked={bool(args.cpp_output)}")


if __name__ == "__main__":
    main()
