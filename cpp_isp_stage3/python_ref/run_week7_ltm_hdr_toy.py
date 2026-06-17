from __future__ import annotations

import csv
import math
import subprocess
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from make_test_vectors import write_cpf32
from tone_mapping_ref import apply_gamma, apply_curve, luminance, percentile_exposure, tone_map_luminance
from run_week5_tone_mapping import make_hdr_like_scene


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week7"
ALIGN_DIR = ROOT / "data" / "week7_alignment"
BUILD_DIR = ROOT / "build"


def save_png(path: Path, image: np.ndarray) -> None:
    image = np.clip(image, 0.0, 1.0)
    Image.fromarray((image * 255.0 + 0.5).astype(np.uint8)).save(path)


def read_cpf32(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        if f.readline().strip() != b"CPF32":
            raise ValueError(path)
        width, height, channels = map(int, f.readline().decode("ascii").split())
        data = np.frombuffer(f.read(), dtype="<f4").copy()
    return data.reshape(height, width, channels)


def reflect_index(index: int, size: int) -> int:
    if 0 <= index < size:
        return index
    if size == 1:
        return 0
    while index < 0 or index >= size:
        if index < 0:
            index = -index
        if index >= size:
            index = 2 * size - 2 - index
    return index


def sample_luma(y_image: np.ndarray, y: int, x: int) -> float:
    yy = reflect_index(y, y_image.shape[0])
    xx = reflect_index(x, y_image.shape[1])
    return float(y_image[yy, xx])


def estimate_base_luma(
    image: np.ndarray,
    radius: int,
    base_filter: str = "box",
    sigma_spatial: float = 3.0,
    sigma_range: float = 0.25,
) -> np.ndarray:
    y_image = luminance(image) if image.ndim == 3 and image.shape[2] >= 3 else image[..., 0]
    h, w = y_image.shape
    out = np.zeros((h, w), dtype=np.float32)
    for yy in range(h):
        for xx in range(w):
            center = float(y_image[yy, xx])
            weighted_sum = 0.0
            weight_sum = 0.0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    value = sample_luma(y_image, yy + dy, xx + dx)
                    weight = 1.0
                    if base_filter == "bilateral":
                        d2 = float(dx * dx + dy * dy)
                        spatial = math.exp(-0.5 * d2 / (sigma_spatial * sigma_spatial))
                        diff = value - center
                        rangew = math.exp(-0.5 * diff * diff / (sigma_range * sigma_range))
                        weight = spatial * rangew
                    weighted_sum += weight * value
                    weight_sum += weight
            out[yy, xx] = weighted_sum / max(weight_sum, 1e-6)
    return out


def local_tone_map(
    image: np.ndarray,
    curve: str,
    exposure: float,
    radius: int,
    base_filter: str,
    sigma_spatial: float,
    sigma_range: float,
    detail_strength: float,
) -> tuple[np.ndarray, np.ndarray]:
    y = luminance(image)
    base = estimate_base_luma(image, radius, base_filter, sigma_spatial, sigma_range)
    detail = y / np.maximum(base, 1e-6)
    mapped_base = apply_curve(base * exposure, curve)
    mapped_y = np.clip(mapped_base * np.power(np.maximum(detail, 1e-6), detail_strength), 0.0, 1.0)
    scale = mapped_y / np.maximum(y, 1e-6)
    return np.clip(image * scale[..., None], 0.0, 1.0).astype(np.float32), base.astype(np.float32)


def saturation_weight(value: np.ndarray, threshold: float) -> np.ndarray:
    return np.where(value <= threshold, 1.0, np.clip((1.0 - value) / max(1.0 - threshold, 1e-6), 0.0, 1.0)).astype(np.float32)


def underexposure_weight(value: np.ndarray, threshold: float) -> np.ndarray:
    return np.where(value >= threshold, 1.0, np.clip(value / max(threshold, 1e-6), 0.0, 1.0)).astype(np.float32)


def make_aligned_exposures(radiance: np.ndarray, short_exposure: float, long_exposure: float) -> tuple[np.ndarray, np.ndarray]:
    short_image = np.clip(radiance * short_exposure, 0.0, 1.0).astype(np.float32)
    long_image = np.clip(radiance * long_exposure, 0.0, 1.0).astype(np.float32)
    return short_image, long_image


def hdr_merge_aligned(
    short_image: np.ndarray,
    long_image: np.ndarray,
    short_exposure: float,
    long_exposure: float,
    saturation_threshold: float = 0.92,
    underexposure_threshold: float = 0.04,
    weight_epsilon: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    short_quality = underexposure_weight(np.max(short_image, axis=2), underexposure_threshold)
    long_quality = saturation_weight(np.max(long_image, axis=2), saturation_threshold)
    short_radiance = short_image / short_exposure
    long_radiance = long_image / long_exposure
    merged = (
        short_quality[..., None] * short_radiance + long_quality[..., None] * long_radiance
    ) / (short_quality[..., None] + long_quality[..., None] + weight_epsilon)
    return merged.astype(np.float32), short_quality, long_quality


def metrics(reference: np.ndarray, output: np.ndarray, threshold: float = 2e-5) -> dict[str, float | str]:
    diff = np.abs(reference.astype(np.float64) - output.astype(np.float64))
    mse = float(np.mean(diff * diff))
    psnr = math.inf if mse == 0.0 else 20.0 * math.log10(1.0 / math.sqrt(mse))
    return {
        "max_abs_error": float(np.max(diff)),
        "mean_abs_error": float(np.mean(diff)),
        "rmse": math.sqrt(mse),
        "psnr": psnr,
        "failed_values": f"{int(np.sum(diff > threshold))} / {diff.size}",
    }


def read_compare_output(text: str) -> dict[str, str]:
    row: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            row[key.strip()] = value.strip()
    return row


def plot_ltm(scene: np.ndarray, exposure: float) -> list[dict[str, float | str]]:
    global_tm = tone_map_luminance(scene, "reinhard", exposure)
    ltm_box, base_box = local_tone_map(scene, "reinhard", exposure, 5, "box", 3.0, 0.25, 0.75)
    ltm_bilateral, base_bilateral = local_tone_map(scene, "reinhard", exposure, 3, "bilateral", 2.4, 0.35, 0.75)

    outputs = [
        ("global", global_tm),
        ("ltm_box", ltm_box),
        ("ltm_bilateral", ltm_bilateral),
    ]
    fig, axes = plt.subplots(3, 3, figsize=(11, 9))
    for col, (title, image) in enumerate(outputs):
        axes[0, col].imshow(apply_gamma(image, 2.2))
        axes[0, col].set_title(title, fontsize=9)
        axes[0, col].axis("off")
        error = np.abs(luminance(image) - luminance(global_tm))
        axes[1, col].imshow(np.clip(error * 4.0, 0.0, 1.0), cmap="magma")
        axes[1, col].set_title("delta vs global x4", fontsize=9)
        axes[1, col].axis("off")
        base = base_box if title == "ltm_box" else base_bilateral if title == "ltm_bilateral" else luminance(scene)
        axes[2, col].imshow(np.clip(base * exposure, 0.0, 1.0), cmap="gray")
        axes[2, col].set_title("base/luma preview", fontsize=9)
        axes[2, col].axis("off")
        save_png(FIGURE_DIR / f"week7_{title}.png", apply_gamma(image, 2.2))
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week7_ltm_global_comparison.png", dpi=170)
    plt.close(fig)

    h, w = scene.shape[:2]
    edge_band = np.s_[int(h * 0.08) : int(h * 0.38), int(w * 0.58) : int(w * 0.94)]
    rows = []
    for name, image in outputs:
        y = luminance(image)
        rows.append(
            {
                "method": name,
                "mean_luma": float(np.mean(y)),
                "p95_luma": float(np.percentile(y, 95)),
                "clip_fraction": float(np.mean(image >= 0.999)),
                "edge_band_std": float(np.std(y[edge_band])),
            }
        )
    return rows


def plot_hdr(scene: np.ndarray, exposure: float) -> None:
    short_exposure = 0.18
    long_exposure = 0.72
    short_image, long_image = make_aligned_exposures(scene, short_exposure, long_exposure)
    merged, short_weight, long_weight = hdr_merge_aligned(short_image, long_image, short_exposure, long_exposure)
    hdr_global = tone_map_luminance(merged, "reinhard", exposure)
    hdr_ltm, _ = local_tone_map(merged, "reinhard", exposure, 3, "bilateral", 2.4, 0.35, 0.75)

    fig, axes = plt.subplots(2, 4, figsize=(14, 7))
    images = [
        ("short exposure", short_image),
        ("long exposure", long_image),
        ("merged HDR TM", hdr_global),
        ("merged HDR LTM", hdr_ltm),
    ]
    for col, (title, image) in enumerate(images):
        axes[0, col].imshow(apply_gamma(np.clip(image, 0.0, 1.0), 2.2))
        axes[0, col].set_title(title, fontsize=9)
        axes[0, col].axis("off")
    axes[1, 0].imshow(short_weight, cmap="viridis", vmin=0, vmax=1)
    axes[1, 0].set_title("short weight", fontsize=9)
    axes[1, 1].imshow(long_weight, cmap="viridis", vmin=0, vmax=1)
    axes[1, 1].set_title("long weight", fontsize=9)
    axes[1, 2].imshow(np.clip(luminance(merged) * exposure, 0.0, 1.0), cmap="gray")
    axes[1, 2].set_title("merged radiance preview", fontsize=9)
    axes[1, 3].imshow(np.clip(np.abs(luminance(hdr_ltm) - luminance(hdr_global)) * 4.0, 0.0, 1.0), cmap="magma")
    axes[1, 3].set_title("LTM delta x4", fontsize=9)
    for ax in axes[1, :]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "week7_hdr_merge_pipeline.png", dpi=170)
    plt.close(fig)

    save_png(FIGURE_DIR / "week7_short_exposure.png", apply_gamma(short_image, 2.2))
    save_png(FIGURE_DIR / "week7_long_exposure.png", apply_gamma(long_image, 2.2))
    save_png(FIGURE_DIR / "week7_hdr_global_tm.png", apply_gamma(hdr_global, 2.2))
    save_png(FIGURE_DIR / "week7_hdr_local_tm.png", apply_gamma(hdr_ltm, 2.2))


def run_alignment(scene: np.ndarray, exposure: float) -> list[dict[str, str]]:
    write_cpf32(ALIGN_DIR / "week7_scene.cpf32", scene)
    rows: list[dict[str, str]] = []

    ltm_ref, _ = local_tone_map(scene, "reinhard", exposure, 3, "bilateral", 2.4, 0.35, 0.75)
    ltm_ref_path = ALIGN_DIR / "week7_python_ltm_bilateral.cpf32"
    ltm_cpp_path = ALIGN_DIR / "week7_cpp_ltm_bilateral.cpf32"
    write_cpf32(ltm_ref_path, ltm_ref)
    subprocess.run(
        [
            str(BUILD_DIR / "run_local_tone_mapping.exe"),
            str(ALIGN_DIR / "week7_scene.cpf32"),
            str(ltm_cpp_path),
            "reinhard",
            f"{exposure:.9f}",
            "bilateral",
            "3",
            "2.4",
            "0.35",
            "0.75",
        ],
        check=True,
    )
    completed = subprocess.run(
        [str(BUILD_DIR / "compare_with_reference.exe"), str(ltm_ref_path), str(ltm_cpp_path), "3e-5"],
        check=True,
        text=True,
        capture_output=True,
    )
    row = {"module": "local_tone_mapping", "case": "reinhard_bilateral"}
    row.update(read_compare_output(completed.stdout))
    rows.append(row)

    short_image, long_image = make_aligned_exposures(scene, 0.18, 0.72)
    hdr_ref, _, _ = hdr_merge_aligned(short_image, long_image, 0.18, 0.72)
    write_cpf32(ALIGN_DIR / "week7_short.cpf32", short_image)
    write_cpf32(ALIGN_DIR / "week7_long.cpf32", long_image)
    hdr_ref_path = ALIGN_DIR / "week7_python_hdr_merge.cpf32"
    hdr_cpp_path = ALIGN_DIR / "week7_cpp_hdr_merge.cpf32"
    write_cpf32(hdr_ref_path, hdr_ref)
    subprocess.run(
        [
            str(BUILD_DIR / "run_hdr_merge.exe"),
            str(ALIGN_DIR / "week7_short.cpf32"),
            str(ALIGN_DIR / "week7_long.cpf32"),
            str(hdr_cpp_path),
            "0.18",
            "0.72",
            "0.92",
            "0.04",
            "0.000001",
        ],
        check=True,
    )
    completed = subprocess.run(
        [str(BUILD_DIR / "compare_with_reference.exe"), str(hdr_ref_path), str(hdr_cpp_path), "3e-5"],
        check=True,
        text=True,
        capture_output=True,
    )
    row = {"module": "hdr_merge", "case": "aligned_short_long"}
    row.update(read_compare_output(completed.stdout))
    rows.append(row)
    return rows


def run_python_benchmark(scene: np.ndarray, exposure: float) -> list[dict[str, float | str]]:
    rows = []
    for name, fn in [
        ("ltm_box_r5", lambda: local_tone_map(scene, "reinhard", exposure, 5, "box", 3.0, 0.25, 0.75)[0]),
        ("ltm_bilateral_r3", lambda: local_tone_map(scene, "reinhard", exposure, 3, "bilateral", 2.4, 0.35, 0.75)[0]),
    ]:
        best = 1e9
        for _ in range(2):
            t0 = time.perf_counter()
            fn()
            best = min(best, (time.perf_counter() - t0) * 1000.0)
        rows.append({"python_method": name, "width": scene.shape[1], "height": scene.shape[0], "ms": best})
    return rows


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    ALIGN_DIR.mkdir(parents=True, exist_ok=True)
    scene = make_hdr_like_scene(width=192, height=128)
    exposure = percentile_exposure(scene, 99.0, 1.0)

    ltm_rows = plot_ltm(scene, exposure)
    with (FIGURE_DIR / "week7_ltm_roi_metrics.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ltm_rows[0].keys()))
        writer.writeheader()
        writer.writerows(ltm_rows)

    plot_hdr(scene, exposure)

    alignment_rows = run_alignment(scene, exposure)
    with (FIGURE_DIR / "week7_python_cpp_alignment.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["module", "case", "max_abs_error", "mean_abs_error", "rmse", "psnr", "failed_values"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(alignment_rows)

    python_rows = run_python_benchmark(scene, exposure)
    with (FIGURE_DIR / "week7_python_benchmark.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(python_rows[0].keys()))
        writer.writeheader()
        writer.writerows(python_rows)

    print(f"wrote Week7 figures and metrics to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
