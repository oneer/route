from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import imageio.v3 as iio
import numpy as np
import rawpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.blc import apply_blc
from soft_isp.demosaic import demosaic_bilinear, normalize_rgb
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def save_preview(rgb: np.ndarray, out_path: Path, white_level: float) -> Path:
    preview = (normalize_rgb(rgb, white_level) * 255.0).round().astype(np.uint8)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(out_path, preview)
    return out_path


def opencv_demosaic(raw_blc: np.ndarray, bayer_pattern: str) -> np.ndarray | None:
    try:
        import cv2
    except ImportError:
        return None

    code_by_pattern = {
        "RGGB": cv2.COLOR_BayerRG2RGB,
        "BGGR": cv2.COLOR_BayerBG2RGB,
        "GRBG": cv2.COLOR_BayerGR2RGB,
        "GBRG": cv2.COLOR_BayerGB2RGB,
    }
    code = code_by_pattern[bayer_pattern.upper()]
    return cv2.cvtColor(raw_blc, code).astype(np.float32)


def analyze_one(
    raw_path: Path,
    out_dir: Path,
    apply_dpc: bool,
    min_delta: int,
    mad_k: float,
) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        raw_pattern = raw.raw_pattern.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        black_levels = list(raw.black_level_per_channel)
        white_level = int(raw.white_level)

    raw_blc = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    raw_for_demosaic = raw_blc
    dpc_candidate_count = 0

    if apply_dpc:
        detection = detect_defects(raw_blc, bayer_pattern, min_delta=min_delta, mad_k=mad_k)
        raw_for_demosaic = repair_defects(raw_blc, bayer_pattern, detection)
        dpc_candidate_count = int(sum(mask.sum() for mask in detection["masks"].values()))

    rgb = demosaic_bilinear(raw_for_demosaic, bayer_pattern)
    effective_white = max(float(white_level - max(black_levels)), 1.0)
    preview_path = save_preview(rgb, out_dir / f"{raw_path.stem}_bilinear_rgb.png", effective_white)

    opencv_rgb = opencv_demosaic(raw_for_demosaic, bayer_pattern)
    opencv_path = None
    diff_mean = None
    diff_p99 = None
    if opencv_rgb is not None:
        opencv_path = save_preview(opencv_rgb, out_dir / f"{raw_path.stem}_opencv_rgb.png", effective_white)
        diff = np.abs(rgb.astype(np.float32) - opencv_rgb.astype(np.float32))
        diff_mean = float(np.mean(diff))
        diff_p99 = float(np.percentile(diff, 99))

    result = {
        "file": str(raw_path),
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "effective_white_after_blc": effective_white,
        "dpc_enabled": apply_dpc,
        "dpc_candidate_count": dpc_candidate_count,
        "raw_for_demosaic": describe_array(raw_for_demosaic),
        "rgb_bilinear": describe_array(rgb),
        "preview": str(preview_path),
        "opencv_preview": str(opencv_path) if opencv_path else None,
        "opencv_diff_mean": diff_mean,
        "opencv_diff_p99": diff_p99,
    }

    json_path = out_dir / f"{raw_path.stem}_demosaic.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}" if abs(value) < 1 else f"{value:.2f}"


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 3-1 Demosaic 学习报告",
        "",
        "本次实现最基础的 bilinear demosaic：先在 Bayer RAW 上保留已有采样点，再用周围同色像素的加权平均补齐缺失的 R/G/B 通道。",
        "",
        "## 为什么需要 Demosaic",
        "",
        "Bayer RAW 的每个像素只记录一种颜色，无法直接显示为 RGB 图像。Demosaic 的任务是把单通道马赛克 RAW 转换成三通道 linear RGB，为后续 AWB、CCM、Gamma/Tone 做准备。",
        "",
        "## 本次算法",
        "",
        "```text",
        "RAW -> BLC -> DPC -> Bilinear Demosaic -> linear RGB",
        "",
        "R/B 缺失值：用附近同色 R/B 像素按 bilinear kernel 插值",
        "G 缺失值：用附近 Gr/Gb 像素按 bilinear kernel 插值",
        "已有 Bayer 采样点：保留原始值，不被插值覆盖",
        "```",
        "",
        "Bilinear 的优点是简单、稳定、容易解释；缺点是不会判断边缘方向，所以在斜边、高频纹理和细线附近容易出现模糊、zipper artifact 和 false color。",
        "",
        "## 结果总表",
        "",
        "| 样张 | Bayer | DPC 候选数 | RGB min | RGB p50 | RGB p99 | OpenCV diff mean | OpenCV diff p99 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        stats = result["rgb_bilinear"]
        lines.append(
            "| {sid} | {pattern} | {dpc} | {minv} | {p50} | {p99} | {diff_mean} | {diff_p99} |".format(
                sid=result["sample_id"],
                pattern=result["bayer_pattern"],
                dpc=result["dpc_candidate_count"],
                minv=fmt(float(stats["min"])),
                p50=fmt(float(stats["p50"])),
                p99=fmt(float(stats["p99"])),
                diff_mean=fmt(result["opencv_diff_mean"]),
                diff_p99=fmt(result["opencv_diff_p99"]),
            )
        )

    lines.extend(["", "## 预览图", ""])
    for result in results:
        preview_rel = Path(result["preview"]).relative_to(report_path.parent).as_posix()
        lines.extend([f"### {result['sample_id']} bilinear", "", f"![{result['sample_id']} bilinear RGB]({preview_rel})", ""])
        if result["opencv_preview"]:
            opencv_rel = Path(result["opencv_preview"]).relative_to(report_path.parent).as_posix()
            lines.extend([f"![{result['sample_id']} OpenCV RGB]({opencv_rel})", ""])

    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. Demosaic 是从 Bayer RAW 进入 RGB 图像的第一步，输出仍然是 linear RGB，不是最终 sRGB 成片。",
            "2. Bayer pattern 必须正确；模式选错会导致颜色通道错位和明显偏色。",
            "3. Bilinear 只做局部平均，不理解边缘方向，所以高频纹理和斜边附近会有伪彩、拉链状边缘和模糊。",
            "4. DPC 的价值会在 Demosaic 后更明显：坏点如果不先修，会被插值扩散到多个 RGB 像素。",
            "",
            "## 下一步",
            "",
            "在 bilinear RGB 输出稳定后，下一步做 gray-world AWB，让 RGB 通道比例更接近可观看的颜色。",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply BLC + DPC + bilinear demosaic and write a learning report.")
    parser.add_argument("raw_paths", type=Path, nargs="+", help="One or more RAW/DNG files.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--report", type=Path, default=Path("reports/week3_demosaic_report.md"))
    parser.add_argument("--skip-dpc", action="store_true", help="Run demosaic directly after BLC.")
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    args = parser.parse_intermixed_args()

    results = [
        analyze_one(raw_path, args.out_dir, not args.skip_dpc, args.min_delta, args.mad_k)
        for raw_path in args.raw_paths
    ]
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
