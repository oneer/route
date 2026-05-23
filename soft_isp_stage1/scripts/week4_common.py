from __future__ import annotations

import os
import sys
from pathlib import Path

import imageio.v3 as iio
import matplotlib
import numpy as np
import rawpy

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.awb import apply_awb, gray_world_gains
from soft_isp.blc import apply_blc
from soft_isp.ccm import apply_ccm, ccm_from_rawpy_color_matrix
from soft_isp.demosaic import bilinear_demosaic
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array
from soft_isp.tone import apply_gamma, normalize_by_percentile, reinhard_tone_map, to_uint8


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def describe_rgb(rgb: np.ndarray) -> dict:
    return {
        "shape": list(rgb.shape),
        "R": describe_array(rgb[:, :, 0]),
        "G": describe_array(rgb[:, :, 1]),
        "B": describe_array(rgb[:, :, 2]),
    }


def rgb_mean(rgb: np.ndarray) -> list[float]:
    return [float(v) for v in np.mean(rgb.reshape(-1, 3), axis=0)]


def fmt(value: float) -> str:
    return f"{value:.3f}"


def rel(path: str, report_path: Path) -> str:
    return Path(os.path.relpath(path, report_path.parent)).as_posix()


def save_compare(path: Path, title: str, panels: list[tuple[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(1, len(panels), figsize=(5.0 * len(panels), 4.2), constrained_layout=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (panel_title, image) in zip(axes, panels):
        ax.imshow(image)
        ax.set_title(panel_title)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def reference_panel(raw_path: Path, reference_dir: Path, fallback: np.ndarray) -> np.ndarray:
    reference_path = reference_dir / f"{raw_path.stem}_rawpy_srgb.png"
    if reference_path.exists():
        return iio.imread(reference_path)
    return np.zeros_like(fallback)


def build_week4_base(raw_path: Path, min_delta: int, mad_k: float) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        raw_pattern = raw.raw_pattern.copy()
        black_levels = list(raw.black_level_per_channel)
        white_level = int(raw.white_level)
        display_flip = int(raw.sizes.flip)
        ccm = ccm_from_rawpy_color_matrix(raw.color_matrix)

    raw_blc = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    detection = detect_defects(raw_blc, bayer_pattern, min_delta=min_delta, mad_k=mad_k)
    raw_dpc = repair_defects(raw_blc, bayer_pattern, detection)
    rgb_linear = bilinear_demosaic(raw_dpc, bayer_pattern)
    gains = gray_world_gains(rgb_linear)
    rgb_awb = apply_awb(rgb_linear, gains, white_level=white_level)
    rgb_ccm = apply_ccm(rgb_awb, ccm, white_level=white_level)

    return {
        "raw_path": raw_path,
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "display_flip": display_flip,
        "awb_gains": [float(v) for v in gains],
        "ccm": ccm,
        "rgb_awb": rgb_awb,
        "rgb_ccm": rgb_ccm,
    }


def gamma_preview(rgb: np.ndarray, percentile: float, gamma: float, display_flip: int) -> np.ndarray:
    preview = to_uint8(apply_gamma(normalize_by_percentile(rgb, percentile), gamma))
    return apply_rawpy_orientation(preview, display_flip)


def linear_preview(rgb: np.ndarray, percentile: float, display_flip: int) -> np.ndarray:
    preview = to_uint8(normalize_by_percentile(rgb, percentile))
    return apply_rawpy_orientation(preview, display_flip)


def reinhard_preview(rgb: np.ndarray, percentile: float, gamma: float, display_flip: int) -> np.ndarray:
    preview = to_uint8(apply_gamma(reinhard_tone_map(rgb, percentile), gamma))
    return apply_rawpy_orientation(preview, display_flip)
