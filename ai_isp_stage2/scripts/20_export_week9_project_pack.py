#!/usr/bin/env python3
"""Export a Week 9 project pack for resume and interview review."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Week 9 project-facing summary artifacts.")
    parser.add_argument(
        "--leaderboard",
        default="ai_isp_stage2/reports/figures/week9_stage2_summary/stage2_leaderboard.csv",
    )
    parser.add_argument(
        "--engineering",
        default="ai_isp_stage2/reports/figures/week10_engineering_summary/stage2_engineering_summary.csv",
    )
    parser.add_argument(
        "--failure-taxonomy",
        default="ai_isp_stage2/reports/figures/week8_failure_taxonomy/week8_failure_taxonomy.csv",
    )
    parser.add_argument("--output-dir", default="ai_isp_stage2/reports/figures/week9_project_pack")
    parser.add_argument("--week9-report", default="ai_isp_stage2/reports/week9_stage2_project_summary.md")
    parser.add_argument("--final-report", default="ai_isp_stage2/reports/stage2_final_project_report.md")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def fmt_float(value: str, digits: int = 4) -> str:
    return f"{float(value):.{digits}f}"


def best_denoise_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
    candidates = [row for row in rows if row["task"] == "week4_sidd_tiny_standard_eval"]
    if not candidates:
        return None
    return max(candidates, key=lambda row: float(row["best_psnr"]))


def write_evidence_csv(
    leaderboard_rows: list[dict[str, str]],
    engineering_rows: list[dict[str, str]],
    failure_rows: list[dict[str, str]],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "week9_project_evidence_pack.csv"
    best = best_denoise_row(leaderboard_rows)
    dncnn_engineering = next(
        (row for row in engineering_rows if row["run"] == "paired_rgb_sidd_tiny_dncnn_l2_2000"),
        None,
    )
    low_light = next((row for row in leaderboard_rows if row["task"] == "week7_low_light_eval"), None)

    rows = [
        {
            "module": "真实 paired RGB 去噪",
            "artifact": "week4_sidd_tiny_standard_eval + Week 9 leaderboard",
            "result": (
                f"{best['run']} reaches {fmt_float(best['best_psnr'])} dB PSNR / "
                f"{fmt_float(best['best_ssim'], 5)} SSIM"
                if best
                else "missing"
            ),
            "interview_value": "能解释为什么 residual DnCNN 是小数据 paired denoise 的强基线。",
            "next_action": "继续用它作为后续 loss、数据和部署实验的 reference baseline。",
        },
        {
            "module": "工程可部署性",
            "artifact": "stage2_engineering_summary.csv",
            "result": (
                f"DnCNN params={dncnn_engineering['params']}, checkpoint={dncnn_engineering['checkpoint_mb']} MB"
                if dncnn_engineering
                else "missing"
            ),
            "interview_value": "能把质量指标和参数量、checkpoint 大小一起讨论，而不是只报 PSNR。",
            "next_action": "Week 10-12 补 ONNX/C++ latency 和输出一致性。",
        },
        {
            "module": "低光增强扩展",
            "artifact": "week7_low_light_eval",
            "result": (
                f"{low_light['run']} reaches {fmt_float(low_light['best_psnr'])} dB PSNR / "
                f"{fmt_float(low_light['best_ssim'], 5)} SSIM"
                if low_light
                else "missing"
            ),
            "interview_value": "能说明 low-light enhancement 同时涉及亮度、颜色和噪声恢复。",
            "next_action": "补暗区 ROI、亮度统计和色偏分析。",
        },
        {
            "module": "失败案例诊断",
            "artifact": "week8_failure_taxonomy.csv",
            "result": f"{len(failure_rows)} failure types summarized",
            "interview_value": "能把 crop/error map 转成 failure taxonomy 和下一步实验。",
            "next_action": "后续可做 error-map 自动挖掘高误差 ROI。",
        },
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["module", "artifact", "result", "interview_value", "next_action"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def markdown_table(rows: list[list[str]], headers: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def build_week9_report(
    leaderboard_rows: list[dict[str, str]],
    engineering_rows: list[dict[str, str]],
    failure_rows: list[dict[str, str]],
    evidence_csv: Path,
) -> str:
    best = best_denoise_row(leaderboard_rows)
    leaderboard_table = markdown_table(
        [
            [
                row["task"],
                row["run"],
                fmt_float(row["best_psnr"]),
                fmt_float(row["best_ssim"], 5),
                row["best_psnr_step"],
            ]
            for row in leaderboard_rows
        ],
        ["Task", "Run", "Best PSNR", "Best SSIM", "Best Step"],
    )
    engineering_table = markdown_table(
        [
            [
                row["run"],
                row["model"],
                row["channels"],
                row["params"],
                row["checkpoint_mb"],
                row["best_psnr"],
                row["best_ssim"],
            ]
            for row in engineering_rows
        ],
        ["Run", "Model", "Ch", "Params", "Ckpt MB", "PSNR", "SSIM"],
    )
    failure_table = markdown_table(
        [
            [
                row.get("run", row.get("Run", "")),
                row.get("failure_type", row.get("Failure Type", "")),
                row.get("next_step", row.get("Next Step", "")),
            ]
            for row in failure_rows[:6]
        ],
        ["Run", "Failure Type", "Next Step"],
    )

    best_text = (
        f"当前 SIDD tiny denoise 最强结果是 `{best['run']}`，PSNR "
        f"{fmt_float(best['best_psnr'])} dB，SSIM {fmt_float(best['best_ssim'], 5)}。"
        if best
        else "当前 leaderboard 缺少 SIDD tiny denoise 结果。"
    )

    lines = [
        "# Week 9：阶段二项目总结、简历和面试表达",
        "",
        "Week 9 的目标不是继续堆模型，而是把 Week 0-8 的训练、数据、评估、失败案例和工程化线索整理成一个能复述、能追问、能继续迭代的 AI-ISP restoration 项目。",
        "",
        "## 1. 是否需要增加内容",
        "",
        "需要增加。原有 Week 9 已经有 leaderboard 和面试表达，但还缺少更清晰的项目交付包：",
        "",
        "- 简历/面试可直接引用的证据链。",
        "- 质量指标、参数量、checkpoint 大小的工程视角汇总。",
        "- failure taxonomy 到下一步实验的闭环表达。",
        "- 可一键复现 Week 9 项目包的脚本和结果文件。",
        "",
        "## 2. 新增运行命令",
        "",
        "```bash",
        "python ai_isp_stage2/scripts/20_export_week9_project_pack.py",
        "```",
        "",
        "输出文件：",
        "",
        f"- `{evidence_csv.as_posix()}`",
        "- `ai_isp_stage2/reports/week9_stage2_project_summary.md`",
        "- `ai_isp_stage2/reports/stage2_final_project_report.md`",
        "",
        "## 3. 阶段二 Leaderboard",
        "",
        *leaderboard_table,
        "",
        best_text,
        "",
        "## 4. 工程视角汇总",
        "",
        *engineering_table,
        "",
        "这张表用于回答社招面试里常见的工程追问：模型有多大、checkpoint 多大、RGB/RAW-like 输入通道怎么变化、后续是否能部署到 ONNX/C++。",
        "",
        "## 5. Failure Taxonomy 到下一步实验",
        "",
        *failure_table,
        "",
        "Week 8 的价值在 Week 9 里要表达成“诊断能力”：看到局部失败后，能判断是数据、loss、模型容量、训练步数还是任务定义的问题。",
        "",
        "## 6. 简历表述",
        "",
        "简洁版：",
        "",
        "```text",
        "基于 PyTorch 搭建 AI-ISP 图像恢复实验闭环，完成 SIDD paired RGB 去噪、synthetic low-light enhancement、NAFNet-lite 复现、PSNR/SSIM 评估、error map 和 failure crop 诊断；在 SIDD tiny 上 DnCNN residual baseline 达到 35.54 dB PSNR / 0.8837 SSIM，并整理参数量、checkpoint 大小和后续 ONNX/C++ 部署路径。",
        "```",
        "",
        "详细版：",
        "",
        "```text",
        "构建 AI-ISP Stage2 图像恢复项目：从 toy RGB denoise sanity check 出发，整理 SIDD Small sRGB paired train/val 数据，建立 noisy input baseline，对比 DnCNN residual、UNet、NAFNet-lite，并扩展 pseudo RAW/RGGB bridge 和 synthetic low-light enhancement。项目包含训练脚本、评估脚本、leaderboard、triplet/error map/failure crop 可视化、failure taxonomy、工程化参数汇总和面试复述材料，可解释 residual denoise、PSNR/SSIM 差异、RAW pack 输入差异和现代 restoration block 在小数据下的训练不足问题。",
        "```",
        "",
        "## 7. 面试讲述框架",
        "",
        "1. 先用 toy RGB denoise 跑通 Dataset -> Model -> Loss -> Metric -> Checkpoint -> Visualization。",
        "2. 再接入 SIDD paired RGB，先测 noisy input baseline，保证模型收益不是凭空判断。",
        "3. 用 DnCNN residual 建强基线，再对比 UNet 和 NAFNet-lite，解释结构假设和训练代价。",
        "4. 用 PSNR/SSIM、triplet、error map 和 failure crop 联合判断，而不是只看单一指标。",
        "5. 用 pseudo RAW/RGGB 和 low-light enhancement 把 RGB restoration 连接到 AI-ISP 场景。",
        "6. 最后把 failure case 分类，决定下一步是扩数据、改 loss、改模型、加训练步数还是做部署验证。",
        "",
        "## 8. 高频追问",
        "",
        "**Q1：为什么 DnCNN 比更复杂的结构还强？**",
        "",
        "当前任务是小规模 paired RGB denoise，输入和 clean 的结构高度一致，主要差异是噪声。Residual DnCNN 直接学习噪声残差，任务假设更匹配；复杂模型在数据少、训练短或配置不充分时不一定占优。",
        "",
        "**Q2：为什么 low-light 不能和 SIDD denoise 直接横向比 PSNR？**",
        "",
        "两者任务定义不同。Denoise 主要恢复噪声，low-light 同时涉及增亮、颜色恢复和噪声控制，所以 PSNR 只能在同任务内比较，跨任务要结合视觉和任务目标解释。",
        "",
        "**Q3：Week 8 failure case 对 Week 9 有什么价值？**",
        "",
        "它让项目从“跑出指标”升级到“能诊断问题”。社招面试更看重你是否能根据失败区域推断数据、loss、模型或训练策略问题，并提出下一轮实验。",
        "",
        "**Q4：这个阶段还不能证明什么？**",
        "",
        "不能证明真实量产 ISP tuning、AE/AWB/AF 联调、平台级 ISP 调试经验或 Imatest/iQ-Analyzer 实操经验；它证明的是 AI-ISP 图像恢复方向的实验闭环、评估诊断和工程化准备能力。",
        "",
        "## 9. Week 10-12 衔接",
        "",
        "Week 9 之后应优先补工程化闭环：Week 10 汇总参数量、checkpoint 大小和部署候选；Week 11 导出 ONNX 并做 PyTorch/ONNX 输出对齐；Week 12 做 C++ OpenCV DNN smoke test 和 CPU latency 记录。",
        "",
        "## 10. 自检问题",
        "",
        "1. noisy、clean、output、loss、metric 的关系是什么？",
        "2. 为什么 paired 数据必须像素对齐？",
        "3. DnCNN residual 为什么适合 denoise？",
        "4. UNet 为什么可能 SSIM 接近但 PSNR 较低？",
        "5. NAFNet-lite 结果不如 DnCNN 时，应该先怀疑结构还是训练设置？",
        "6. RAW pack 为什么通常是 4 通道？",
        "7. error map 和 failure crop 分别能定位什么问题？",
        "8. 这个项目如何讲成完整 AI-ISP restoration baseline？",
        "",
    ]
    return "\n".join(lines)


def build_final_report(report: str) -> str:
    sections = report.split("## 6. 简历表述")
    body = sections[0].rstrip()
    resume_part = "## 6. 简历表述" + sections[1] if len(sections) > 1 else ""
    return "\n".join(
        [
            "# 阶段二最终项目报告：AI-ISP 图像恢复实验闭环",
            "",
            "这份报告是 Week 9 项目包的最终版，用于阶段二收口、作品集整理和后续 Week 10-12 工程化衔接。",
            "",
            body,
            "",
            resume_part,
        ]
    )


def main() -> None:
    args = parse_args()
    leaderboard_rows = read_csv(Path(args.leaderboard))
    engineering_rows = read_csv(Path(args.engineering))
    failure_rows = read_csv(Path(args.failure_taxonomy))

    if not leaderboard_rows:
        raise FileNotFoundError(f"No leaderboard rows found: {args.leaderboard}")

    output_dir = Path(args.output_dir)
    evidence_csv = write_evidence_csv(leaderboard_rows, engineering_rows, failure_rows, output_dir)
    report = build_week9_report(leaderboard_rows, engineering_rows, failure_rows, evidence_csv)
    final_report = build_final_report(report)

    week9_path = Path(args.week9_report)
    final_path = Path(args.final_report)
    week9_path.parent.mkdir(parents=True, exist_ok=True)
    week9_path.write_text(report, encoding="utf-8")
    final_path.write_text(final_report, encoding="utf-8")

    print(f"saved: {evidence_csv}")
    print(f"saved: {week9_path}")
    print(f"saved: {final_path}")


if __name__ == "__main__":
    main()
