"""Summarize denoise runs and generate report figures.

This script is intentionally lightweight: it only depends on the standard
library plus Pillow, so it can run in the same minimal environment as the
training code.
"""
# 中文说明：汇总多个训练 run 的曲线、图片和误差图，形成对比报告。

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


@dataclass
class MetricRow:
    """中文说明：单行指标记录的数据结构，便于后续排序、绘图和导出。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    step: int
    train_loss: float
    val_psnr: float
    val_ssim: float


@dataclass
class RunSummary:
    """中文说明：单次训练运行的摘要结构，聚合最佳指标、最终指标和可视化路径。
    
    这个类把同一职责的数据和方法放在一起，方便训练、评估或报告脚本复用。
    """
    name: str
    path: Path
    rows: list[MetricRow]
    best_psnr: MetricRow
    best_ssim: MetricRow
    last: MetricRow


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", required=True, help="Run directories to summarize.")
    parser.add_argument(
        "--output-dir",
        default="stage2_ai_isp/reports/figures/week4_eval",
        help="Directory for generated figures and CSV summary.",
    )
    parser.add_argument(
        "--report-md",
        default="stage2_ai_isp/reports/week4_experiment_results.md",
        help="Markdown report path.",
    )
    parser.add_argument("--title", default="Week 4 Evaluation Summary")
    return parser.parse_args()


def read_metrics(path: Path) -> list[MetricRow]:
    """中文说明：读取训练过程记录的 metrics.csv，并转换成后续汇总需要的数据结构。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    metrics_path = path / "metrics.csv"
    if not metrics_path.exists():
        raise FileNotFoundError(metrics_path)

    rows: list[MetricRow] = []
    with metrics_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                MetricRow(
                    step=int(float(row["step"])),
                    train_loss=float(row["train_loss"]),
                    val_psnr=float(row["val_psnr"]),
                    val_ssim=float(row["val_ssim"]),
                )
            )
    if not rows:
        raise ValueError(f"No metric rows in {metrics_path}")
    return rows


def summarize_run(path: Path) -> RunSummary:
    """中文说明：读取单次实验的曲线、checkpoint 和可视化资产，形成统一摘要。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    rows = read_metrics(path)
    return RunSummary(
        name=path.name,
        path=path,
        rows=rows,
        best_psnr=max(rows, key=lambda r: r.val_psnr),
        best_ssim=max(rows, key=lambda r: r.val_ssim),
        last=rows[-1],
    )


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """中文说明：选择绘图可用字体；找不到指定字体时回退到默认字体。
    
    输入：size、bold。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_summary_csv(summaries: list[RunSummary], output_dir: Path) -> Path:
    """中文说明：将当前脚本整理出的结果写入磁盘，作为阶段产物或报告素材。
    
    输入：summaries、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    path = output_dir / "metrics_summary.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "run",
                "best_psnr",
                "best_psnr_step",
                "best_ssim",
                "best_ssim_step",
                "last_psnr",
                "last_ssim",
                "last_step",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary.name,
                    f"{summary.best_psnr.val_psnr:.4f}",
                    summary.best_psnr.step,
                    f"{summary.best_ssim.val_ssim:.5f}",
                    summary.best_ssim.step,
                    f"{summary.last.val_psnr:.4f}",
                    f"{summary.last.val_ssim:.5f}",
                    summary.last.step,
                ]
            )
    return path


def scale(value: float, min_value: float, max_value: float, low: int, high: int) -> int:
    """中文说明：实现 `scale` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：value、min_value、max_value、low、high。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    if max_value <= min_value:
        return (low + high) // 2
    t = (value - min_value) / (max_value - min_value)
    return int(low + t * (high - low))


