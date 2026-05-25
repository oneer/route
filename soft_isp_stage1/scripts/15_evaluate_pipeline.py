from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import imageio.v3 as iio
import matplotlib
import numpy as np
import rawpy
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.awb import apply_awb, gray_world_gains
from soft_isp.blc import apply_blc
from soft_isp.ccm import apply_ccm, ccm_from_rawpy_color_matrix
from soft_isp.demosaic import bilinear_demosaic
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.lsc import apply_lsc
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy
from soft_isp.tone import apply_gamma, normalize_by_percentile, reinhard_tone_map, to_uint8


VARIANTS = {
    "full": {"dpc": True, "lsc": True, "awb": True, "ccm": True, "tone": True},
    "no_lsc": {"dpc": True, "lsc": False, "awb": True, "ccm": True, "tone": True},
    "no_dpc": {"dpc": False, "lsc": True, "awb": True, "ccm": True, "tone": True},
    "no_awb": {"dpc": True, "lsc": True, "awb": False, "ccm": True, "tone": True},
    "no_ccm": {"dpc": True, "lsc": True, "awb": True, "ccm": False, "tone": True},
    "gamma_only": {"dpc": True, "lsc": True, "awb": True, "ccm": True, "tone": False},
}


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def run_variant(raw_path: Path, options: dict, min_delta: int, mad_k: float, gamma: float, tone_percentile: float) -> np.ndarray:
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
    raw_stage = raw_blc
    if options["dpc"]:
        detection = detect_defects(raw_stage, bayer_pattern, min_delta=min_delta, mad_k=mad_k)
        raw_stage = repair_defects(raw_stage, bayer_pattern, detection)
    if options["lsc"]:
        raw_stage, _ = apply_lsc(raw_stage, bayer_pattern, white_level=white_level)

    rgb = bilinear_demosaic(raw_stage, bayer_pattern)
    if options["awb"]:
        rgb = apply_awb(rgb, gray_world_gains(rgb), white_level=white_level)
    if options["ccm"]:
        rgb = apply_ccm(rgb, ccm, white_level=white_level)

    if options["tone"]:
        rgb_01 = reinhard_tone_map(rgb, percentile=tone_percentile)
    else:
        rgb_01 = normalize_by_percentile(rgb, percentile=tone_percentile)
    preview = to_uint8(apply_gamma(rgb_01, gamma=gamma))
    return apply_rawpy_orientation(preview, display_flip)


def load_reference(raw_path: Path, reference_dir: Path) -> np.ndarray | None:
    reference_path = reference_dir / f"{raw_path.stem}_rawpy_srgb.png"
    if not reference_path.exists():
        return None
    return iio.imread(reference_path)


def compute_metrics(candidate: np.ndarray, reference: np.ndarray) -> dict:
    cand = candidate.astype(np.float32) / 255.0
    ref = reference.astype(np.float32) / 255.0
    if cand.shape != ref.shape:
        min_h = min(cand.shape[0], ref.shape[0])
        min_w = min(cand.shape[1], ref.shape[1])
        cand = cand[:min_h, :min_w, :]
        ref = ref[:min_h, :min_w, :]
    return {
        "psnr": float(peak_signal_noise_ratio(ref, cand, data_range=1.0)),
        "ssim": float(structural_similarity(ref, cand, channel_axis=2, data_range=1.0)),
        "mean_abs_diff": float(np.mean(np.abs(ref - cand))),
    }


