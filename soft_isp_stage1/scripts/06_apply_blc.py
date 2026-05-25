"""BLC（黑电平校正）实验脚本 —— 从 RAW 扣除黑电平并生成前后对比报告。

用法:
    python 06_apply_blc.py <raw_path>... [--out-dir reports/figures] [--bins 512]

功能:
    读取 DNG 文件的 black_level 元数据，按 Bayer 位置扣除黑电平偏置，
    生成 BLC 前后的视觉对比图和直方图对比图，并汇总为 Week 2 的 BLC 学习报告。

BLC 公式:
    corrected = clip(raw - black_level, 0, white_level - black_level)

输出:
    - {sample}_blc_visual_compare.png: BLC 前后灰度预览并排对比
    - {sample}_blc_hist_compare.png:   BLC 前后直方图叠加对比
    - {sample}_blc.json:               逐通道统计信息
    - reports/week2/blc_report.md:     汇总 Markdown 报告
"""

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.blc import apply_blc
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array, split_bayer


CHANNEL_ORDER = ("R", "Gr", "Gb", "B")
CHANNEL_COLORS = {
    "R": "#d62728",
    "Gr": "#2ca02c",
    "Gb": "#1f9d55",
    "B": "#1f77b4",
}


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def channel_stats(raw_array: np.ndarray, bayer_pattern: str) -> dict:
    return {
        name: describe_array(channel)
        for name, channel in split_bayer(raw_array, bayer_pattern).items()
    }


def make_preview(raw_array: np.ndarray, display_max: float) -> np.ndarray:
    gray = np.clip(raw_array.astype(np.float32) / max(display_max, 1.0), 0.0, 1.0)
    gray8 = (gray * 255).astype(np.uint8)
    return np.repeat(gray8[:, :, None], 3, axis=2)


