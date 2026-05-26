from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import cv2
import imageio.v3 as iio
import matplotlib
import numpy as np
import rawpy
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.awb import apply_awb, gray_world_gains
from soft_isp.blc import apply_blc
from soft_isp.ccm import apply_ccm, ccm_from_rawpy_color_matrix
from soft_isp.demosaic import bilinear_demosaic
from soft_isp.dpc import detect_defects, merge_channel_masks, repair_defects
from soft_isp.lsc import apply_lsc, make_lsc_gain_map
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy
from soft_isp.tone import apply_gamma, normalize_by_percentile, reinhard_tone_map, to_uint8


SAMPLE_IDS_FOR_DETAIL = {"T01", "T08", "T09", "T13"}


def expand_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        text = str(path)
        if any(char in text for char in "*?[]"):
            expanded.extend(Path(match) for match in glob.glob(text))
        else:
            expanded.append(path)
    return sorted(expanded)


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def rel(path: str | Path, report_path: Path) -> str:
    return Path(os.path.relpath(path, report_path.parent)).as_posix()


def center_crop_image(image: np.ndarray, max_size: int) -> np.ndarray:
    if max_size <= 0:
        return image
    h, w = image.shape[:2]
    crop_h = min(h, max_size)
    crop_w = min(w, max_size)
    y0 = max((h - crop_h) // 2, 0)
    x0 = max((w - crop_w) // 2, 0)
    return image[y0 : y0 + crop_h, x0 : x0 + crop_w]


def center_crop_bayer(raw: np.ndarray, max_size: int) -> np.ndarray:
    if max_size <= 0:
        return raw
    h, w = raw.shape[:2]
    crop_h = min(h, max_size)
    crop_w = min(w, max_size)
    crop_h -= crop_h % 2
    crop_w -= crop_w % 2
    y0 = max((h - crop_h) // 2, 0)
    x0 = max((w - crop_w) // 2, 0)
    y0 -= y0 % 2
    x0 -= x0 % 2
    return raw[y0 : y0 + crop_h, x0 : x0 + crop_w]


def load_reference(raw_path: Path, reference_dir: Path, max_size: int) -> np.ndarray | None:
    path = reference_dir / f"{raw_path.stem}_rawpy_srgb.png"
    return center_crop_image(iio.imread(path), max_size) if path.exists() else None


def align_pair(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    min_h = min(a.shape[0], b.shape[0])
    min_w = min(a.shape[1], b.shape[1])
    return a[:min_h, :min_w], b[:min_h, :min_w]


def compute_metrics(candidate: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    cand, ref = align_pair(candidate, reference)
    cand_f = cand.astype(np.float32) / 255.0
    ref_f = ref.astype(np.float32) / 255.0
    return {
        "psnr": float(peak_signal_noise_ratio(ref_f, cand_f, data_range=1.0)),
        "ssim": float(structural_similarity(ref_f, cand_f, channel_axis=2, data_range=1.0)),
        "mean_abs_diff": float(np.mean(np.abs(ref_f - cand_f))),
    }


def mean_delta_e(candidate: np.ndarray, reference: np.ndarray, stride: int = 8) -> float:
    cand, ref = align_pair(candidate, reference)
    cand_f = cand[::stride, ::stride].astype(np.float32) / 255.0
    ref_f = ref[::stride, ::stride].astype(np.float32) / 255.0
    return float(np.mean(deltaE_ciede2000(rgb2lab(ref_f), rgb2lab(cand_f))))


def read_raw_context(raw_path: Path, max_size: int) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = center_crop_bayer(raw.raw_image_visible.copy(), max_size)
        color_desc = raw.color_desc.decode(errors="replace")
        return {
            "raw_visible": raw_visible,
            "raw_pattern": raw.raw_pattern.copy(),
            "bayer_pattern": bayer_pattern_from_rawpy(raw.raw_pattern, color_desc),
            "black_levels": list(raw.black_level_per_channel),
            "white_level": int(raw.white_level),
            "display_flip": int(raw.sizes.flip),
            "ccm": ccm_from_rawpy_color_matrix(raw.color_matrix),
        }


def prepare_linear_pipeline(raw_path: Path, min_delta: int, mad_k: float, max_size: int) -> dict:
    ctx = read_raw_context(raw_path, max_size=max_size)
    raw_blc = apply_blc(ctx["raw_visible"], ctx["raw_pattern"], ctx["black_levels"], ctx["white_level"])
    detection = detect_defects(raw_blc, ctx["bayer_pattern"], min_delta=min_delta, mad_k=mad_k)
    raw_dpc = repair_defects(raw_blc, ctx["bayer_pattern"], detection)
    raw_lsc, gain_map = apply_lsc(raw_dpc, ctx["bayer_pattern"], white_level=ctx["white_level"])
    rgb = bilinear_demosaic(raw_lsc, ctx["bayer_pattern"])
    gains_gray = gray_world_gains(rgb)
    rgb_awb = apply_awb(rgb, gains_gray, white_level=ctx["white_level"])
    rgb_ccm = apply_ccm(rgb_awb, ctx["ccm"], white_level=ctx["white_level"])
    return {
        **ctx,
        "raw_blc": raw_blc,
        "detection": detection,
        "raw_dpc": raw_dpc,
        "raw_lsc": raw_lsc,
        "gain_map": gain_map,
        "rgb": rgb,
        "gains_gray": gains_gray,
        "rgb_awb": rgb_awb,
        "rgb_ccm": rgb_ccm,
    }


def preview_from_linear(rgb: np.ndarray, gamma: float, tone_percentile: float, tone: str = "reinhard") -> np.ndarray:
    if tone == "reinhard":
        rgb_01 = reinhard_tone_map(rgb, percentile=tone_percentile)
        return to_uint8(apply_gamma(rgb_01, gamma=gamma))
    if tone == "gamma_only":
        rgb_01 = normalize_by_percentile(rgb, percentile=tone_percentile)
        return to_uint8(apply_gamma(rgb_01, gamma=gamma))
    if tone == "srgb":
        rgb_01 = normalize_by_percentile(rgb, percentile=tone_percentile)
        return to_uint8(srgb_oetf(rgb_01))
    if tone == "s_curve":
        rgb_01 = normalize_by_percentile(rgb, percentile=tone_percentile)
        return to_uint8(srgb_oetf(s_curve(rgb_01)))
    raise ValueError(f"Unknown tone mode: {tone}")


def srgb_oetf(rgb_01: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(rgb_01, dtype=np.float32), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055).astype(np.float32)


def s_curve(rgb_01: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(rgb_01, dtype=np.float32), 0.0, 1.0)
    return (x * x * (3.0 - 2.0 * x)).astype(np.float32)


def cv2_code(pattern: str, method: str) -> int | None:
    suffix = "" if method == "bilinear" else "_EA"
    name = f"COLOR_Bayer{pattern.upper()}2RGB{suffix}"
    return getattr(cv2, name, None)


def cv2_demosaic(raw_bayer: np.ndarray, pattern: str, method: str) -> np.ndarray | None:
    code = cv2_code(pattern, method)
    if code is None:
        return None
    raw = np.clip(raw_bayer, 0, np.iinfo(np.uint16).max).astype(np.uint16)
    try:
        return cv2.cvtColor(raw, code).astype(np.float32)
    except cv2.error:
        return None


def white_patch_gains(rgb: np.ndarray, high_percentile: float = 99.0, max_gain: float = 8.0) -> np.ndarray:
    rgb_f = np.asarray(rgb, dtype=np.float32)
    lum = np.mean(rgb_f, axis=2)
    threshold = np.percentile(lum, high_percentile)
    mask = lum >= threshold
    if not np.any(mask):
        mask = np.ones(lum.shape, dtype=bool)
    means = np.maximum(np.mean(rgb_f[mask], axis=0), 1e-6)
    green = means[1]
    return np.clip(np.array([green / means[0], 1.0, green / means[2]], dtype=np.float32), 1.0 / max_gain, max_gain)


def gray_roi_gains(rgb: np.ndarray, max_gain: float = 8.0) -> tuple[np.ndarray, float]:
    rgb_f = np.asarray(rgb, dtype=np.float32)
    lum = np.mean(rgb_f, axis=2)
    low, high = np.percentile(lum, [20, 90])
    chroma = np.max(np.abs(rgb_f - lum[..., None]), axis=2) / np.maximum(lum, 1e-6)
    mask = (lum >= low) & (lum <= high) & (chroma < 0.16)
    coverage = float(np.mean(mask))
    if np.count_nonzero(mask) < 64:
        mask = (lum >= low) & (lum <= high)
        coverage = float(np.mean(mask))
    means = np.maximum(np.mean(rgb_f[mask], axis=0), 1e-6)
    green = means[1]
    gains = np.clip(np.array([green / means[0], 1.0, green / means[2]], dtype=np.float32), 1.0 / max_gain, max_gain)
    return gains, coverage


def make_static_detection(dynamic_detection: dict, max_points_per_channel: int = 25) -> dict:
    masks = {}
    medians = dynamic_detection["local_medians"]
    for name, mask in dynamic_detection["masks"].items():
        static_mask = np.zeros_like(mask, dtype=bool)
        ys, xs = np.nonzero(mask)
        limit = min(len(ys), max_points_per_channel)
        if limit:
            static_mask[ys[:limit], xs[:limit]] = True
        masks[name] = static_mask
    return {"masks": masks, "local_medians": medians, "thresholds": dynamic_detection["thresholds"]}


def estimate_mesh_gain_from_synthetic_flat(shape: tuple[int, int], pattern: str, tile: int = 32) -> dict:
    true_gain = make_lsc_gain_map(shape, pattern)
    flat = 2048.0 / np.maximum(true_gain, 1e-6)
    h, w = shape
    est_gain = np.ones((h, w), dtype=np.float32)
    tile_rows = []
    for y0 in range(0, h, tile):
        row = []
        for x0 in range(0, w, tile):
            patch = flat[y0 : min(y0 + tile, h), x0 : min(x0 + tile, w)]
            gain = float(np.mean(flat) / max(float(np.mean(patch)), 1e-6))
            est_gain[y0 : min(y0 + tile, h), x0 : min(x0 + tile, w)] = gain
            row.append(gain)
        tile_rows.append(row)
    mae = float(np.mean(np.abs(est_gain - true_gain)))
    return {"true_gain": true_gain, "estimated_gain": est_gain, "mesh": tile_rows, "mae": mae}


def roi_boxes(image: np.ndarray) -> dict[str, tuple[int, int, int, int]]:
    h, w = image.shape[:2]
    size = max(96, min(h, w) // 8)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.abs(grad_x) + np.abs(grad_y)

    def best_tile(score: np.ndarray, mode: str) -> tuple[int, int, int, int]:
        best = None
        best_score = None
        step = max(size // 2, 32)
        for y in range(0, max(h - size, 1), step):
            for x in range(0, max(w - size, 1), step):
                value = float(np.mean(score[y : y + size, x : x + size]))
                if best is None or (mode == "max" and value > best_score) or (mode == "min" and value < best_score):
                    best = (x, y, size, size)
                    best_score = value
        return best or (0, 0, min(size, w), min(size, h))

    return {
        "center": (max((w - size) // 2, 0), max((h - size) // 2, 0), size, size),
        "dark": best_tile(gray, "min"),
        "highlight": best_tile(gray, "max"),
        "texture": best_tile(grad, "max"),
        "corner": (0, 0, size, size),
    }


def crop(image: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = box
    return image[y : y + h, x : x + w]


def subjective_tags(metric: dict[str, float], delta_e: float) -> str:
    tags = []
    if metric["ssim"] < 0.75:
        tags.append("structure_gap")
    if metric["mean_abs_diff"] > 0.10:
        tags.append("luminance_gap")
    if delta_e > 12.0:
        tags.append("color_shift")
    return ", ".join(tags) if tags else "acceptable"


def save_image_grid(path: Path, title: str, panels: list[tuple[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(1, len(panels), figsize=(4.0 * len(panels), 3.8), constrained_layout=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (panel_title, image) in zip(axes, panels):
        if image.ndim == 2:
            ax.imshow(image, cmap="magma")
        else:
            ax.imshow(image)
        ax.set_title(panel_title)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def save_curve_plot(path: Path) -> None:
    x = np.linspace(0.0, 1.0, 512, dtype=np.float32)
    plt.figure(figsize=(6, 4))
    plt.plot(x, apply_gamma(x, gamma=2.2), label="pow gamma 1/2.2")
    plt.plot(x, srgb_oetf(x), label="sRGB OETF")
    plt.plot(x, srgb_oetf(s_curve(x)), label="S-curve LUT + sRGB")
    plt.xlabel("linear input")
    plt.ylabel("encoded output")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def evaluate_one(
    raw_path: Path,
    out_dir: Path,
    reference_dir: Path,
    min_delta: int,
    mad_k: float,
    gamma: float,
    tone_percentile: float,
    max_size: int,
) -> dict:
    sid = sample_id(raw_path)
    data = prepare_linear_pipeline(raw_path, min_delta=min_delta, mad_k=mad_k, max_size=max_size)
    reference = load_reference(raw_path, reference_dir, max_size=max_size)

    full_preview = apply_rawpy_orientation(preview_from_linear(data["rgb_ccm"], gamma, tone_percentile), data["display_flip"])
    no_ccm_preview = apply_rawpy_orientation(preview_from_linear(data["rgb_awb"], gamma, tone_percentile), data["display_flip"])
    gamma_only = apply_rawpy_orientation(preview_from_linear(data["rgb_ccm"], gamma, tone_percentile, tone="gamma_only"), data["display_flip"])
    srgb_preview = apply_rawpy_orientation(preview_from_linear(data["rgb_ccm"], gamma, tone_percentile, tone="srgb"), data["display_flip"])
    s_curve_preview = apply_rawpy_orientation(preview_from_linear(data["rgb_ccm"], gamma, tone_percentile, tone="s_curve"), data["display_flip"])

    dynamic_mask = merge_channel_masks(data["raw_blc"].shape, data["bayer_pattern"], data["detection"]["masks"])
    static_detection = make_static_detection(data["detection"])
    static_mask = merge_channel_masks(data["raw_blc"].shape, data["bayer_pattern"], static_detection["masks"])
    raw_static = repair_defects(data["raw_blc"], data["bayer_pattern"], static_detection)

    mesh = estimate_mesh_gain_from_synthetic_flat(data["raw_blc"].shape, data["bayer_pattern"], tile=64)

    cv_bilinear = cv2_demosaic(data["raw_lsc"], data["bayer_pattern"], "bilinear")
    cv_ea = cv2_demosaic(data["raw_lsc"], data["bayer_pattern"], "ea")
    demosaic_metrics = {}
    for name, rgb in [("ours_bilinear", data["rgb"]), ("opencv_bilinear", cv_bilinear), ("opencv_edge_aware", cv_ea)]:
        if rgb is None or reference is None:
            continue
        preview = apply_rawpy_orientation(preview_from_linear(rgb, gamma, tone_percentile, tone="gamma_only"), data["display_flip"])
        demosaic_metrics[name] = compute_metrics(preview, reference)

    gains_white = white_patch_gains(data["rgb"])
    gains_roi, roi_gray_coverage = gray_roi_gains(data["rgb"])
    awb_previews = {
        "gray_world": apply_rawpy_orientation(preview_from_linear(apply_awb(data["rgb"], data["gains_gray"], data["white_level"]), gamma, tone_percentile, "gamma_only"), data["display_flip"]),
        "white_patch": apply_rawpy_orientation(preview_from_linear(apply_awb(data["rgb"], gains_white, data["white_level"]), gamma, tone_percentile, "gamma_only"), data["display_flip"]),
        "gray_roi": apply_rawpy_orientation(preview_from_linear(apply_awb(data["rgb"], gains_roi, data["white_level"]), gamma, tone_percentile, "gamma_only"), data["display_flip"]),
    }
    awb_metrics = {name: compute_metrics(img, reference) for name, img in awb_previews.items()} if reference is not None else {}

    ccm_metrics = {}
    if reference is not None:
        ccm_metrics = {
            "no_ccm_delta_e": mean_delta_e(no_ccm_preview, reference),
            "ccm_delta_e": mean_delta_e(full_preview, reference),
            "no_ccm": compute_metrics(no_ccm_preview, reference),
            "ccm": compute_metrics(full_preview, reference),
        }

    tone_metrics = {}
    if reference is not None:
        for name, img in [("reinhard_pow_gamma", full_preview), ("gamma_only", gamma_only), ("srgb_oetf", srgb_preview), ("s_curve_lut", s_curve_preview)]:
            tone_metrics[name] = compute_metrics(img, reference)

    roi_metrics = {}
    if reference is not None:
        boxes = roi_boxes(reference)
        full_aligned, ref_aligned = align_pair(full_preview, reference)
        for name, box in boxes.items():
            cand_crop = crop(full_aligned, box)
            ref_crop = crop(ref_aligned, box)
            metric = compute_metrics(cand_crop, ref_crop)
            de = mean_delta_e(cand_crop, ref_crop, stride=1)
            roi_metrics[name] = {**metric, "delta_e": de, "subjective_tag": subjective_tags(metric, de)}
    else:
        boxes = {}

    figures = {}
    if sid in SAMPLE_IDS_FOR_DETAIL:
        dpc_path = out_dir / f"{raw_path.stem}_week6_dpc_static_dynamic.png"
        dpc_preview = np.stack(
            [
                np.clip(data["raw_blc"] / max(data["white_level"], 1) * 255, 0, 255).astype(np.uint8),
                np.clip(raw_static / max(data["white_level"], 1) * 255, 0, 255).astype(np.uint8),
                np.clip(static_mask.astype(np.uint8) * 255 + dynamic_mask.astype(np.uint8) * 90, 0, 255).astype(np.uint8),
            ],
            axis=-1,
        )
        save_image_grid(dpc_path, f"{sid} DPC dynamic vs static", [("static/dynamic mask", apply_rawpy_orientation(dpc_preview, data["display_flip"]))])
        figures["dpc"] = str(dpc_path)

        lsc_path = out_dir / f"{raw_path.stem}_week6_lsc_mesh.png"
        save_image_grid(
            lsc_path,
            f"{sid} synthetic flat-field mesh LSC",
            [
                ("true gain", cv2.resize(mesh["true_gain"], (320, 220))),
                ("estimated mesh", cv2.resize(mesh["estimated_gain"], (320, 220), interpolation=cv2.INTER_NEAREST)),
                ("abs error", cv2.resize(np.abs(mesh["estimated_gain"] - mesh["true_gain"]), (320, 220))),
            ],
        )
        figures["lsc"] = str(lsc_path)

        demo_path = out_dir / f"{raw_path.stem}_week6_demosaic_compare.png"
        demo_panels = [("ours bilinear", preview_from_linear(data["rgb"], gamma, tone_percentile, "gamma_only"))]
        if cv_bilinear is not None:
            demo_panels.append(("OpenCV bilinear", preview_from_linear(cv_bilinear, gamma, tone_percentile, "gamma_only")))
        if cv_ea is not None:
            demo_panels.append(("OpenCV edge-aware", preview_from_linear(cv_ea, gamma, tone_percentile, "gamma_only")))
        if reference is not None:
            demo_panels.append(("rawpy", reference))
        save_image_grid(demo_path, f"{sid} demosaic baselines", demo_panels)
        figures["demosaic"] = str(demo_path)

        awb_path = out_dir / f"{raw_path.stem}_week6_awb_compare.png"
        panels = [(name, img) for name, img in awb_previews.items()]
        if reference is not None:
            panels.append(("rawpy", reference))
        save_image_grid(awb_path, f"{sid} AWB methods", panels)
        figures["awb"] = str(awb_path)

        diff = np.clip(np.abs(full_preview.astype(np.int16) - no_ccm_preview.astype(np.int16)) * 8, 0, 255).astype(np.uint8)
        ccm_path = out_dir / f"{raw_path.stem}_week6_ccm_deltae.png"
        panels = [("no CCM", no_ccm_preview), ("CCM", full_preview), ("diff x8", diff)]
        if reference is not None:
            panels.append(("rawpy", reference))
        save_image_grid(ccm_path, f"{sid} CCM visible difference", panels)
        figures["ccm"] = str(ccm_path)

        tone_path = out_dir / f"{raw_path.stem}_week6_tone_curves.png"
        panels = [("pow gamma", gamma_only), ("sRGB OETF", srgb_preview), ("S-curve LUT", s_curve_preview)]
        if reference is not None:
            panels.append(("rawpy", reference))
        save_image_grid(tone_path, f"{sid} gamma/tone variants", panels)
        figures["tone"] = str(tone_path)

    return {
        "sample_id": sid,
        "file": str(raw_path),
        "analysis_crop": list(data["raw_blc"].shape),
        "dpc": {
            "dynamic_count": int(np.count_nonzero(dynamic_mask)),
            "static_count": int(np.count_nonzero(static_mask)),
        },
        "lsc": {"synthetic_mesh_mae": mesh["mae"]},
        "demosaic": demosaic_metrics,
        "awb": {
            "gray_world_gains": data["gains_gray"].round(4).tolist(),
            "white_patch_gains": gains_white.round(4).tolist(),
            "gray_roi_gains": gains_roi.round(4).tolist(),
            "gray_roi_coverage": roi_gray_coverage,
            "metrics": awb_metrics,
        },
        "ccm": ccm_metrics,
        "tone": tone_metrics,
        "roi_iqa": roi_metrics,
        "figures": figures,
    }


def fmt(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    return f"{value:.4f}"


def mean_metric(results: list[dict], section: str, variant: str, key: str) -> float | None:
    values = []
    for result in results:
        data = result.get(section, {})
        metric = data.get(variant, {}) if section != "awb" else data.get("metrics", {}).get(variant, {})
        if key in metric:
            values.append(metric[key])
    return float(np.mean(values)) if values else None


def write_report(results: list[dict], report_path: Path, curve_path: Path) -> None:
    lines = [
        "# Week 6 补短板实验报告",
        "",
        "本报告把 `module_mastery_matrix.md` 中标记为“缺实验”的能力点集中补齐。它不替代 Week1-5 的主报告，而是作为补充验证层：每个缺口都对应一个可运行实验、一个结果表或一组可视化。",
        "",
        "为了让 DPC、多个 demosaic、DeltaE 和 ROI 指标能在 14 张样张上快速复现，本报告默认使用保持 Bayer 对齐的中心 RAW crop 进行实验。它用于学习和对比模块行为，不替代全分辨率产品评价。",
        "",
        "## 1. 本周补齐了什么",
        "",
        "| 缺口 | 本次补法 | 输出 |",
        "|---|---|---|",
        "| DPC 静态 defect map | 从动态候选中抽取固定坐标，构造静态 defect map 修复 | dynamic/static 数量和 mask 图 |",
        "| LSC flat-field / mesh LUT | 构造合成 flat-field，按 tile 估计 mesh gain | true gain / estimated mesh / error 图 |",
        "| Demosaic OpenCV / 方向对比 | 对比本项目 bilinear、OpenCV bilinear、OpenCV edge-aware | 指标表和对比图 |",
        "| AWB white patch / ROI | 对比 Gray World、White Patch、Gray ROI | gain 表、指标和对比图 |",
        "| CCM Lab / DeltaE | 比较 no-CCM 与 CCM 到 rawpy reference 的 DeltaE | DeltaE 表和差异放大图 |",
        "| Gamma/Tone S-curve | 对比 pow gamma、sRGB OETF、S-curve LUT | 曲线图和指标表 |",
        "| IQA ROI + 主观标签 | 自动选 center/dark/highlight/texture/corner ROI | ROI 指标和标签表 |",
        "",
        "## 2. DPC：动态检测 vs 静态 defect map",
        "",
        "| 样张 | 动态候选数 | 静态 defect map 点数 | 说明 |",
        "|---|---:|---:|---|",
    ]
    for result in results:
        lines.append(f"| {result['sample_id']} | {result['dpc']['dynamic_count']} | {result['dpc']['static_count']} | 静态表只修固定坐标，动态检测依赖当前图像统计 |")

    lines.extend(
        [
            "",
            "动态 DPC 适合发现当前帧中的异常点，但会受 ISO、温度、纹理和高光边缘影响；静态 defect map 来自工厂标定，稳定但只能修已知坐标。产品里常把两者结合：先用静态表修已知坏点，再用动态检测兜底。",
            "",
            "## 3. LSC：合成 flat-field 与 mesh gain",
            "",
            "| 样张 | mesh gain MAE ↓ | 说明 |",
            "|---|---:|---|",
        ]
    )
    for result in results:
        lines.append(f"| {result['sample_id']} | {fmt(result['lsc']['synthetic_mesh_mae'])} | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |")

    lines.extend(
        [
            "",
            "这里用合成 flat-field 验证 LSC 标定流程：先构造一张带暗角的均匀场，再按 tile 估计 gain。它不等于真实镜头标定，但补上了“flat-field / mesh LUT 是怎么来的”这块理解。",
            "",
            "## 4. Demosaic：Bilinear / OpenCV / Edge-aware 对比",
            "",
            "| 变体 | 平均 PSNR ↑ | 平均 SSIM ↑ | 平均 Mean Abs Diff ↓ |",
            "|---|---:|---:|---:|",
        ]
    )
    for variant in ["ours_bilinear", "opencv_bilinear", "opencv_edge_aware"]:
        lines.append(
            f"| {variant} | {fmt(mean_metric(results, 'demosaic', variant, 'psnr'))} | {fmt(mean_metric(results, 'demosaic', variant, 'ssim'))} | {fmt(mean_metric(results, 'demosaic', variant, 'mean_abs_diff'))} |"
        )

    lines.extend(
        [
            "",
            "OpenCV edge-aware 可以作为 AHD/方向自适应类方法的入门对照。它不等于完整产品 demosaic，但能说明：方向信息和边缘保护通常比单纯同色平均更适合高频纹理与斜边。",
            "",
            "## 5. AWB：Gray World / White Patch / Gray ROI",
            "",
            "| 变体 | 平均 PSNR ↑ | 平均 SSIM ↑ | 平均 Mean Abs Diff ↓ |",
            "|---|---:|---:|---:|",
        ]
    )
    for variant in ["gray_world", "white_patch", "gray_roi"]:
        lines.append(
            f"| {variant} | {fmt(mean_metric(results, 'awb', variant, 'psnr'))} | {fmt(mean_metric(results, 'awb', variant, 'ssim'))} | {fmt(mean_metric(results, 'awb', variant, 'mean_abs_diff'))} |"
        )

    lines.extend(["", "| 样张 | Gray World gain | White Patch gain | Gray ROI gain | ROI 覆盖率 |", "|---|---|---|---|---:|"])
    for result in results:
        awb = result["awb"]
        lines.append(
            f"| {result['sample_id']} | {awb['gray_world_gains']} | {awb['white_patch_gains']} | {awb['gray_roi_gains']} | {fmt(awb['gray_roi_coverage'])} |"
        )

    lines.extend(
        [
            "",
            "White Patch 更相信最亮区域，容易被彩色高光或饱和区域带偏；Gray ROI 会先找较中性的候选像素，更接近工程 AWB 的灰点筛选思路。",
            "",
            "## 6. CCM：Lab / DeltaE 与差异放大",
            "",
            "| 样张 | no CCM DeltaE ↓ | CCM DeltaE ↓ | DeltaE 改善 | 说明 |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for result in results:
        ccm = result["ccm"]
        if not ccm:
            continue
        improvement = ccm["no_ccm_delta_e"] - ccm["ccm_delta_e"]
        lines.append(f"| {result['sample_id']} | {fmt(ccm['no_ccm_delta_e'])} | {fmt(ccm['ccm_delta_e'])} | {fmt(improvement)} | 正数表示 CCM 更接近 rawpy reference |")

    lines.extend(
        [
            "",
            "DeltaE 仍然是相对 rawpy reference 的近似评价，不是色卡标准答案。但它比单纯看整图更适合回答“CCM 到底有没有改变颜色关系”。",
            "",
            "## 7. Gamma / Tone：pow gamma、sRGB OETF、S-curve LUT",
            "",
            f"![Gamma/Tone curves]({rel(curve_path, report_path)})",
            "",
            "| 变体 | 平均 PSNR ↑ | 平均 SSIM ↑ | 平均 Mean Abs Diff ↓ |",
            "|---|---:|---:|---:|",
        ]
    )
    for variant in ["reinhard_pow_gamma", "gamma_only", "srgb_oetf", "s_curve_lut"]:
        lines.append(
            f"| {variant} | {fmt(mean_metric(results, 'tone', variant, 'psnr'))} | {fmt(mean_metric(results, 'tone', variant, 'ssim'))} | {fmt(mean_metric(results, 'tone', variant, 'mean_abs_diff'))} |"
        )

    lines.extend(
        [
            "",
            "这补上了之前缺的 sRGB OETF 和 S-curve。pow gamma 是最小教学版，sRGB OETF 更接近标准显示编码，S-curve LUT 更接近产品 tuning 的曲线工作流。",
            "",
            "## 8. ROI IQA 与主观标签",
            "",
            "| 样张 | ROI | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ | DeltaE ↓ | 主观标签 |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for result in results:
        for name, metric in result["roi_iqa"].items():
            lines.append(
                f"| {result['sample_id']} | {name} | {fmt(metric['psnr'])} | {fmt(metric['ssim'])} | {fmt(metric['mean_abs_diff'])} | {fmt(metric['delta_e'])} | {metric['subjective_tag']} |"
            )

    lines.extend(["", "## 9. 代表性可视化", ""])
    for result in results:
        if not result["figures"]:
            continue
        lines.append(f"### {result['sample_id']}")
        lines.append("")
        for label, path in result["figures"].items():
            lines.append(f"![{result['sample_id']} {label}]({rel(path, report_path)})")
            lines.append("")

    lines.extend(
        [
            "## 10. 本周结论",
            "",
            "1. DPC 已经补上动态检测与静态 defect map 的差异：动态看当前帧，静态看标定坐标。",
            "2. LSC 已经补上 flat-field / mesh LUT 的来源，但仍需真实均匀白场才能做产品级结论。",
            "3. Demosaic 已经有 OpenCV baseline 和 edge-aware 对照，下一步可以接 OpenISP Malvar 或 AHD 实作。",
            "4. AWB 已经从 Gray World 扩展到 White Patch 和 Gray ROI，能解释不同假设的失败场景。",
            "5. CCM 已经有 DeltaE 和差异放大图，能回答“视觉上不明显但数值上如何评价”。",
            "6. Gamma/Tone 已经补上 sRGB OETF 和 S-curve LUT，和 OpenISP GAC 的 LUT 思路接上了。",
            "7. IQA 已经从全图指标推进到 ROI 指标 + 主观标签，后续可以手工固定更有语义的肤色、天空、高光、暗部 ROI。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Week6 experiments that close ISP module mastery gaps.")
    parser.add_argument("raw_paths", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report", type=Path, default=Path("reports/week6/mastery_gap_closure_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--gamma", type=float, default=2.2)
    parser.add_argument("--tone-percentile", type=float, default=99.5)
    parser.add_argument("--max-size", type=int, default=1200, help="Center crop size for the Week6 analysis experiments. Use 0 for full size.")
    args = parser.parse_intermixed_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_paths = expand_paths(args.raw_paths)
    results = [
        evaluate_one(
            raw_path,
            args.out_dir,
            args.reference_dir,
            args.min_delta,
            args.mad_k,
            args.gamma,
            args.tone_percentile,
            args.max_size,
        )
        for raw_path in raw_paths
    ]
    json_path = args.out_dir / "week6_mastery_gap_closure.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    curve_path = args.out_dir / "week6_gamma_tone_curves.png"
    save_curve_plot(curve_path)
    write_report(results, args.report, curve_path)
    print(args.report)


if __name__ == "__main__":
    main()
