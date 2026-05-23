from __future__ import annotations

import argparse
import json
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
from soft_isp.demosaic import bilinear_demosaic, rgb_preview
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def describe_rgb(rgb: np.ndarray) -> dict:
    return {
        "shape": rgb.shape,
        "dtype": str(rgb.dtype),
        "R": describe_array(rgb[:, :, 0]),
        "G": describe_array(rgb[:, :, 1]),
        "B": describe_array(rgb[:, :, 2]),
    }


def channel_means(rgb: np.ndarray) -> list[float]:
    return [float(np.mean(rgb[:, :, index])) for index in range(3)]


def save_compare_figure(
    raw_path: Path,
    before_preview: np.ndarray,
    after_preview: np.ndarray,
    reference_dir: Path,
    out_dir: Path,
) -> Path:
    out_path = out_dir / f"{raw_path.stem}_awb_compare.png"
    reference_path = reference_dir / f"{raw_path.stem}_rawpy_srgb.png"

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    axes[0].imshow(before_preview)
    axes[0].set_title("Before AWB")
    axes[1].imshow(after_preview)
    axes[1].set_title("After gray-world AWB")

    if reference_path.exists():
        axes[2].imshow(iio.imread(reference_path))
        axes[2].set_title("rawpy reference ISP")
    else:
        axes[2].imshow(np.zeros_like(after_preview))
        axes[2].set_title("rawpy reference missing")

    for ax in axes:
        ax.set_axis_off()

    fig.suptitle(raw_path.name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def analyze_one(
    raw_path: Path,
    out_dir: Path,
    reference_dir: Path,
    min_delta: int,
    mad_k: float,
    low_percentile: float,
    high_percentile: float,
) -> dict:
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
    rgb_linear = bilinear_demosaic(raw_dpc, bayer_pattern)

    gains = gray_world_gains(
        rgb_linear,
        low_percentile=low_percentile,
        high_percentile=high_percentile,
    )
    rgb_awb = apply_awb(rgb_linear, gains, white_level=white_level)

    display_white = max(float(np.percentile(rgb_linear, 99.5)), float(np.percentile(rgb_awb, 99.5)), 1.0)
    before_preview = apply_rawpy_orientation(rgb_preview(rgb_linear, white=display_white), display_flip)
    after_preview = apply_rawpy_orientation(rgb_preview(rgb_awb, white=display_white), display_flip)

    before_path = out_dir / f"{raw_path.stem}_awb_before.png"
    after_path = out_dir / f"{raw_path.stem}_awb_after.png"
    iio.imwrite(before_path, before_preview)
    iio.imwrite(after_path, after_preview)
    compare_path = save_compare_figure(raw_path, before_preview, after_preview, reference_dir, out_dir)

    before_means = channel_means(rgb_linear)
    after_means = channel_means(rgb_awb)
    result = {
        "file": str(raw_path),
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "display_flip": display_flip,
        "gray_world_low_percentile": low_percentile,
        "gray_world_high_percentile": high_percentile,
        "gains_rgb": [float(v) for v in gains],
        "means_before_rgb": before_means,
        "means_after_rgb": after_means,
        "rg_ratio_before": float(before_means[0] / max(before_means[1], 1e-6)),
        "bg_ratio_before": float(before_means[2] / max(before_means[1], 1e-6)),
        "rg_ratio_after": float(after_means[0] / max(after_means[1], 1e-6)),
        "bg_ratio_after": float(after_means[2] / max(after_means[1], 1e-6)),
        "rgb_before_awb": describe_rgb(rgb_linear),
        "rgb_after_awb": describe_rgb(rgb_awb),
        "before_preview": str(before_path),
        "after_preview": str(after_path),
        "compare": str(compare_path),
    }

    json_path = out_dir / f"{raw_path.stem}_awb.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def fmt(value: float) -> str:
    return f"{value:.3f}"


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 3 AWB 学习报告",
        "",
        "本次完成 Week3 的第二个核心模块：AWB，也就是 Auto White Balance，自动白平衡。输入是 Demosaic 后的线性 RGB，输出仍然是线性 RGB，只是每个颜色通道乘了不同的 gain。",
        "",
        "## AWB 解决什么问题",
        "",
        "Demosaic 只是把 Bayer RAW 补成 RGB，它不会让颜色变准。传感器的 R/G/B 响应、光源颜色、镜头透过率都会让图像偏色。AWB 的目标是估计光源颜色，并用通道增益把中性物体拉回接近灰色。",
        "",
        "白平衡最核心的形式很简单：",
        "",
        "```text",
        "R_awb = R * R_gain",
        "G_awb = G * G_gain",
        "B_awb = B * B_gain",
        "```",
        "",
        "本次为了学习，固定 `G_gain = 1`，让 R 和 B 向 G 对齐。",
        "",
        "## Gray World 假设",
        "",
        "Gray World 的假设是：如果一张图包含足够多不同颜色的物体，那么整张图的平均颜色应该接近灰色。灰色意味着 R、G、B 三个通道平均值接近。",
        "",
        "所以可以用下面的公式估计 gain：",
        "",
        "```text",
        "R_gain = G_mean / R_mean",
        "G_gain = 1",
        "B_gain = G_mean / B_mean",
        "```",
        "",
        "本次实现会先排除最暗的 5% 和最亮的 5% 像素，再计算均值。这样可以减少黑场噪声和高光饱和区域对白平衡估计的影响。",
        "",
        "## 结果总表",
        "",
        "| 样张 | Bayer | R gain | G gain | B gain | R/G before | B/G before | R/G after | B/G after | 观察 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for result in results:
        gains = result["gains_rgb"]
        observation = "通道均值更接近，但颜色仍未经过 CCM/Gamma"
        lines.append(
            "| {sid} | {pattern} | {rgain} | {ggain} | {bgain} | {rgb} | {bgb} | {rga} | {bga} | {obs} |".format(
                sid=result["sample_id"],
                pattern=result["bayer_pattern"],
                rgain=fmt(gains[0]),
                ggain=fmt(gains[1]),
                bgain=fmt(gains[2]),
                rgb=fmt(result["rg_ratio_before"]),
                bgb=fmt(result["bg_ratio_before"]),
                rga=fmt(result["rg_ratio_after"]),
                bga=fmt(result["bg_ratio_after"]),
                obs=observation,
            )
        )

    lines.extend(["", "## AWB 前后对比", ""])
    for result in results:
        compare_rel = Path(os.path.relpath(result["compare"], report_path.parent)).as_posix()
        lines.extend(
            [
                f"### {result['sample_id']}",
                "",
                f"![{result['sample_id']} AWB compare]({compare_rel})",
                "",
            ]
        )

    lines.extend(
        [
            "## 怎么验证 AWB 是否有效",
            "",
            "第一，看数值：AWB 后的 `R/G` 和 `B/G` 应该比 AWB 前更接近 1。第二，看图像：明显偏绿、偏蓝或偏红的趋势应该减轻。第三，不能只看是否“好看”，因为当前还没有做 CCM、Gamma 和 Tone Mapping。",
            "",
            "## 失败场景",
            "",
            "Gray World 很简单，也很容易失败。比如画面里大面积草地、天空、红墙、舞台灯，整张图的平均颜色本来就不该是灰色，这时它会把真实颜色错误地中和掉。混合光源也会失败，因为不同区域需要不同白平衡，单一 RGB gain 无法同时修正。",
            "",
            "## 今天要记住的结论",
            "",
            "1. AWB 的输入是 Demosaic 后的线性 RGB，不是 sRGB 图片。",
            "2. AWB 本质是估计并应用每通道 gain，不是复杂调色。",
            "3. Gray World 是一个可解释的 baseline，适合学习和建立直觉。",
            "4. AWB 后颜色仍然不等于最终照片，因为还缺 CCM、Gamma/Tone。",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply BLC + DPC + demosaic + gray-world AWB.")
    parser.add_argument("raw_paths", type=Path, nargs="+", help="One or more RAW/DNG files.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report", type=Path, default=Path("reports/week3/awb_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--low-percentile", type=float, default=5.0)
    parser.add_argument("--high-percentile", type=float, default=95.0)
    args = parser.parse_intermixed_args()

    results = [
        analyze_one(
            raw_path,
            args.out_dir,
            args.reference_dir,
            args.min_delta,
            args.mad_k,
            args.low_percentile,
            args.high_percentile,
        )
        for raw_path in args.raw_paths
    ]
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
