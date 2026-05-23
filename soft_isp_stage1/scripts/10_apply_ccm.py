from __future__ import annotations

import argparse
import json
from pathlib import Path

from week4_common import (
    build_week4_base,
    describe_rgb,
    fmt,
    gamma_preview,
    reference_panel,
    rel,
    rgb_mean,
    save_compare,
)


def analyze_ccm(raw_path: Path, out_dir: Path, reference_dir: Path, min_delta: int, mad_k: float, gamma: float, tone_percentile: float) -> dict:
    base = build_week4_base(raw_path, min_delta=min_delta, mad_k=mad_k)
    out_dir.mkdir(parents=True, exist_ok=True)

    awb_preview = gamma_preview(base["rgb_awb"], tone_percentile, gamma, base["display_flip"])
    ccm_preview = gamma_preview(base["rgb_ccm"], tone_percentile, gamma, base["display_flip"])
    reference = reference_panel(raw_path, reference_dir, ccm_preview)
    ccm_compare = out_dir / f"{raw_path.stem}_ccm_compare.png"

    save_compare(
        ccm_compare,
        raw_path.name,
        [("After AWB", awb_preview), ("After CCM", ccm_preview), ("rawpy reference", reference)],
    )

    result = {
        "file": str(raw_path),
        "sample_id": base["sample_id"],
        "bayer_pattern": base["bayer_pattern"],
        "black_level_per_channel": base["black_level_per_channel"],
        "white_level": base["white_level"],
        "awb_gains": base["awb_gains"],
        "ccm": base["ccm"].tolist(),
        "rgb_awb": describe_rgb(base["rgb_awb"]),
        "rgb_ccm": describe_rgb(base["rgb_ccm"]),
        "mean_awb_rgb": rgb_mean(base["rgb_awb"]),
        "mean_ccm_rgb": rgb_mean(base["rgb_ccm"]),
        "ccm_compare": str(ccm_compare),
    }
    (out_dir / f"{raw_path.stem}_ccm.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def write_ccm_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 4-1 CCM 学习报告",
        "",
        "CCM 的全称是 Color Correction Matrix，颜色校正矩阵。它接在 AWB 后面，用一个 `3x3` 矩阵把相机 RGB 映射到更接近目标颜色空间的 RGB。",
        "",
        "## CCM 解决什么问题",
        "",
        "AWB 只是在 R/G/B 三个通道上乘增益，让灰色或白色更接近中性。它不能处理颜色之间的串扰关系。相机传感器的 R/G/B 不是标准 sRGB 的 R/G/B，每个滤光片都会收到一部分其他波段的光，所以还需要 CCM 做通道混合。",
        "",
        "AWB 做的是：",
        "",
        "```text",
        "R_awb = R * gain_R",
        "G_awb = G * gain_G",
        "B_awb = B * gain_B",
        "```",
        "",
        "CCM 做的是：",
        "",
        "```text",
        "[R']   [m00 m01 m02] [R]",
        "[G'] = [m10 m11 m12] [G]",
        "[B']   [m20 m21 m22] [B]",
        "```",
        "",
        "展开第一行就是 `R' = m00 * R + m01 * G + m02 * B`。这说明输出 R 不只来自输入 R，也可以混入 G/B。这就是 CCM 能修正色偏、色相和饱和度关系的原因。",
        "",
        "## 本脚本做了什么",
        "",
        "```text",
        "RAW -> BLC -> DPC -> Demosaic -> AWB -> CCM -> 对比图",
        "```",
        "",
        "本周为了学习闭环，先使用 DNG/rawpy 暴露的 `color_matrix` 前三列作为学习用 CCM。它能帮助理解矩阵校色流程，但还不是完整产品 ISP 里的色卡拟合和标定流程。",
        "",
        "## 结果总表",
        "",
        "| 样张 | R gain | G gain | B gain | AWB mean RGB | CCM mean RGB | 观察 |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for result in results:
        gains = result["awb_gains"]
        awb_mean = "/".join(fmt(v) for v in result["mean_awb_rgb"])
        ccm_mean = "/".join(fmt(v) for v in result["mean_ccm_rgb"])
        lines.append(f"| {result['sample_id']} | {fmt(gains[0])} | {fmt(gains[1])} | {fmt(gains[2])} | {awb_mean} | {ccm_mean} | CCM 改变颜色通道混合关系 |")

    lines.extend(
        [
            "",
            "## CCM 前后对比",
            "",
            "左边是 AWB 后，右边是 CCM 后，第三张是 rawpy 参考。重点看灰白区域是否保持中性、典型颜色是否发生色相变化，以及 CCM 后是否出现明显过饱和或高光 clip。",
            "",
        ]
    )
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} CCM compare]({rel(result['ccm_compare'], report_path)})", ""])

    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. AWB 是三个通道的独立增益，CCM 是三个通道之间的线性混合。",
            "2. CCM 的输入仍然应该是线性 RGB，不应该先做 gamma。",
            "3. CCM 后可能出现负值或超过白电平的值，所以工程上要 clip 或配合后续 tone mapping。",
            "4. 产品中的 CCM 通常来自色卡标定，并可能按色温准备多套矩阵。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Week4 CCM and write the CCM report.")
    parser.add_argument("raw_paths", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report-path", type=Path, default=Path("reports/week4/ccm_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--gamma", type=float, default=2.2)
    parser.add_argument("--tone-percentile", type=float, default=99.5)
    args = parser.parse_intermixed_args()

    results = [
        analyze_ccm(raw_path, args.out_dir, args.reference_dir, args.min_delta, args.mad_k, args.gamma, args.tone_percentile)
        for raw_path in args.raw_paths
    ]
    write_ccm_report(results, args.report_path)
    print(args.report_path)


if __name__ == "__main__":
    main()
