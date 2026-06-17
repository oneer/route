from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from make_test_vectors import write_cpf32
from tone_mapping_ref import (
    apply_gamma,
    filmic_curve,
    luminance,
    percentile_exposure,
    reinhard_curve,
    scurve,
    tone_map_luminance,
)
from run_week5_tone_mapping import make_hdr_like_scene


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week6"
ALIGN_DIR = ROOT / "data" / "week6_alignment"
BUILD_DIR = ROOT / "build"


def save_png(path: Path, image: np.ndarray) -> None:
    image = np.clip(image, 0.0, 1.0)
    Image.fromarray((image * 255.0 + 0.5).astype(np.uint8)).save(path)


def read_cpf32(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        magic = f.readline().strip()
        if magic != b"CPF32":
            raise ValueError(f"bad CPF32 magic: {path}")
        width, height, channels = map(int, f.readline().decode("ascii").split())
        data = np.frombuffer(f.read(), dtype="<f4").copy()
    return data.reshape(height, width, channels)


def apply_curve(x: np.ndarray, curve: str) -> np.ndarray:
    if curve == "reinhard":
        return reinhard_curve(x)
    if curve == "filmic":
        return filmic_curve(x)
    if curve == "scurve":
        return scurve(x)
    raise ValueError(curve)


def make_lut(curve: str, input_bits: int, output_bits: int, input_max: float) -> np.ndarray:
    input_max_code = (1 << input_bits) - 1
    output_max_code = (1 << output_bits) - 1
    x = np.linspace(0.0, input_max, input_max_code + 1, dtype=np.float32)
    y = apply_curve(x, curve)
    return np.clip(np.rint(y * output_max_code), 0, output_max_code).astype(np.uint32)


def apply_lut_scalar(x: np.ndarray, lut: np.ndarray, input_bits: int, output_bits: int, input_max: float) -> np.ndarray:
    input_max_code = (1 << input_bits) - 1
    output_max_code = (1 << output_bits) - 1
    code = np.rint(np.clip(x, 0.0, input_max) / input_max * input_max_code).astype(np.int64)
    code = np.clip(code, 0, input_max_code)
    return (lut[code] / output_max_code).astype(np.float32)


def tone_map_luma_lut(
    image: np.ndarray,
    curve: str,
    exposure: float,
    input_bits: int,
    output_bits: int,
    input_max: float,
) -> np.ndarray:
    lut = make_lut(curve, input_bits, output_bits, input_max)
    y = luminance(image)
    mapped_y = apply_lut_scalar(y * exposure, lut, input_bits, output_bits, input_max)
    scale = mapped_y / np.maximum(y, 1e-6)
    return np.clip(image * scale[..., None], 0.0, 1.0).astype(np.float32)


def metrics(reference: np.ndarray, output: np.ndarray, threshold: float = 2e-3) -> dict[str, float | int]:
    diff = np.abs(reference.astype(np.float64) - output.astype(np.float64))
    mse = float(np.mean(diff * diff))
    psnr = math.inf if mse == 0.0 else 20.0 * math.log10(1.0 / math.sqrt(mse))
    return {
        "max_abs_error": float(np.max(diff)),
        "mean_abs_error": float(np.mean(diff)),
        "rmse": math.sqrt(mse),
        "psnr": psnr,
        "failed_values": int(np.sum(diff > threshold)),
        "total_values": int(diff.size),
    }


def plot_error_curves() -> list[dict[str, float | int | str]]:
    x = np.linspace(0.0, 8.0, 4096, dtype=np.float32)
    rows: list[dict[str, float | int | str]] = []
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, curve in zip(axes, ["reinhard", "filmic", "scurve"]):
        ref = apply_curve(x, curve)
        for input_bits in [8, 10, 12, 14]:
            lut = make_lut(curve, input_bits, 12, 8.0)
            approx = apply_lut_scalar(x, lut, input_bits, 12, 8.0)
            err = np.abs(ref - approx)
            ax.plot(x, err, label=f"{input_bits}-bit in")
            row = {"curve": curve, "input_bits": input_bits, "output_bits": 12}
            row.update(metrics(ref, approx, threshold=1.0 / 4095.0))
            rows.append(row)
        ax.set_title(curve)
        ax.set_xlabel("curve input")
        ax.set_ylabel("absolute error")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week6_lut_error_curves.png", dpi=170)
    plt.close(fig)
    return rows


def plot_banding(scene: np.ndarray, exposure: float) -> None:
    height, width = 96, 512
    gradient = np.tile(np.linspace(0.0, 0.22, width, dtype=np.float32), (height, 1))
    shadow = np.dstack([gradient * 1.08, gradient, gradient * 0.82]).astype(np.float32)
    float_out = tone_map_luminance(shadow, "scurve", exposure=1.0)
    lut_8 = tone_map_luma_lut(shadow, "scurve", 1.0, 8, 8, 1.0)
    lut_10 = tone_map_luma_lut(shadow, "scurve", 1.0, 10, 10, 1.0)
    lut_12 = tone_map_luma_lut(shadow, "scurve", 1.0, 12, 12, 1.0)

    images = [
        ("float", float_out),
        ("8-bit LUT", lut_8),
        ("10-bit LUT", lut_10),
        ("12-bit LUT", lut_12),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(14, 5.2))
    for col, (title, image) in enumerate(images):
        axes[0, col].imshow(apply_gamma(image, 2.2))
        axes[0, col].set_title(title, fontsize=9)
        axes[0, col].axis("off")
        error = np.abs(luminance(float_out) - luminance(image))
        axes[1, col].imshow(np.clip(error * 40.0, 0.0, 1.0), cmap="magma")
        axes[1, col].set_title("error x40", fontsize=9)
        axes[1, col].axis("off")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week6_shadow_banding_compare.png", dpi=170)
    plt.close(fig)

    output = tone_map_luma_lut(scene, "scurve", exposure, 12, 12, 8.0)
    save_png(FIGURE_DIR / "week6_scurve_lut_scene.png", apply_gamma(output, 2.2))


def read_compare_output(text: str) -> dict[str, str]:
    row: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            row[key.strip()] = value.strip()
    return row


def run_cpp_alignment(scene: np.ndarray, exposure: float) -> list[dict[str, str]]:
    input_path = ALIGN_DIR / "week6_tone_input.cpf32"
    write_cpf32(input_path, scene)
    rows: list[dict[str, str]] = []
    cases = [
        ("reinhard", 10, 10),
        ("reinhard", 12, 12),
        ("filmic", 12, 12),
        ("scurve", 12, 12),
    ]
    for curve, input_bits, output_bits in cases:
        reference = tone_map_luma_lut(scene, curve, exposure, input_bits, output_bits, 8.0)
        ref_path = ALIGN_DIR / f"week6_python_{curve}_{input_bits}_{output_bits}.cpf32"
        out_path = ALIGN_DIR / f"week6_cpp_{curve}_{input_bits}_{output_bits}.cpf32"
        write_cpf32(ref_path, reference)
        subprocess.run(
            [
                str(BUILD_DIR / "run_tone_lut.exe"),
                str(input_path),
                str(out_path),
                curve,
                "luma",
                f"{exposure:.9f}",
                str(input_bits),
                str(output_bits),
                "8.0",
            ],
            check=True,
        )
        completed = subprocess.run(
            [str(BUILD_DIR / "compare_with_reference.exe"), str(ref_path), str(out_path), "2e-5"],
            check=True,
            text=True,
            capture_output=True,
        )
        row = {"curve": curve, "mode": "luma", "input_bits": str(input_bits), "output_bits": str(output_bits)}
        row.update(read_compare_output(completed.stdout))
        rows.append(row)
    return rows


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    ALIGN_DIR.mkdir(parents=True, exist_ok=True)
    scene = make_hdr_like_scene()
    exposure = percentile_exposure(scene, 99.0, 1.0)

    ablation_rows = plot_error_curves()
    with (FIGURE_DIR / "week6_lut_size_ablation.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ablation_rows[0].keys()))
        writer.writeheader()
        writer.writerows(ablation_rows)

    plot_banding(scene, exposure)

    alignment_rows = run_cpp_alignment(scene, exposure)
    with (FIGURE_DIR / "week6_python_cpp_alignment.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["curve", "mode", "input_bits", "output_bits", "max_abs_error", "mean_abs_error", "rmse", "psnr", "failed_values"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(alignment_rows)

    print(f"wrote Week6 figures and metrics to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