def plot_blc_visual_compare(
    raw_path: Path,
    raw_visible: np.ndarray,
    corrected: np.ndarray,
    out_dir: Path,
    display_flip: int,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{raw_path.stem}_blc_visual_compare.png"
    display_max = max(float(np.percentile(raw_visible, 99.5)), float(np.percentile(corrected, 99.5)), 1.0)
    before_preview = apply_rawpy_orientation(make_preview(raw_visible, display_max), display_flip)
    after_preview = apply_rawpy_orientation(make_preview(corrected, display_max), display_flip)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4), constrained_layout=True)
    axes[0].imshow(before_preview)
    axes[0].set_title("Before BLC")
    axes[1].imshow(after_preview)
    axes[1].set_title("After BLC")
    for ax in axes:
        ax.set_axis_off()

    fig.suptitle(raw_path.name)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def plot_blc_compare(
    raw_path: Path,
    raw_visible: np.ndarray,
    corrected: np.ndarray,
    bayer_pattern: str,
    black_levels: list[int],
    white_level: int,
    out_dir: Path,
    bins: int,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{raw_path.stem}_blc_hist_compare.png"

    corrected_white_min = max(white_level - max(black_levels), 0)
    corrected_white_max = max(white_level - min(black_levels), 0)
    raw_channels = split_bayer(raw_visible, bayer_pattern)
    corrected_channels = split_bayer(corrected, bayer_pattern)

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    fig.suptitle(f"{raw_path.name} BLC histogram compare ({bayer_pattern})")

    axes[0].hist(raw_visible.ravel(), bins=bins, histtype="step", color="#666666", log=True, label="before BLC")
    axes[0].hist(corrected.ravel(), bins=bins, histtype="step", color="#111111", log=True, label="after BLC")
    for black_level in sorted(set(black_levels)):
        axes[0].axvline(black_level, color="#222222", linestyle=":", linewidth=1.0, label=f"black level {black_level}")
    axes[0].axvline(white_level, color="#d62728", linestyle="--", linewidth=1.1, label="white level before")
    axes[0].axvline(corrected_white_min, color="#ff7f0e", linestyle="--", linewidth=1.1, label="white level after min")
    if corrected_white_max != corrected_white_min:
        axes[0].axvline(corrected_white_max, color="#ff7f0e", linestyle=":", linewidth=1.1, label="white level after max")
    axes[0].set_title("All Bayer samples")
    axes[0].set_xlabel("RAW value")
    axes[0].set_ylabel("Pixel count (log)")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    for name in CHANNEL_ORDER:
        axes[1].hist(
            raw_channels[name].ravel(),
            bins=bins,
            histtype="step",
            linewidth=0.9,
            color=CHANNEL_COLORS[name],
            alpha=0.35,
            log=True,
            label=f"{name} before",
        )
        axes[1].hist(
            corrected_channels[name].ravel(),
            bins=bins,
            histtype="step",
            linewidth=1.2,
            color=CHANNEL_COLORS[name],
            log=True,
            label=f"{name} after",
        )

    axes[1].set_title("Bayer channel samples")
    axes[1].set_xlabel("RAW value")
    axes[1].set_ylabel("Pixel count (log)")
    axes[1].grid(alpha=0.25)
    axes[1].legend(ncol=2, fontsize=8)

    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def analyze_one(raw_path: Path, out_dir: Path, bins: int) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        raw_pattern = raw.raw_pattern.copy()
        black_levels = list(raw.black_level_per_channel)
        white_level = int(raw.white_level)
        display_flip = int(raw.sizes.flip)

    corrected = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    visual_path = plot_blc_visual_compare(raw_path, raw_visible, corrected, out_dir, display_flip)
    figure_path = plot_blc_compare(
        raw_path,
        raw_visible,
        corrected,
        bayer_pattern,
        black_levels,
        white_level,
        out_dir,
        bins,
    )

    result = {
        "file": str(raw_path),
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level_before": white_level,
        "white_level_after_min": max(white_level - max(black_levels), 0),
        "white_level_after_max": max(white_level - min(black_levels), 0),
        "raw": describe_array(raw_visible),
        "blc": describe_array(corrected),
        "channels_before": channel_stats(raw_visible, bayer_pattern),
        "channels_after": channel_stats(corrected, bayer_pattern),
        "visual_compare": str(visual_path),
        "figure": str(figure_path),
    }

    json_path = out_dir / f"{raw_path.stem}_blc.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def fmt(value: float) -> str:
    return f"{value:.2f}"


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 2 BLC 学习报告",
        "",
        "本次只做一个小闭环：读取 RAW metadata 里的 black level，按 Bayer 位置扣除黑电平，然后观察直方图和统计量的变化。",
        "",
        "## BLC 做了什么",
        "",
        "BLC 的全称是 Black Level Correction，中文可以理解为黑电平校正。RAW 数值里不只有真实光信号，还包含传感器和读出电路带来的基础偏置。这个偏置就是 black level。",
        "",
        "本次实现的公式是：",
        "",
        "```text",
        "corrected = raw - black_level",
        "corrected = clip(corrected, 0, white_level - black_level)",
        "```",
        "",
        "如果一张图的 black level 是 0，那么 BLC 前后应该几乎不变；如果 black level 不为 0，暗部会向 0 移动，后续 demosaic、AWB、颜色校正才是在真实光信号上继续做。",
        "",
        "## 结果总表",
        "",
        "| 样张 | Bayer | black level | white before | white after | p50 before | p50 after | mean before | mean after | 结论 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for result in results:
        black_levels = result["black_level_per_channel"]
        if all(level == 0 for level in black_levels):
            conclusion = "black level 为 0，BLC 是 identity case"
        else:
            conclusion = "暗部基线被扣除，RAW 数值回到真实信号起点"
        white_after = str(result["white_level_after_min"])
        if result["white_level_after_min"] != result["white_level_after_max"]:
            white_after = f"{result['white_level_after_min']}-{result['white_level_after_max']}"
        lines.append(
            "| {sid} | {pattern} | {black} | {wb} | {wa} | {p50b} | {p50a} | {meanb} | {meana} | {conclusion} |".format(
                sid=result["sample_id"],
                pattern=result["bayer_pattern"],
                black="/".join(str(v) for v in black_levels),
                wb=result["white_level_before"],
                wa=white_after,
                p50b=fmt(float(result["raw"]["p50"])),
                p50a=fmt(float(result["blc"]["p50"])),
                meanb=fmt(float(result["raw"]["mean"])),
                meana=fmt(float(result["blc"]["mean"])),
                conclusion=conclusion,
            )
        )

    lines.extend(
        [
            "",
            "## 视觉前后对比",
            "",
            "这组图把 BLC 前后的 RAW 当成灰度图显示，并用同一个显示上限做缩放。重点不是看颜色，而是看暗部基线有没有被扣掉。当前这批样张大多 black level 为 0，所以视觉上通常几乎不变；这反而说明 BLC 在这些样张上是一个 identity case。",
            "",
        ]
    )

    for result in results:
        visual_rel = Path(os.path.relpath(result["visual_compare"], report_path.parent)).as_posix()
        lines.extend(
            [
                f"### {result['sample_id']}",
                "",
                f"![{result['sample_id']} BLC visual compare]({visual_rel})",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "## 对比直方图",
            "",
            "看图时重点看两件事：第一，after BLC 的分布是否整体左移；第二，暗部是否从 black level 附近移动到 0 附近。",
            "",
        ]
    )

    for result in results:
        figure_rel = Path(os.path.relpath(result["figure"], report_path.parent)).as_posix()
        lines.extend(
            [
                f"### {result['sample_id']}",
                "",
                f"![{result['sample_id']} BLC histogram compare]({figure_rel})",
                "",
            ]
        )

    lines.extend(
        [
            "## 分样张观察",
            "",
        ]
    )

    for result in results:
        lines.extend(
            [
                f"### {result['sample_id']}",
                "",
                f"- black level: `{result['black_level_per_channel']}`",
                f"- BLC 前：min `{fmt(float(result['raw']['min']))}`，p50 `{fmt(float(result['raw']['p50']))}`，p99 `{fmt(float(result['raw']['p99']))}`",
                f"- BLC 后：min `{fmt(float(result['blc']['min']))}`，p50 `{fmt(float(result['blc']['p50']))}`，p99 `{fmt(float(result['blc']['p99']))}`",
                "",
            ]
        )

    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. BLC 不是调亮或调暗图片，而是把传感器的基线偏置扣掉。",
            "2. black level 为 0 时，BLC 可以保留这个步骤，但结果应基本不变，用来验证流程没有破坏数据。",
            "3. black level 不为 0 时，必须先扣除，再进入 demosaic/AWB；否则后面的颜色和亮度判断都会带着偏置。",
            "4. BLC 后有效白电平变成 `white_level - black_level`；如果四通道 black level 不完全一样，有效白电平也会按 Bayer 位置略有差异。",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply black level correction and write a learning report.")
    parser.add_argument("raw_paths", type=Path, nargs="+", help="One or more RAW/DNG files.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--report", type=Path, default=Path("reports/week2/blc_report.md"))
    parser.add_argument("--bins", type=int, default=512)
    args = parser.parse_args()

    results = [analyze_one(raw_path, args.out_dir, args.bins) for raw_path in args.raw_paths]
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
