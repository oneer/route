#!/usr/bin/env python3
"""Export a Week 9 project pack for resume and interview review."""
# 中文说明：导出 Week9 项目包与最终报告所需证据。

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """中文说明：解析命令行参数，把脚本可调项集中到 argparse 命名空间。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回 argparse.Namespace，供 main() 读取脚本参数。
    """
    parser = argparse.ArgumentParser(description="Create Week 9 project-facing summary artifacts.")
    parser.add_argument(
        "--leaderboard",
        default="stage2_ai_isp/reports/figures/week9_stage2_summary/stage2_leaderboard.csv",
    )
    parser.add_argument(
        "--engineering",
        default="stage2_ai_isp/reports/figures/week10_engineering_summary/stage2_engineering_summary.csv",
    )
    parser.add_argument(
        "--failure-taxonomy",
        default="stage2_ai_isp/reports/figures/week8_failure_taxonomy/week8_failure_taxonomy.csv",
    )
    parser.add_argument("--output-dir", default="stage2_ai_isp/reports/figures/week9_project_pack")
    parser.add_argument("--week9-report", default="stage2_ai_isp/reports/week9_stage2_project_summary.md")
    parser.add_argument("--final-report", default="stage2_ai_isp/reports/stage2_final_project_report.md")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    """中文说明：读取外部文件或模型状态，并转换成当前脚本后续步骤需要的格式。
    
    输入：path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def fmt_float(value: str, digits: int = 4) -> str:
    """中文说明：实现 `fmt_float` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：value、digits。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    return f"{float(value):.{digits}f}"


def best_denoise_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
    """中文说明：实现 `best_denoise_row` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：rows。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：将当前脚本整理出的结果写入磁盘，作为阶段产物或报告素材。
    
    输入：leaderboard_rows、engineering_rows、failure_rows、output_dir。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
                f"DnCNN params={dncnn_engineering['params']}, checkpoint={dncnn_engineering['checkpoint_mb']} MB; "
                "ONNX/C++ alignment completed"
                if dncnn_engineering
                else "missing"
            ),
            "interview_value": "能把质量指标、参数量、模型大小、输出误差和 latency 一起讨论。",
            "next_action": "保持 held-out test 和 ONNX/C++ 对齐证据可复现。",
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
            "next_action": "在多组曝光/噪声参数和真实采集数据上验证泛化。",
        },
        {
            "module": "失败案例诊断",
            "artifact": "week8_failure_taxonomy.csv",
            "result": f"{len(failure_rows)} failure types summarized",
            "interview_value": "能把 crop/error map 转成 failure taxonomy 和下一步实验。",
            "next_action": "人工标注代表性 ROI，并用单变量对照实验验证推断原因。",
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
    """中文说明：实现 `markdown_table` 这一步的核心逻辑，供本文件的主流程复用。
    
    输入：rows、headers。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
    """中文说明：构造后续流程需要的对象或可视化产物，把零散配置集中成可复用结果。
    
    输入：leaderboard_rows、engineering_rows、failure_rows、evidence_csv。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
        f"在这张历史表收录的 SIDD tiny denoise 条目中，`{best['run']}` 的 validation "
        f"PSNR 最高，为 {fmt_float(best['best_psnr'])} dB。DnCNN L1 消融另有 "
        "35.6334 dB 的记录，但它不在这张表内；现有结果的 loss、steps 和 batch "
        "并未完全统一，因此不能据此宣称普遍模型排名。当前新版协议下的 held-out test "
        "只冻结评估了 DnCNN L2。"
        if best
        else "当前 leaderboard 缺少 SIDD tiny denoise 结果。"
    )

    lines = [
        "# Week 9：阶段二项目总结、简历和面试表达",
        "",
        "Week 9 的目标不是继续堆模型，而是把 Week 0-8 的训练、数据、评估、失败案例和工程化线索整理成一个能复述、能追问、能继续迭代的 AI-ISP restoration 项目。",
        "",
        "## 1. 项目交付内容",
        "",
        "Week 9 将前八周材料整理成以下可复查交付包：",
        "",
        "- 简历/面试可直接引用的证据链。",
        "- 质量指标、参数量、checkpoint 大小的工程视角汇总。",
        "- failure taxonomy 到下一步实验的闭环表达。",
        "- 可一键复现 Week 9 项目包的脚本和结果文件。",
        "",
        "## 2. 复现命令",
        "",
        "```bash",
        "python stage2_ai_isp/scripts/20_export_week9_project_pack.py",
        "```",
        "",
        "输出文件：",
        "",
        f"- `{evidence_csv.as_posix()}`",
        "- `stage2_ai_isp/reports/week9_stage2_project_summary.md`",
        "- `stage2_ai_isp/reports/stage2_final_project_report.md`",
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
        "基于 PyTorch 搭建 AI-ISP 图像恢复实验闭环，完成 SIDD paired RGB 去噪、synthetic low-light enhancement、NAFNet-lite 复现、held-out test、error map 和 failure crop 诊断；DnCNN 在 20 张 held-out test pairs 上达到 37.00 dB / 0.9111，并完成 ONNX Runtime Python/C++ CPU 输出对齐和 latency 验证。",
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
        "## 9. Week 10-12 工程证据",
        "",
        "Week 10 已补 held-out test 和工程汇总；Week 11 已完成 ONNX 对齐；Week 12 已完成 C++ ONNX Runtime CPU 输出对齐与重复 latency。",
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
    """中文说明：构造后续流程需要的对象或可视化产物，把零散配置集中成可复用结果。
    
    输入：report。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    sections = report.split("## 6. 简历表述")
    body = sections[0].rstrip()
    resume_part = "## 6. 简历表述" + sections[1] if len(sections) > 1 else ""
    body = "\n".join("#" + line if line.startswith("#") else line for line in body.splitlines())
    resume_part = "\n".join(
        "#" + line if line.startswith("#") else line for line in resume_part.splitlines()
    )
    return "\n".join(
        [
            "# 阶段二最终项目报告：AI-ISP 图像恢复实验闭环",
            "",
            "这份报告用于阶段二收口；Week 10-12 工程证据已补齐。",
            "",
            body,
            "",
            resume_part,
        ]
    ).rstrip() + "\n"


def main() -> None:
    """中文说明：脚本主入口，按顺序组织读取输入、执行核心逻辑和写出结果。
    
    输入：主要依赖当前对象状态或命令行参数。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
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