def draw_metric_plot(summaries: list[RunSummary], output_dir: Path) -> Path:
    """中文说明：实现 `draw_metric_plot` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：summaries、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    path = output_dir / "metrics_plot.png"
    width, height = 1680, 900
    margin_left, margin_right = 95, 430
    title_h = 74
    gap = 56
    plot_h = 280
    plot_w = width - margin_left - margin_right
    psnr_top = title_h
    ssim_top = title_h + plot_h + gap

    all_steps = [row.step for s in summaries for row in s.rows]
    all_psnr = [row.val_psnr for s in summaries for row in s.rows]
    all_ssim = [row.val_ssim for s in summaries for row in s.rows]
    x_min, x_max = min(all_steps), max(all_steps)
    psnr_min, psnr_max = min(all_psnr), max(all_psnr)
    ssim_min, ssim_max = min(all_ssim), max(all_ssim)

    image = Image.new("RGB", (width, height), (250, 252, 253))
    draw = ImageDraw.Draw(image)
    draw.text((40, 24), "Validation Metrics Across Runs", fill=(30, 42, 55), font=font(30, True))

    colors = [
        (66, 133, 244),
        (52, 168, 83),
        (251, 188, 5),
        (234, 67, 53),
        (124, 77, 255),
        (0, 150, 136),
    ]

    def draw_panel(top: int, title: str, min_value: float, max_value: float) -> None:
        """中文说明：实现 `draw_panel` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：top、title、min_value、max_value。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        draw.rectangle(
            [margin_left, top, margin_left + plot_w, top + plot_h],
            outline=(200, 210, 220),
            width=2,
            fill=(255, 255, 255),
        )
        draw.text((margin_left, top - 30), title, fill=(30, 42, 55), font=font(20, True))
        draw.text(
            (margin_left + plot_w - 170, top - 28),
            f"{min_value:.4f} .. {max_value:.4f}",
            fill=(84, 99, 116),
            font=font(15),
        )
        for i in range(5):
            y = top + 24 + i * (plot_h - 48) // 4
            draw.line([margin_left, y, margin_left + plot_w, y], fill=(235, 239, 243), width=1)
        draw.text((margin_left, top + plot_h + 12), f"step: {x_min} .. {x_max}", fill=(84, 99, 116), font=font(15))

    def xy(step: int, value: float, values_min: float, values_max: float, top: int) -> tuple[int, int]:
        """中文说明：实现 `xy` 这一步的核心逻辑，供本文件的主流程复用。
        
        输入：step、value、values_min、values_max、top。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        x = scale(step, x_min, x_max, margin_left + 20, margin_left + plot_w - 20)
        y = scale(value, values_min, values_max, top + plot_h - 30, top + 30)
        return x, y

    draw_panel(psnr_top, "PSNR: pixel error view", psnr_min, psnr_max)
    draw_panel(ssim_top, "SSIM: structure similarity view", ssim_min, ssim_max)

    for idx, summary in enumerate(summaries):
        color = colors[idx % len(colors)]
        psnr_points = [xy(row.step, row.val_psnr, psnr_min, psnr_max, psnr_top) for row in summary.rows]
        ssim_points = [xy(row.step, row.val_ssim, ssim_min, ssim_max, ssim_top) for row in summary.rows]
        for points in (psnr_points, ssim_points):
            if len(points) > 1:
                draw.line(points, fill=color, width=4)
            for point in points:
                draw.ellipse([point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4], fill=color)

        legend_x = margin_left + plot_w + 28
        legend_y = psnr_top + 16 + idx * 74
        draw.rectangle([legend_x, legend_y + 5, legend_x + 20, legend_y + 25], fill=color)
        draw.text((legend_x + 30, legend_y), summary.name, fill=(30, 42, 55), font=font(15, True))
        draw.text(
            (legend_x + 30, legend_y + 24),
            f"best PSNR {summary.best_psnr.val_psnr:.2f} @ {summary.best_psnr.step}",
            fill=(84, 99, 116),
            font=font(14),
        )
        draw.text(
            (legend_x + 30, legend_y + 44),
            f"best SSIM {summary.best_ssim.val_ssim:.4f} @ {summary.best_ssim.step}",
            fill=(84, 99, 116),
            font=font(14),
        )

    image.save(path)
    return path


def pick_vis_images(run: Path) -> list[Path]:
    """中文说明：实现 `pick_vis_images` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：run。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    vis_dir = run / "vis"
    if not vis_dir.exists():
        return []
    images = sorted(vis_dir.glob("step_*.png"))
    if len(images) <= 3:
        return images
    return [images[0], images[len(images) // 2], images[-1]]


def make_contact_sheet(summaries: list[RunSummary], output_dir: Path) -> Path | None:
    """中文说明：构造后续流程需要的对象或可视化产物，把零散配置集中成可复用结果。
    
    输入：summaries、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    selected: list[tuple[str, Path]] = []
    for summary in summaries:
        for image_path in pick_vis_images(summary.path):
            selected.append((summary.name, image_path))
    if not selected:
        return None

    thumb_w = 420
    label_h = 44
    thumbs: list[tuple[str, Image.Image]] = []
    for run_name, image_path in selected:
        image = Image.open(image_path).convert("RGB")
        ratio = thumb_w / image.width
        thumb_h = int(image.height * ratio)
        image = image.resize((thumb_w, thumb_h), Image.BICUBIC)
        thumbs.append((f"{run_name} / {image_path.name}", image))

    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    cell_h = max(image.height for _, image in thumbs) + label_h
    sheet = Image.new("RGB", (cols * thumb_w, rows * cell_h), (250, 252, 253))
    draw = ImageDraw.Draw(sheet)
    for idx, (label, image) in enumerate(thumbs):
        x = (idx % cols) * thumb_w
        y = (idx // cols) * cell_h
        draw.text((x + 12, y + 10), label, fill=(30, 42, 55), font=font(16, True))
        sheet.paste(image, (x, y + label_h))

    path = output_dir / "triplet_contact_sheet.png"
    sheet.save(path)
    return path


def make_error_maps(summaries: list[RunSummary], output_dir: Path) -> list[Path]:
    """中文说明：构造后续流程需要的对象或可视化产物，把零散配置集中成可复用结果。
    
    输入：summaries、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    paths: list[Path] = []
    error_dir = output_dir / "error_maps"
    error_dir.mkdir(parents=True, exist_ok=True)
    for summary in summaries:
        images = pick_vis_images(summary.path)
        if not images:
            continue
        source = images[-1]
        triplet = Image.open(source).convert("RGB")
        panel_w = triplet.width // 3
        output = triplet.crop((panel_w, 0, panel_w * 2, triplet.height))
        clean = triplet.crop((panel_w * 2, 0, panel_w * 3, triplet.height))
        out_px = output.load()
        clean_px = clean.load()
        err = Image.new("RGB", output.size)
        err_px = err.load()
        for y in range(output.height):
            for x in range(output.width):
                o = out_px[x, y]
                c = clean_px[x, y]
                diff = max(abs(o[0] - c[0]), abs(o[1] - c[1]), abs(o[2] - c[2]))
                v = min(255, diff * 6)
                err_px[x, y] = (v, v, v)
        path = error_dir / f"{summary.name}_{source.stem}_error_x6.png"
        err.save(path)
        paths.append(path)
    return paths


def rel(path: Path, base: Path) -> str:
    """中文说明：实现 `rel` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：path、base。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def write_markdown(
    summaries: list[RunSummary],
    output_dir: Path,
    report_path: Path,
    metric_plot: Path,
    contact_sheet: Path | None,
    error_maps: list[Path],
    title: str,
) -> None:
    """中文说明：把汇总结果写成 Markdown，便于直接放入阶段文档。
    
    输入：summaries、output_dir、report_path、metric_plot、contact_sheet、error_maps、title。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    base = report_path.parent
    lines = [
        f"# {title}",
        "",
        "This report was generated by `scripts/05_evaluate_runs.py`.",
        "",
        "## Metric Summary",
        "",
        "| Run | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | Last PSNR | Last SSIM |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        lines.append(
            "| "
            + " | ".join(
                [
                    summary.name,
                    f"{summary.best_psnr.val_psnr:.4f}",
                    str(summary.best_psnr.step),
                    f"{summary.best_ssim.val_ssim:.5f}",
                    str(summary.best_ssim.step),
                    f"{summary.last.val_psnr:.4f}",
                    f"{summary.last.val_ssim:.5f}",
                ]
            )
            + " |"
        )

    lines += [
        "",
        "## Metric Plot",
        "",
        f"![metrics]({rel(metric_plot, base)})",
        "",
    ]
    if contact_sheet is not None:
        lines += [
            "## Triplet Contact Sheet",
            "",
            f"![triplets]({rel(contact_sheet, base)})",
            "",
        ]
    if error_maps:
        lines += ["## Error Maps", ""]
        for path in error_maps:
            lines.append(f"![{path.stem}]({rel(path, base)})")
        lines.append("")

    lines += [
        "## Learner Analysis Required",
        "",
        "- Write one visual conclusion supported by a triplet or error map.",
        "- Identify at least one failure case without inferring it only from the run name.",
        "- Propose one single-variable next experiment and its acceptance criterion.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = [summarize_run(Path(run)) for run in args.runs]
    write_summary_csv(summaries, output_dir)
    metric_plot = draw_metric_plot(summaries, output_dir)
    contact_sheet = make_contact_sheet(summaries, output_dir)
    error_maps = make_error_maps(summaries, output_dir)
    write_markdown(
        summaries=summaries,
        output_dir=output_dir,
        report_path=Path(args.report_md),
        metric_plot=metric_plot,
        contact_sheet=contact_sheet,
        error_maps=error_maps,
        title=args.title,
    )
    print(f"wrote {output_dir}")
    print(f"wrote {args.report_md}")


if __name__ == "__main__":
    main()
