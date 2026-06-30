#!/usr/bin/env python3
"""Export Week 4 evaluation protocol summaries from metrics_summary.csv files."""
# 中文说明：导出 Week4 评估协议和测试结果表。

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


DEFAULT_EVALS = [
    (
        "short_300",
        "stage2_ai_isp/reports/figures/week4_sidd_tiny_eval/metrics_summary.csv",
    ),
    (
        "standard",
        "stage2_ai_isp/reports/figures/week4_sidd_tiny_standard_eval/metrics_summary.csv",
    ),
    (
        "ablation",
        "stage2_ai_isp/reports/figures/week4_sidd_tiny_ablation_eval/metrics_summary.csv",
    ),
]


@dataclass
class EvalRow:
    """中文说明：测试集评估结果的一行结构。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    eval_name: str
    run: str
    best_psnr: float
    best_psnr_step: int
    best_ssim: float
    best_ssim_step: int
    last_psnr: float
    last_ssim: float
    psnr_gain: float
    ssim_gain: float
    psnr_rank: int = 0
    ssim_rank: int = 0

    @property
    def rank_gap(self) -> int:
        """中文说明：实现 `rank_gap` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        return abs(self.psnr_rank - self.ssim_rank)

    @property
    def metric_note(self) -> str:
        """中文说明：实现 `metric_note` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：主要依赖当前对象状态或命令行参数。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        if self.rank_gap >= 2:
            return "PSNR/SSIM disagree; inspect triplet and error map"
        if self.best_psnr_step != self.best_ssim_step:
            return "Best PSNR and best SSIM occur at different steps"
        return "PSNR/SSIM broadly aligned"


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create Week 4 evaluation protocol summary.")
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week4_evaluation_protocol")
    parser.add_argument("--input-psnr", type=float, default=26.7302)
    parser.add_argument("--input-ssim", type=float, default=0.52412)
    return parser.parse_args()


def read_eval(eval_name: str, path: Path, input_psnr: float, input_ssim: float) -> list[EvalRow]:
    """中文说明：读取外部文件或模型状态，并转换成当前脚本后续步骤需要的格式。
    
    输入：eval_name、path、input_psnr、input_ssim。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    if not path.exists():
        return []
    rows: list[EvalRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            best_psnr = float(row["best_psnr"])
            best_ssim = float(row["best_ssim"])
            rows.append(
                EvalRow(
                    eval_name=eval_name,
                    run=row["run"],
                    best_psnr=best_psnr,
                    best_psnr_step=int(row["best_psnr_step"]),
                    best_ssim=best_ssim,
                    best_ssim_step=int(row["best_ssim_step"]),
                    last_psnr=float(row["last_psnr"]),
                    last_ssim=float(row["last_ssim"]),
                    psnr_gain=best_psnr - input_psnr,
                    ssim_gain=best_ssim - input_ssim,
                )
            )
    by_psnr = sorted(rows, key=lambda item: item.best_psnr, reverse=True)
    by_ssim = sorted(rows, key=lambda item: item.best_ssim, reverse=True)
    for rank, row in enumerate(by_psnr, start=1):
        row.psnr_rank = rank
    for rank, row in enumerate(by_ssim, start=1):
        row.ssim_rank = rank
    return rows


def write_csv(rows: list[EvalRow], output_dir: Path) -> Path:
    """中文说明：把汇总结果写成 CSV，便于表格查看和后续报告引用。
    
    输入：rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "week4_evaluation_protocol.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "eval",
                "run",
                "best_psnr",
                "best_psnr_step",
                "best_ssim",
                "best_ssim_step",
                "psnr_gain_vs_input",
                "ssim_gain_vs_input",
                "psnr_rank",
                "ssim_rank",
                "rank_gap",
                "metric_note",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.eval_name,
                    row.run,
                    f"{row.best_psnr:.4f}",
                    row.best_psnr_step,
                    f"{row.best_ssim:.5f}",
                    row.best_ssim_step,
                    f"{row.psnr_gain:.4f}",
                    f"{row.ssim_gain:.5f}",
                    row.psnr_rank,
                    row.ssim_rank,
                    row.rank_gap,
                    row.metric_note,
                ]
            )
    return path


def write_markdown(rows: list[EvalRow], output_dir: Path, input_psnr: float, input_ssim: float) -> Path:
    """中文说明：把汇总结果写成 Markdown，便于直接放入阶段文档。
    
    输入：rows、output_dir、input_psnr、input_ssim。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    path = output_dir / "week4_evaluation_protocol.md"
    lines = [
        "# Week 4 Evaluation Protocol Summary",
        "",
        f"Input noisy baseline: PSNR `{input_psnr:.4f}`, SSIM `{input_ssim:.5f}`.",
        "",
        "| Eval | Run | Best PSNR | Best SSIM | PSNR gain | SSIM gain | PSNR rank | SSIM rank | Note |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.eval_name,
                    row.run,
                    f"{row.best_psnr:.4f}@{row.best_psnr_step}",
                    f"{row.best_ssim:.5f}@{row.best_ssim_step}",
                    f"{row.psnr_gain:.4f}",
                    f"{row.ssim_gain:.5f}",
                    str(row.psnr_rank),
                    str(row.ssim_rank),
                    row.metric_note,
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## How To Use",
        "",
        "- If PSNR and SSIM ranks disagree, inspect the triplet contact sheet and error map before choosing a model.",
        "- If best PSNR and best SSIM occur at different steps, keep both metric rows in the report and avoid relying only on the last checkpoint.",
        "- A model must exceed the noisy input baseline before it can be considered useful.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    output_dir = Path(args.output_dir)
    rows: list[EvalRow] = []
    for eval_name, path in DEFAULT_EVALS:
        rows.extend(read_eval(eval_name, Path(path), args.input_psnr, args.input_ssim))
    csv_path = write_csv(rows, output_dir)
    md_path = write_markdown(rows, output_dir, args.input_psnr, args.input_ssim)
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    for row in rows:
        print(
            f"{row.eval_name}/{row.run}: psnr_rank={row.psnr_rank} "
            f"ssim_rank={row.ssim_rank} note={row.metric_note}"
        )


if __name__ == "__main__":
    main()
