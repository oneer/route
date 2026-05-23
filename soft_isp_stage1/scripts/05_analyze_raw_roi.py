from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib
import numpy as np
import rawpy

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.orientation import apply_rawpy_orientation, transform_box_for_orientation
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array, split_bayer


ROI_TARGETS = {
    "dark": 5,
    "midtone": 50,
    "highlight": 99,
}

ROI_COLORS = {
    "dark": "#1f77b4",
    "midtone": "#2ca02c",
    "highlight": "#d62728",
}


def make_raw_preview(raw_visible: np.ndarray, black_levels: list[int], white_level: int) -> np.ndarray:
    black_level = min(black_levels)
    display_max = min(float(np.percentile(raw_visible, 99.5)), float(white_level))
    if display_max <= black_level:
        display_max = float(np.max(raw_visible))

    normalized = (raw_visible.astype(np.float32) - black_level) / (display_max - black_level)
    gray = np.clip(normalized, 0.0, 1.0)
    gray8 = (gray * 255).astype(np.uint8)
    return np.repeat(gray8[:, :, None], 3, axis=2)


def pick_roi(raw_visible: np.ndarray, target_value: float, roi_size: int, stride: int) -> dict[str, int | float]:
    height, width = raw_visible.shape
    best: dict[str, int | float] | None = None

    for y in range(0, height - roi_size + 1, stride):
        for x in range(0, width - roi_size + 1, stride):
            roi = raw_visible[y : y + roi_size, x : x + roi_size]
            mean = float(np.mean(roi))
            score = abs(mean - target_value)
            if best is None or score < float(best["score"]):
                best = {"x": x, "y": y, "w": roi_size, "h": roi_size, "mean": mean, "score": score}

    if best is None:
        raise ValueError(f"ROI size {roi_size} is too large for RAW shape {raw_visible.shape}")
    return best


def roi_channel_means(raw_visible: np.ndarray, bayer_pattern: str, roi: dict[str, int | float]) -> dict[str, float]:
    x = int(roi["x"])
    y = int(roi["y"])
    w = int(roi["w"])
    h = int(roi["h"])

    if x % 2:
        x -= 1
    if y % 2:
        y -= 1
    if w % 2:
        w -= 1
    if h % 2:
        h -= 1

    roi_raw = raw_visible[y : y + h, x : x + w]
    channels = split_bayer(roi_raw, bayer_pattern)
    return {name: float(np.mean(channel)) for name, channel in channels.items()}


