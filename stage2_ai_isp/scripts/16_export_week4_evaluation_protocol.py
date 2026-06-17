#!/usr/bin/env python3
"""Export Week 4 evaluation protocol summaries from metrics_summary.csv files."""

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
        return abs(self.psnr_rank - self.ssim_rank)

    @property
    def metric_note(self) -> str:
        if self.rank_gap >= 2:
            return "PSNR/SSIM disagree; inspect triplet and error map"
        if self.best_psnr_step != self.best_ssim_step:
            return "Best PSNR and best SSIM occur at different steps"
        return "PSNR/SSIM broadly aligned"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Week 4 evaluation protocol summary.")
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week4_evaluation_protocol")
    parser.add_argument("--input-psnr", type=float, default=26.7302)
    parser.add_argument("--input-ssim", type=float, default=0.52412)
    return parser.parse_args()


def read_eval(eval_name: str, path: Path, input_psnr: float, input_ssim: float) -> list[EvalRow]:
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
