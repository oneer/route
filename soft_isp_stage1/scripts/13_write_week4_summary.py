from __future__ import annotations

import argparse
import json
from pathlib import Path

from week4_common import build_week4_base, gamma_preview, reference_panel, rel, save_compare


def analyze_summary(raw_path: Path, out_dir: Path, reference_dir: Path, min_delta: int, mad_k: float, gamma: float, tone_percentile: float) -> dict:
    base = build_week4_base(raw_path, min_delta=min_delta, mad_k=mad_k)
    out_dir.mkdir(parents=True, exist_ok=True)

    awb_preview = gamma_preview(base["rgb_awb"], tone_percentile, gamma, base["display_flip"])
    ccm_preview = gamma_preview(base["rgb_ccm"], tone_percentile, gamma, base["display_flip"])
    tone_preview = ccm_preview
    reference = reference_panel(raw_path, reference_dir, tone_preview)
    pipeline_compare = out_dir / f"{raw_path.stem}_week4_pipeline_compare.png"

    save_compare(
        pipeline_compare,
        raw_path.name,
        [("AWB", awb_preview), ("CCM", ccm_preview), ("Tone + gamma", tone_preview), ("rawpy reference", reference)],
    )

    result = {"file": str(raw_path), "sample_id": base["sample_id"], "pipeline_compare": str(pipeline_compare)}
    (out_dir / f"{raw_path.stem}_week4_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def write_summary(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 4 总结：CCM / Gamma / Tone Mapping",
        "",
        "Week4 的目标是把 Week3 的 AWB 后 RGB 继续推向可显示图像。三个模块分开理解：CCM 负责颜色空间/颜色混合，Gamma 负责显示编码，Tone Mapping 负责动态范围压缩。",
        "",
        "如果只记一句话：Week3 得到的是“线性相机 RGB”，Week4 开始把它变成“更接近人眼和显示器能正常观看的图像”。",
        "",
        "## 本周流水线",
        "",
        "```text",
        "RAW -> BLC -> DPC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma -> Preview",
        "```",
        "",
        "## 分模块脚本",
        "",
        "- `scripts/10_apply_ccm.py`：只负责 CCM 对比图和 CCM 报告",
        "- `scripts/11_apply_gamma.py`：只负责 Gamma 对比图和 Gamma 报告",
        "- `scripts/12_apply_tone_mapping.py`：只负责 Tone Mapping 对比图和 Tone Mapping 报告",
        "- `scripts/13_write_week4_summary.py`：只负责 Week4 综合对比图和总结",
        "",
        "## 分模块报告",
        "",
        "- [CCM 报告](ccm_report.md)",
        "- [Gamma 报告](gamma_report.md)",
        "- [Tone Mapping 报告](tone_mapping_report.md)",
        "",
        "## 核心概念速查",
        "",
        "| 名词 | 简单理解 | 本周位置 |",
        "|---|---|---|",
        "| 线性 RGB | 数值和真实光强近似成正比 | Demosaic/AWB/CCM 的工作空间 |",
        "| Linear display | 把线性 RGB 直接当显示图看 | 只用于对比，不是最终输出 |",
        "| CCM | 用 `3x3` 矩阵混合 R/G/B，修正相机颜色空间 | AWB 之后 |",
        "| Tone Mapping | 把高动态范围压进显示范围 | CCM 之后、Gamma 之前 |",
        "| Gamma | 把线性亮度编码成更适合显示和视觉感知的非线性值 | 接近最终输出 |",
        "",
        "## 为什么顺序是 CCM -> Tone Mapping -> Gamma",
        "",
        "CCM 需要在线性 RGB 上做矩阵乘法，因为颜色混合默认基于线性光强。Tone Mapping 也最好在线性亮度上做，这样压高光、保中间调的曲线含义更清楚。Gamma 放在最后，是因为它主要是显示编码，不应该提前破坏前面算法需要的线性关系。",
        "",
        "## 综合对比图",
        "",
        "这组图从左到右是 AWB、CCM、Tone+Gamma、rawpy reference，用来快速观察 Week4 之后整体显示效果的变化。",
        "",
    ]
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} Week4 pipeline compare]({rel(result['pipeline_compare'], report_path)})", ""])

    lines.extend(
        [
            "## Week4 学习结论",
            "",
            "1. Demosaic 之后只是有了 RGB 结构，还不是最终显示图。",
            "2. AWB 让白点接近中性，CCM 进一步修正颜色关系。",
            "3. Gamma 会显著影响中间调亮度，所以不能把它和曝光、AWB 混在一起理解。",
            "4. Tone Mapping 是显示输出前非常关键的一步，决定亮部和暗部如何压缩。",
            "5. linear display 偏暗通常不是错，而是线性数据还没经过显示编码。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the Week4 summary report.")
    parser.add_argument("raw_paths", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report-path", type=Path, default=Path("reports/week4/summary.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--gamma", type=float, default=2.2)
    parser.add_argument("--tone-percentile", type=float, default=99.5)
    args = parser.parse_intermixed_args()

    results = [
        analyze_summary(raw_path, args.out_dir, args.reference_dir, args.min_delta, args.mad_k, args.gamma, args.tone_percentile)
        for raw_path in args.raw_paths
    ]
    write_summary(results, args.report_path)
    print(args.report_path)


if __name__ == "__main__":
    main()
