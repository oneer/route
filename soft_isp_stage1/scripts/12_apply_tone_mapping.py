from __future__ import annotations

import argparse
import json
from pathlib import Path

from week4_common import build_week4_base, gamma_preview, reference_panel, reinhard_preview, rel, save_compare


def analyze_tone(raw_path: Path, out_dir: Path, reference_dir: Path, min_delta: int, mad_k: float, gamma: float, tone_percentile: float) -> dict:
    base = build_week4_base(raw_path, min_delta=min_delta, mad_k=mad_k)
    out_dir.mkdir(parents=True, exist_ok=True)

    percentile_preview = gamma_preview(base["rgb_ccm"], tone_percentile, gamma, base["display_flip"])
    reinhard = reinhard_preview(base["rgb_ccm"], tone_percentile, gamma, base["display_flip"])
    reference = reference_panel(raw_path, reference_dir, percentile_preview)
    tone_compare = out_dir / f"{raw_path.stem}_tone_mapping_compare.png"

    save_compare(
        tone_compare,
        raw_path.name,
        [(f"Percentile {tone_percentile:g}% + gamma", percentile_preview), ("Reinhard + gamma", reinhard), ("rawpy reference", reference)],
    )

    result = {
        "file": str(raw_path),
        "sample_id": base["sample_id"],
        "gamma": gamma,
        "tone_percentile": tone_percentile,
        "tone_compare": str(tone_compare),
    }
    (out_dir / f"{raw_path.stem}_tone_mapping.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def write_tone_report(results: list[dict], report_path: Path) -> None:
    percentile = results[0]["tone_percentile"] if results else 99.5
    lines = [
        "# Week 4-3 Tone Mapping 学习报告",
        "",
        "Tone Mapping 解决的是动态范围压缩问题。RAW/线性 RGB 里可能有很亮的高光，如果直接线性压到 `0..1`，暗部和中间调很容易被压得不好看。",
        "",
        "## 为什么需要动态范围压缩",
        "",
        "RAW 能记录的亮度范围通常比普通 `8-bit` 显示图更宽。如果为了保住高光，整体会被压暗；如果为了主体正常，高光又容易 clip 成一片白。Tone Mapping 的目标是在高光保护、中间调亮度、暗部可见性和整体对比之间折中。",
        "",
        "## 本脚本实现的两个简单版本",
        "",
        "第一种是 percentile clip：",
        "",
        "```text",
        f"display_white = percentile(rgb, {percentile})",
        "rgb_norm = clip(rgb / display_white, 0, 1)",
        "```",
        "",
        "`display_white` 是显示白点，不是传感器的 `white_level`。使用 `99.5%` 分位点表示允许最亮的 0.5% 像素被压到白色附近，避免极少数异常高光把整张图压暗。",
        "",
        "第二种是全局 Reinhard 曲线：",
        "",
        "```text",
        "rgb_tone = rgb_norm / (1 + rgb_norm)",
        "```",
        "",
        "Reinhard 的特点是输入越大，压缩越强：`0.25 -> 0.200`、`1.00 -> 0.500`、`4.00 -> 0.800`。它能柔和压高光，但整体可能变灰、对比度下降。",
        "",
        "## 本脚本做了什么",
        "",
        "```text",
        "方案 A: rgb_ccm -> percentile normalize -> gamma -> preview",
        "方案 B: rgb_ccm -> percentile normalize -> Reinhard -> gamma -> preview",
        "```",
        "",
        "Gamma 放在 tone mapping 后面，因为 tone mapping 的输入应尽量保持线性亮度关系。",
        "",
        "## Tone Mapping 对比",
        "",
        "左边是 percentile clip + gamma，中间是 Reinhard + gamma，右边是 rawpy 参考。重点看亮部压缩和整体观感的差异。",
        "",
    ]
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} tone compare]({rel(result['tone_compare'], report_path)})", ""])

    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. Tone Mapping 负责把线性高动态范围压到显示范围。",
            "2. percentile clip 简单直接，但可能丢高光层次。",
            "3. Reinhard 曲线会更柔和地压亮部，但整体可能偏灰或偏暗。",
            "4. Gamma 和 Tone Mapping 经常一起出现在显示输出阶段，但它们解决的问题不同。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Week4 tone mapping and write the tone mapping report.")
    parser.add_argument("raw_paths", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report-path", type=Path, default=Path("reports/week4/tone_mapping_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--gamma", type=float, default=2.2)
    parser.add_argument("--tone-percentile", type=float, default=99.5)
    args = parser.parse_intermixed_args()

    results = [
        analyze_tone(raw_path, args.out_dir, args.reference_dir, args.min_delta, args.mad_k, args.gamma, args.tone_percentile)
        for raw_path in args.raw_paths
    ]
    write_tone_report(results, args.report_path)
    print(args.report_path)


if __name__ == "__main__":
    main()
