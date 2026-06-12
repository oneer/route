#!/usr/bin/env python3
"""Export a compact Stage 2 leaderboard from generated metric summaries."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Stage 2 final summary table and figure.")
    parser.add_argument(
        "--metric-csvs",
        nargs="+",
        default=[
            "ai_isp_stage2/reports/figures/week4_sidd_tiny_standard_eval/metrics_summary.csv",
            "ai_isp_stage2/reports/figures/week7_low_light_eval/metrics_summary.csv",
        ],
    )
    parser.add_argument("--output-dir", default="ai_isp_stage2/reports/figures/week9_stage2_summary")
    parser.add_argument("--report-md", default="ai_isp_stage2/reports/week9_stage2_project_summary.md")
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
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


def read_rows(paths: list[str]) -> list[dict[str, str]]:
    rows = []
    for path_text in paths:
        path = Path(path_text)
        if not path.exists():
            continue
        task = path.parent.name
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                row = dict(row)
                row["task"] = task
                rows.append(row)
    return rows


TASK_LABELS = {
    "week4_sidd_tiny_standard_eval": "SIDD tiny denoise",
    "week7_low_light_eval": "Synthetic low-light",
}


RUN_LABELS = {
    "paired_rgb_sidd_tiny_dncnn_l2_2000": "DnCNN residual, L2, 2000 steps",
    "paired_rgb_sidd_tiny_unet_l1_1000": "UNet, L1, 1000 steps",
    "paired_rgb_sidd_tiny_nafnet_lite_l1_1000": "NAFNet-lite, L1, 1000 steps",
    "low_light_sidd_tiny_unet_l1_300": "Low-light UNet, L1, 300 steps",
}


def task_label(task: str) -> str:
    return TASK_LABELS.get(task, task)


def run_label(run: str) -> str:
    return RUN_LABELS.get(run, run)


def best_row_for_task(rows: list[dict[str, str]], task: str) -> dict[str, str] | None:
    task_rows = [row for row in rows if row["task"] == task]
    if not task_rows:
        return None
    return max(task_rows, key=lambda row: float(row["best_psnr"]))


def write_markdown_report(rows: list[dict[str, str]], report_path: Path, leaderboard_csv: Path) -> None:
    denoise_best = best_row_for_task(rows, "week4_sidd_tiny_standard_eval")
    low_light_best = best_row_for_task(rows, "week7_low_light_eval")

    lines = [
        "# Week 9：阶段二项目总结、简历和面试表达",
        "",
        "Week9 的目标是把阶段二收束成一个完整项目报告 v1。它不是继续追一个更复杂的模型，而是把前面 0-8 周留下的训练闭环、数据证据、模型对比、可视化诊断和面试表达整理成能复述、能复现、能继续迭代的项目。",
        "",
        "## 1. 本周成功标准",
        "",
        "| 成功标准 | Week9 对应产物 |",
        "|---|---|",
        "| 能把阶段二讲成项目，而不是周报流水账 | 本报告的任务定义、证据链、简历版本和面试问答 |",
        "| 能用同一张表解释主要实验 | `reports/figures/week9_stage2_summary/stage2_leaderboard.csv` |",
        "| 能用可视化支撑结论 | `reports/figures/week9_stage2_summary/stage2_leaderboard.png` |",
        "| 能明确下一步工程化方向 | 报告中的 Week10-12 衔接计划 |",
        "",
        "## 2. 运行命令",
        "",
        "```bash",
        "python ai_isp_stage2/scripts/11_export_stage2_summary.py --metric-csvs ai_isp_stage2/reports/figures/week4_sidd_tiny_standard_eval/metrics_summary.csv ai_isp_stage2/reports/figures/week7_low_light_eval/metrics_summary.csv --output-dir ai_isp_stage2/reports/figures/week9_stage2_summary --report-md ai_isp_stage2/reports/week9_stage2_project_summary.md",
        "```",
        "",
        "脚本会读取 Week4 的 SIDD tiny 标准评估和 Week7 的 low-light 评估结果，重新生成 leaderboard CSV、leaderboard PNG 和本学习报告。",
        "",
        "## 3. 阶段二总榜",
        "",
        "![Stage2 leaderboard](figures/week9_stage2_summary/stage2_leaderboard.png)",
        "",
        f"CSV 结果：`{leaderboard_csv.as_posix()}`",
        "",
        "| Task | Run | Best PSNR | Best SSIM | Best Step |",
        "|---|---|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    task_label(row["task"]),
                    run_label(row["run"]),
                    row["best_psnr"],
                    row["best_ssim"],
                    row["best_psnr_step"],
                ]
            )
            + " |"
        )

    lines += [
        "",
        "## 4. 从结果学到什么",
        "",
    ]
    if denoise_best:
        lines += [
            f"- SIDD tiny 去噪当前最强的是 `{run_label(denoise_best['run'])}`：PSNR `{float(denoise_best['best_psnr']):.4f}`，SSIM `{float(denoise_best['best_ssim']):.5f}`。这说明在小规模 paired RGB 去噪里，先建立强 residual baseline 很重要。",
        ]
    if low_light_best:
        lines += [
            f"- Low-light UNet 达到 PSNR `{float(low_light_best['best_psnr']):.4f}`，SSIM `{float(low_light_best['best_ssim']):.5f}`。它不能和普通去噪直接横向比较，因为任务同时包含增亮、去噪和颜色恢复。",
        ]

    lines += [
        "- UNet 的 SSIM 接近 DnCNN，但 PSNR 明显更低，说明结构相似和像素误差关注点不同；看指标时必须结合三联图、error map 和局部 crop。",
        "- NAFNet-lite 标准版明显优于短训版，说明现代 restoration block 需要足够训练步数和合适配置，不能用短训 smoke 结果做最终判断。",
        "- Week6 的 pseudo RAW bridge 不是模型成绩，而是用来理解 Bayer、RAW pack、demosaic 和 RGB 去噪之间的输入域差异。",
        "",
        "## 5. 阶段二能力证据链",
        "",
        "| 能力 | 证据 | 你应该能讲清什么 |",
        "|---|---|---|",
        "| 训练闭环 | Week0-1 toy RGB、TinyCNN/DnCNN 训练输出 | data -> model -> loss -> metric -> checkpoint -> visualization 的顺序 |",
        "| 真实 paired 数据 | Week2 SIDD tiny 数据检查图和 dataset card | noisy/clean 为什么必须像素对齐，input baseline 为什么必要 |",
        "| RGB restoration baseline | Week3-5 DnCNN/UNet/NAFNet-lite 对比 | residual denoise、UNet skip、NAFBlock-lite 的任务假设和代价 |",
        "| 评估诊断 | Week4 metrics、triplet、error map | 为什么 PSNR/SSIM 不能替代视觉诊断 |",
        "| RAW/ISP 过渡 | Week6 pseudo Bayer、RAW pack、demosaic | RAW pack 为什么是 4 通道，和 sRGB 输入有什么差异 |",
        "| 低光增强 | Week7 synthetic low-light 实验 | 低光增强为什么不只是去噪，还包含亮度和颜色恢复 |",
        "| Failure case | Week8 crop sheet 和 crop MAE | 如何从失败区域反推数据、loss、模型或训练策略问题 |",
        "",
        "## 6. 简历表达",
        "",
        "简洁版：",
        "",
        "```text",
        "基于 PyTorch 搭建 AI-ISP 图像恢复实验闭环，完成 SIDD paired RGB 去噪、低光增强、NAFNet-lite 复现和评估可视化；实现 PSNR/SSIM、三联图、error map、局部 failure crop 分析，在 SIDD tiny 上 DnCNN residual baseline 达到 35.54 dB PSNR / 0.8837 SSIM。",
        "```",
        "",
        "详细版：",
        "",
        "```text",
        "构建 AI-ISP Stage2 学习项目：从 toy RGB denoise 到真实 SIDD Small sRGB paired 数据，编写数据整理、baseline 测量、模型训练、评估汇总和 failure case 分析脚本；对比 DnCNN residual、UNet、NAFNet-lite，并扩展 synthetic low-light enhancement 实验。形成可复现周报、结果图和面试问答，能够解释 residual denoise、RAW pack、PSNR/SSIM 差异和现代恢复模型训练不足问题。",
        "```",
        "",
        "## 7. 面试讲述框架",
        "",
        "```text",
        "1. 我先用 toy RGB 去噪跑通训练闭环，确认 Dataset、Model、Loss、Metric、Checkpoint 都能工作；",
        "2. 然后整理 SIDD Small sRGB 成 paired train/val，并先测 noisy input baseline；",
        "3. 用 DnCNN residual 建立强 baseline，再对比 UNet 和 NAFNet-lite；",
        "4. 用 PSNR/SSIM、三联图、error map 和局部 crop 共同判断结果；",
        "5. 通过 pseudo RAW bridge 理解 Bayer/RAW pack，再做 synthetic low-light 连接到 AI-ISP 场景；",
        "6. 最后把 failure case 分类，决定下一步是扩数据、改 loss、改模型还是做部署验证。",
        "```",
        "",
        "## 8. 高频问答",
        "",
        "**Q1：这个项目和普通图像去噪 demo 有什么区别？**",
        "",
        "普通 demo 往往只跑一个模型。这里建立的是完整闭环：真实 paired 数据整理、baseline 测量、多模型对比、指标曲线、三联图、error map、failure crop、周报分析和面试复述。",
        "",
        "**Q2：为什么 DnCNN 这么简单反而最好？**",
        "",
        "当前任务是 SIDD tiny RGB 去噪，输入和 clean 主体内容高度一致，差异主要是噪声。DnCNN residual 直接预测噪声，再从输入中减去，非常贴合任务。复杂模型在小数据、短训练或配置不够稳定时，不一定马上超过它。",
        "",
        "**Q3：NAFNet-lite 的价值是什么？**",
        "",
        "它把项目从基础 CNN baseline 带到现代 restoration block。短训版不能代表最终能力，标准版结果说明结构可以学习，但需要足够训练步数、数据规模和调参。",
        "",
        "**Q4：为什么 low-light 不能和 SIDD denoise 直接比 PSNR？**",
        "",
        "两个任务输入输出难度不同。SIDD denoise 主要恢复噪声，low-light 同时要恢复亮度、颜色和噪声，所以 PSNR 的绝对值不能直接横向比较，只能在同一任务内比较。",
        "",
        "**Q5：看到 failure case 后下一步怎么做？**",
        "",
        "先分类错误。如果是暗部噪声残留，优先扩低光样本或调整噪声建模；如果是过平滑，考虑 loss 或模型容量；如果是偏色，检查颜色空间和数据；如果是边缘伪影，看 crop 策略、模型结构和局部 loss。",
        "",
        "## 9. Week10-12 衔接",
        "",
        "Week9 之后不要急着换大模型。更合理的路线是：Week10 汇总参数量、checkpoint 大小和可部署性；Week11 导出 ONNX 并做 PyTorch/ONNX 输出对齐；Week12 做 C++ OpenCV DNN smoke test 和 CPU latency 记录。这样阶段二才能自然衔接到阶段三工程化。",
        "",
        "## 10. 自检问题",
        "",
        "1. noisy、clean、output、loss、metric 的关系是什么？",
        "2. 为什么 paired 数据必须像素对齐？",
        "3. DnCNN residual 为什么适合去噪？",
        "4. UNet 为什么 SSIM 高但 PSNR 可能低？",
        "5. RAW pack 为什么是 4 通道？",
        "6. low-light enhancement 为什么不只是 denoise？",
        "7. error map 和 failure crop 分别能定位什么？",
        "8. 如何把这个项目讲成一个完整 AI-ISP restoration baseline？",
        "",
    ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.metric_csvs)
    if not rows:
        raise ValueError("No metric rows found.")

    out_csv = output_dir / "stage2_leaderboard.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["task", "run", "best_psnr", "best_ssim", "best_psnr_step", "best_ssim_step"])
        for row in rows:
            writer.writerow(
                [
                    row["task"],
                    row["run"],
                    row["best_psnr"],
                    row["best_ssim"],
                    row["best_psnr_step"],
                    row["best_ssim_step"],
                ]
            )

    width = 1500
    row_h = 48
    header_h = 86
    image = Image.new("RGB", (width, header_h + row_h * (len(rows) + 1)), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.text((36, 28), "Stage 2 Final Leaderboard", fill=(30, 42, 55), font=font(30, True))
    columns = [("Task", 36), ("Run", 310), ("Best PSNR", 900), ("Best SSIM", 1080), ("Step", 1260)]
    y = header_h
    draw.rectangle([24, y, width - 24, y + row_h], fill=(226, 232, 240))
    for label, x in columns:
        draw.text((x, y + 13), label, fill=(30, 42, 55), font=font(16, True))
    for idx, row in enumerate(rows, start=1):
        y = header_h + idx * row_h
        fill = (255, 255, 255) if idx % 2 else (242, 246, 250)
        draw.rectangle([24, y, width - 24, y + row_h], fill=fill)
        draw.text((36, y + 13), row["task"], fill=(30, 42, 55), font=font(15))
        draw.text((310, y + 13), row["run"], fill=(30, 42, 55), font=font(15))
        draw.text((900, y + 13), row["best_psnr"], fill=(30, 42, 55), font=font(15, True))
        draw.text((1080, y + 13), row["best_ssim"], fill=(30, 42, 55), font=font(15, True))
        draw.text((1260, y + 13), f"{row['best_psnr_step']} / {row['best_ssim_step']}", fill=(30, 42, 55), font=font(15))

    out_png = output_dir / "stage2_leaderboard.png"
    image.save(out_png)
    write_markdown_report(rows, Path(args.report_md), out_csv)
    print(f"wrote {out_csv}")
    print(f"wrote {out_png}")
    print(f"wrote {args.report_md}")


if __name__ == "__main__":
    main()
