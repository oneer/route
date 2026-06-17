from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def psnr(pred: np.ndarray, target: np.ndarray, eps: float = 1e-8) -> float:
    mse = float(np.mean((pred - target) ** 2))
    return float(10.0 * np.log10(1.0 / max(mse, eps)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare C++ ORT output against Python ORT reference.")
    parser.add_argument("--cpp", default="stage4_deploy_isp/outputs/week2_cpp_io/cpp_outputs/pair_00001_cpp_output.ppm")
    parser.add_argument("--ref", default="stage4_deploy_isp/outputs/week2_cpp_io/ort_reference_png/pair_00001_ort_reference.png")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cpp = load_rgb(Path(args.cpp))
    ref = load_rgb(Path(args.ref))
    err = np.abs(cpp - ref)
    print(
        {
            "max_abs_error": float(err.max()),
            "mean_abs_error": float(err.mean()),
            "psnr": psnr(cpp, ref),
        }
    )


if __name__ == "__main__":
    main()