def annotate_preview(
    preview: np.ndarray,
    raw_shape: tuple[int, int],
    rois: dict[str, dict[str, int | float]],
    out_path: Path,
    display_flip: int,
) -> None:
    preview = apply_rawpy_orientation(preview, display_flip)
    preview_height, preview_width = preview.shape[:2]
    raw_height, raw_width = raw_shape
    oriented_raw_height, oriented_raw_width = apply_rawpy_orientation(np.zeros(raw_shape, dtype=np.uint8), display_flip).shape[:2]
    scale_x = preview_width / oriented_raw_width
    scale_y = preview_height / oriented_raw_height

    fig, ax = plt.subplots(figsize=(10, 7), constrained_layout=True)
    ax.imshow(preview)
    ax.set_axis_off()

    for name, roi in rois.items():
        box_x, box_y, box_w, box_h = transform_box_for_orientation(
            float(roi["x"]),
            float(roi["y"]),
            float(roi["w"]),
            float(roi["h"]),
            raw_shape,
            display_flip,
        )
        x = box_x * scale_x
        y = box_y * scale_y
        w = box_w * scale_x
        h = box_h * scale_y
        color = ROI_COLORS[name]
        ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=color, linewidth=2.0))
        ax.text(x, max(y - 6, 0), name, color=color, fontsize=11, weight="bold")

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def analyze_raw(raw_path: Path, out_dir: Path, roi_size: int, stride: int) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        black_levels = list(raw.black_level_per_channel)
        white_level = raw.white_level
        display_flip = int(raw.sizes.flip)

    preview = make_raw_preview(raw_visible, black_levels, white_level)

    targets = {
        name: float(np.percentile(raw_visible, percentile))
        for name, percentile in ROI_TARGETS.items()
    }

    rois = {
        name: pick_roi(raw_visible, target_value, roi_size, stride)
        for name, target_value in targets.items()
    }

    roi_results = {}
    for name, roi in rois.items():
        x = int(roi["x"])
        y = int(roi["y"])
        w = int(roi["w"])
        h = int(roi["h"])
        roi_raw = raw_visible[y : y + h, x : x + w]
        stats = describe_array(roi_raw)
        channel_means = roi_channel_means(raw_visible, bayer_pattern, roi)
        roi_results[name] = {
            "target_percentile": ROI_TARGETS[name],
            "target_value": targets[name],
            "roi": {"x": x, "y": y, "w": w, "h": h},
            "stats": stats,
            "channel_means": channel_means,
            "near_black": float(stats["p50"]) <= max(black_levels) + 64,
            "near_white": float(stats["p99"]) >= white_level * 0.98,
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    preview_path = out_dir / f"{raw_path.stem}_roi_preview.png"
    json_path = out_dir / f"{raw_path.stem}_roi.json"
    annotate_preview(preview, raw_visible.shape, rois, preview_path, display_flip)

    result = {
        "file": str(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "display_flip": display_flip,
        "roi_size": roi_size,
        "stride": stride,
        "preview": str(preview_path),
        "rois": roi_results,
    }
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def format_number(value: float) -> str:
    return f"{value:.2f}"


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 1 ROI 分析",
        "",
        "本报告把 histogram 里的暗部、中间亮度、高光，映射回图像上的具体区域。ROI 由脚本自动选择：暗部接近 p05，中间亮度接近 p50，高光接近 p99。",
        "",
        "标注图使用 RAW 数值直接生成灰度预览，而不是 rawpy 的彩色后处理图。ROI 统计仍然基于 RAW 原始坐标；为了阅读舒服，写入报告的预览图会按相机 display orientation 旋正。",
        "",
        "## ROI 标注图",
        "",
    ]

    for result in results:
        sample_id = Path(result["file"]).name.split("_", 1)[0]
        preview_rel = Path(os.path.relpath(result["preview"], report_path.parent)).as_posix()
        lines.extend(
            [
                f"### {sample_id}",
                "",
                f"![{sample_id} ROI preview]({preview_rel})",
                "",
            ]
        )

    lines.extend(
        [
            "## ROI 统计表",
            "",
            "| 样张 | ROI | 坐标 x,y,w,h | min/max | mean/std | p50/p99 | R mean | Gr mean | Gb mean | B mean | 判断 |",
            "|---|---|---|---|---|---|---:|---:|---:|---:|---|",
        ]
    )

    for result in results:
        sample_id = Path(result["file"]).name.split("_", 1)[0]
        for roi_name in ("dark", "midtone", "highlight"):
            roi_result = result["rois"][roi_name]
            roi = roi_result["roi"]
            stats = roi_result["stats"]
            channels = roi_result["channel_means"]
            flags = []
            if roi_result["near_black"]:
                flags.append("接近 black level")
            if roi_result["near_white"]:
                flags.append("接近 white level")
            judgment = "；".join(flags) if flags else "未贴近黑/白电平"
            lines.append(
                "| {sample} | {roi_name} | {x},{y},{w},{h} | {minv}/{maxv} | {mean}/{std} | {p50}/{p99} | {r} | {gr} | {gb} | {b} | {judgment} |".format(
                    sample=sample_id,
                    roi_name=roi_name,
                    x=roi["x"],
                    y=roi["y"],
                    w=roi["w"],
                    h=roi["h"],
                    minv=format_number(float(stats["min"])),
                    maxv=format_number(float(stats["max"])),
                    mean=format_number(float(stats["mean"])),
                    std=format_number(float(stats["std"])),
                    p50=format_number(float(stats["p50"])),
                    p99=format_number(float(stats["p99"])),
                    r=format_number(channels["R"]),
                    gr=format_number(channels["Gr"]),
                    gb=format_number(channels["Gb"]),
                    b=format_number(channels["B"]),
                    judgment=judgment,
                )
            )

    lines.extend(
        [
            "",
            "## 初步结论",
            "",
            "1. `dark` ROI 用来观察暗部是否贴近 black level；如果 p50 接近 black level，BLC 后大量像素可能被压到 0。",
            "2. `midtone` ROI 用来观察主体曝光区域，是后续比较 BLC、AWB、Demosaic 前后变化的稳定参考。",
            "3. `highlight` ROI 用来观察高光是否贴近 white level；如果 p99 接近或达到 white level，说明该区域可能已经 clipping。",
            "4. ROI 坐标来自自动滑窗选择，下一步可以打开标注图，人工确认这些框是否落在合理图像区域。",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze dark/midtone/highlight ROIs in RAW files.")
    parser.add_argument("raw_paths", type=Path, nargs="+", help="One or more RAW/DNG files.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--report", type=Path, default=Path("reports/week1/roi_analysis.md"))
    parser.add_argument("--roi-size", type=int, default=256)
    parser.add_argument("--stride", type=int, default=128)
    args = parser.parse_args()

    results = [analyze_raw(raw_path, args.out_dir, args.roi_size, args.stride) for raw_path in args.raw_paths]
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
