"""Gamma 校正实验脚本 —— 将线性 RGB 通过 Gamma 编码映射为适合显示的图像。

用法:
    python 11_apply_gamma.py <raw_path>... [--out-dir reports/figures] [--gamma 2.2]

功能:
    对 CCM 后的线性 RGB 应用 Gamma 编码（幂函数 1/2.2），
    生成 Linear display（线性直接显示）与 Gamma encoded 的对比图，
    并汇总为 Week 4 的 Gamma 学习报告。

Gamma 公式:
    rgb_gamma = rgb_linear ** (1 / gamma)

为什么需要 Gamma:
    - 人眼对亮度的感知是非线性的（暗部更敏感）
    - 显示设备的输入-输出响应近似为幂函数
    - Gamma 编码让有限的 8-bit 码值更高效地分配给人眼敏感的区域

算法流程:
    rgb_ccm -> percentile normalize -> gamma encode -> uint8 preview

输出:
    - {sample}_gamma_compare.png:  Linear display / Gamma encoded 并排对比
    - {sample}_gamma.json:         参数记录
    - reports/week4/gamma_report.md: 汇总 Markdown 报告
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from week4_common import build_week4_base, gamma_preview, linear_preview, rel, save_compare


def analyze_gamma(raw_path: Path, out_dir: Path, min_delta: int, mad_k: float, gamma: float, tone_percentile: float) -> dict:
    base = build_week4_base(raw_path, min_delta=min_delta, mad_k=mad_k)
    out_dir.mkdir(parents=True, exist_ok=True)

    linear = linear_preview(base["rgb_ccm"], tone_percentile, base["display_flip"])
    encoded = gamma_preview(base["rgb_ccm"], tone_percentile, gamma, base["display_flip"])
    gamma_compare = out_dir / f"{raw_path.stem}_gamma_compare.png"

    save_compare(gamma_compare, raw_path.name, [("Linear display", linear), (f"Gamma 1/{gamma:.1f}", encoded)])

    result = {
        "file": str(raw_path),
        "sample_id": base["sample_id"],
        "gamma": gamma,
        "tone_percentile": tone_percentile,
        "gamma_compare": str(gamma_compare),
    }
    (out_dir / f"{raw_path.stem}_gamma.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def write_gamma_report(results: list[dict], report_path: Path) -> None:
    gamma_value = results[0]["gamma"] if results else 2.2
    lines = [
        "# Week 4-2 Gamma 学习报告",
        "",
        "Gamma 是把线性 RGB 映射到更适合显示和人眼感知的非线性 RGB。线性图直接显示通常会显得偏暗，因为显示编码和人眼感知都不是简单的线性关系。",
        "",
        "## 什么是线性 RGB",
        "",
        "线性 RGB 的意思是：数值和真实光强成正比。假设一个像素的线性值是 `0.2`，另一个是 `0.4`，后者代表的光强大约是前者的两倍。Demosaic、AWB、CCM 这类算法都应该尽量在线性空间里做。",
        "",
        "## 什么是 linear display",
        "",
        "`Linear display` 不是新的 ISP 算法，它只是为了对比，把线性 RGB 归一化到 `0..1` 后直接保存成图片：",
        "",
        "```text",
        "rgb_display = clip(rgb_linear / display_white, 0, 1)",
        "```",
        "",
        "普通图片和显示链路通常默认输入已经是类似 sRGB/gamma 编码后的值。如果把线性值直接当显示值，中间调会偏暗。",
        "",
        "举例：线性值 `0.25` 做 gamma 后会变成：",
        "",
        "```text",
        "0.25 ** (1 / 2.2) = 0.533",
        "```",
        "",
        "所以你看到暗部和中间调被抬起来，本质是同一批线性数值换了一种更适合显示的编码方式，不是曝光被改了。",
        "",
        "## 数学形式",
        "",
        "```text",
        "rgb_gamma = rgb_linear ** (1 / gamma)",
        f"gamma = {gamma_value}",
        "```",
        "",
        "对 `0..1` 之间的数做 `1/2.2` 幂，会让中低亮度值变大：",
        "",
        "```text",
        "x = 0.10 -> x ** (1/2.2) = 0.351",
        "x = 0.25 -> x ** (1/2.2) = 0.533",
        "x = 0.50 -> x ** (1/2.2) = 0.730",
        "x = 1.00 -> x ** (1/2.2) = 1.000",
        "```",
        "",
        "## 本脚本做了什么",
        "",
        "```text",
        "rgb_ccm -> percentile normalize -> gamma encode -> uint8 preview",
        "```",
        "",
        "这里使用的是简化 gamma。严格的 sRGB OETF 在暗部有线性分段，不完全等于单纯 `1/2.2` 幂函数。",
        "",
        "## Gamma 前后对比",
        "",
        "左边是线性 RGB 直接显示，右边是加 gamma 后。重点看中间调和暗部是不是被抬起来。",
        "",
    ]
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} gamma compare]({rel(result['gamma_compare'], report_path)})", ""])

    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. Gamma 不是白平衡，也不是颜色校正，它主要改变亮度编码方式。",
            "2. Gamma 通常放在接近显示输出的位置。",
            "3. Gamma 不等于 Tone Mapping。Gamma 主要解决显示编码和感知亮度，Tone Mapping 主要解决动态范围压缩。",
            "4. 看到 linear display 偏暗不是算法错了，而是线性数据还没有进入适合显示的编码状态。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Week4 gamma encoding and write the gamma report.")
    parser.add_argument("raw_paths", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--report-path", type=Path, default=Path("reports/week4/gamma_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--gamma", type=float, default=2.2)
    parser.add_argument("--tone-percentile", type=float, default=99.5)
    args = parser.parse_intermixed_args()

    results = [analyze_gamma(raw_path, args.out_dir, args.min_delta, args.mad_k, args.gamma, args.tone_percentile) for raw_path in args.raw_paths]
    write_gamma_report(results, args.report_path)
    print(args.report_path)


if __name__ == "__main__":
    main()