def save_grid(path: Path, title: str, panels: list[tuple[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(1, len(panels), figsize=(4.4 * len(panels), 4.0), constrained_layout=True)
    for ax, (panel_title, image) in zip(axes, panels):
        ax.imshow(image)
        ax.set_title(panel_title)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def evaluate_one(raw_path: Path, out_dir: Path, reference_dir: Path, min_delta: int, mad_k: float, gamma: float, tone_percentile: float) -> dict:
    reference = load_reference(raw_path, reference_dir)
    previews = {}
    metrics = {}
    for name, options in VARIANTS.items():
        preview = run_variant(raw_path, options, min_delta=min_delta, mad_k=mad_k, gamma=gamma, tone_percentile=tone_percentile)
        previews[name] = preview
        if reference is not None:
            metrics[name] = compute_metrics(preview, reference)

    panels = [(name, previews[name]) for name in ["full", "no_lsc", "no_awb", "no_ccm"]]
    if reference is not None:
        panels.append(("rawpy", reference))
    grid_path = out_dir / f"{raw_path.stem}_week5_ablation.png"
    save_grid(grid_path, raw_path.name, panels)

    return {"file": str(raw_path), "sample_id": sample_id(raw_path), "metrics": metrics, "ablation": str(grid_path)}


def rel(path: str, report_path: Path) -> str:
    return Path(os.path.relpath(path, report_path.parent)).as_posix()


def fmt(value: float) -> str:
    return f"{value:.4f}"


def summarize_variant(results: list[dict], variant: str, key: str) -> float:
    values = [result["metrics"][variant][key] for result in results if variant in result["metrics"]]
    return float(np.mean(values)) if values else float("nan")


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 5 IQA / 消融实验报告",
        "",
        "Week5 的目标不是证明学习版 pipeline 超过 rawpy，而是把“看起来差不多”变成可量化、可复盘的差异。这里用 rawpy 生成的 sRGB 图作为参考，计算 PSNR、SSIM 和平均绝对差，同时做模块消融。",
        "",
        "## 评价边界",
        "",
        "rawpy reference 不是唯一真值，它包含 LibRaw 的完整处理策略，和本项目的学习版模块并不等价。因此这些指标只用于观察趋势，不作为产品画质结论。真正的颜色评价还需要色卡、标准光源和 DeltaE。",
        "",
        "## 消融配置",
        "",
        "| 变体 | 含义 |",
        "|---|---|",
        "| full | BLC + DPC + LSC + Demosaic + AWB + CCM + Tone + Gamma |",
        "| no_lsc | 去掉 LSC，观察位置相关校正缺失的影响 |",
        "| no_dpc | 去掉 DPC，观察坏点是否扩散进 RGB |",
        "| no_awb | 去掉 AWB，观察全局色偏 |",
        "| no_ccm | 去掉 CCM，观察相机 RGB 与显示 RGB 的差异 |",
        "| gamma_only | 去掉 Reinhard tone，只做分位归一化 + Gamma |",
        "",
        "## 平均指标",
        "",
        "| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |",
        "|---|---:|---:|---:|",
    ]
    for variant in VARIANTS:
        lines.append(
            f"| {variant} | {fmt(summarize_variant(results, variant, 'psnr'))} | {fmt(summarize_variant(results, variant, 'ssim'))} | {fmt(summarize_variant(results, variant, 'mean_abs_diff'))} |"
        )

    lines.extend(["", "## 逐样张指标", ""])
    for result in results:
        lines.extend(
            [
                f"### {result['sample_id']}",
                "",
                "| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |",
                "|---|---:|---:|---:|",
            ]
        )
        for variant in VARIANTS:
            metric = result["metrics"].get(variant)
            if metric:
                lines.append(f"| {variant} | {fmt(metric['psnr'])} | {fmt(metric['ssim'])} | {fmt(metric['mean_abs_diff'])} |")
        lines.extend(["", f"![{result['sample_id']} ablation]({rel(result['ablation'], report_path)})", ""])

    lines.extend(
        [
            "## 本周结论",
            "",
            "1. 指标用于定位趋势，不等于主观画质最终答案。",
            "2. AWB/CCM 对颜色差异的影响通常比 DPC 更显眼，因为 DPC 主要处理稀疏坏点。",
            "3. LSC 没有标定图时只能作为学习实验，不能用指标好坏直接判断真实镜头校正是否正确。",
            "4. 下一步如果要做严肃色彩评价，应引入色卡 ROI、Lab 转换和 DeltaE，而不是只和 rawpy 全图像素对齐。",
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
    parser = argparse.ArgumentParser(description="Evaluate Week5 IQA metrics and ablation variants.")
    parser.add_argument("raw_paths", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report", type=Path, default=Path("reports/week5/iqa_ablation_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--gamma", type=float, default=2.2)
    parser.add_argument("--tone-percentile", type=float, default=99.5)
    args = parser.parse_intermixed_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_paths = expand_paths(args.raw_paths)
    results = [
        evaluate_one(raw_path, args.out_dir, args.reference_dir, args.min_delta, args.mad_k, args.gamma, args.tone_percentile)
        for raw_path in raw_paths
    ]
    (args.out_dir / "week5_iqa_ablation.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
