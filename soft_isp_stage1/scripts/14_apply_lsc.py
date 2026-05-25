from __future__ import annotations

import argparse
import json
import os
import sys
import glob
from pathlib import Path

import imageio.v3 as iio
import matplotlib
import numpy as np
import rawpy

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.blc import apply_blc
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.lsc import apply_lsc
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def raw_preview(raw_array: np.ndarray, display_white: float) -> np.ndarray:
    gray = np.clip(raw_array.astype(np.float32) / max(display_white, 1.0), 0.0, 1.0)
    gray8 = (gray * 255.0 + 0.5).astype(np.uint8)
    return np.repeat(gray8[:, :, None], 3, axis=2)


def gain_preview(gain_map: np.ndarray) -> np.ndarray:
    norm = (gain_map - np.min(gain_map)) / max(float(np.max(gain_map) - np.min(gain_map)), 1e-6)
    img = (norm * 255.0 + 0.5).astype(np.uint8)
    return np.repeat(img[:, :, None], 3, axis=2)


def save_compare(path: Path, title: str, panels: list[tuple[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(1, len(panels), figsize=(5.0 * len(panels), 4.2), constrained_layout=True)
    for ax, (panel_title, image) in zip(axes, panels):
        ax.imshow(image)
        ax.set_title(panel_title)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def analyze_one(raw_path: Path, out_dir: Path, min_delta: int, mad_k: float) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        raw_pattern = raw.raw_pattern.copy()
        black_levels = list(raw.black_level_per_channel)
        white_level = int(raw.white_level)
        display_flip = int(raw.sizes.flip)

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_blc = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    detection = detect_defects(raw_blc, bayer_pattern, min_delta=min_delta, mad_k=mad_k)
    raw_dpc = repair_defects(raw_blc, bayer_pattern, detection)
    raw_lsc, gain_map = apply_lsc(raw_dpc, bayer_pattern, white_level=white_level)

    display_white = float(np.percentile(raw_lsc, 99.5))
    before = apply_rawpy_orientation(raw_preview(raw_dpc, display_white), display_flip)
    after = apply_rawpy_orientation(raw_preview(raw_lsc, display_white), display_flip)
    gain = apply_rawpy_orientation(gain_preview(gain_map), display_flip)

    compare_path = out_dir / f"{raw_path.stem}_lsc_compare.png"
    save_compare(compare_path, raw_path.name, [("BLC + DPC", before), ("Radial LSC", after), ("Gain map", gain)])

    result = {
        "file": str(raw_path),
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "raw_dpc": describe_array(raw_dpc),
        "raw_lsc": describe_array(raw_lsc),
        "gain_map": describe_array(gain_map),
        "compare": str(compare_path),
    }
    (out_dir / f"{raw_path.stem}_lsc.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def rel(path: str, report_path: Path) -> str:
    return Path(os.path.relpath(path, report_path.parent)).as_posix()


def fmt(value: float) -> str:
    return f"{value:.3f}"


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 2-3 LSC 学习报告",
        "",
        "LSC 的全称是 Lens Shading Correction，镜头阴影校正。它处理的是位置相关的亮度和颜色不均匀：常见现象是中心较亮、边缘较暗，或者边缘带一点颜色偏移。",
        "",
        "## 本次实现边界",
        "",
        "这里实现的是学习用径向 LSC baseline，不是产品标定版。真实产品通常用积分球或均匀白场拍摄得到 R/Gr/Gb/B 的 gain map，并按镜头、焦距、光圈、色温准备多套表。",
        "",
        "本次默认只做保守补偿：中心 gain 为 1，越靠近边缘 gain 越高，且 R/Gr/Gb/B 可以有不同边缘增益。它的价值是把 LSC 放回 pipeline 的正确位置，并观察它如何影响后续 AWB/CCM。",
        "",
        "## Pipeline 位置",
        "",
        "```text",
        "RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone/Gamma",
        "```",
        "",
        "LSC 放在 Demosaic 之前，因为镜头阴影发生在 RAW/Bayer 域。越早处理，越不容易把位置相关的亮度/色偏带进 AWB 的全局统计。",
        "",
        "## 结果总表",
        "",
        "| 样张 | Bayer | gain min | gain max | RAW mean before | RAW mean after | 观察 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            "| {sid} | {pattern} | {gmin} | {gmax} | {before} | {after} | 边缘被保守抬升，噪声也会同步放大 |".format(
                sid=result["sample_id"],
                pattern=result["bayer_pattern"],
                gmin=fmt(result["gain_map"]["min"]),
                gmax=fmt(result["gain_map"]["max"]),
                before=fmt(result["raw_dpc"]["mean"]),
                after=fmt(result["raw_lsc"]["mean"]),
            )
        )

    lines.extend(["", "## LSC 对比图", ""])
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} LSC compare]({rel(result['compare'], report_path)})", ""])

    lines.extend(
        [
            "## 失败场景和注意点",
            "",
            "1. 没有 flat-field 标定时，径向模型可能把真实场景的暗角误当成镜头问题。",
            "2. LSC 会放大边缘信号，也会放大边缘噪声，所以不能只看亮度是否更均匀。",
            "3. 如果不同颜色通道 gain 不合理，AWB 会被新的边缘色偏带偏。",
            "4. 当前实现用于学习 pipeline 位置和数据域，不应当被当作相机标定结果。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def expand_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        text = str(path)
        if any(char in text for char in "*?[]"):
            expanded.extend(Path(match) for match in glob.glob(text))
        else:
            expanded.append(path)
    return sorted(expanded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply learning radial LSC and write a report.")
    parser.add_argument("raw_paths", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--report", type=Path, default=Path("reports/week2/lsc_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    args = parser.parse_intermixed_args()

    raw_paths = expand_paths(args.raw_paths)
    results = [analyze_one(raw_path, args.out_dir, args.min_delta, args.mad_k) for raw_path in raw_paths]
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
