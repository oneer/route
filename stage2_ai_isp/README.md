# AI-ISP Stage 2

阶段二聚焦 AI-ISP 和图像恢复。从 toy RGB 去噪起步，逐步走向真实成对 RGB
数据（SIDD），最终形成训练、严格评估、独立实现和部署验证闭环。

**状态：** ✅ Week 0–12 工程基线已完成。已加入 held-out test、自动化测试、
ONNX/PyTorch 对齐以及 ONNX Runtime C++ CPU 推理与 latency。学习者仍需完成
`exercises/` 和独立 capstone，才能证明个人独立掌握。

第一次学习请从 [`stage2_start_here.md`](stage2_start_here.md) 开始。该文件是唯一执行入口，
并包含自动化测试、独立练习和能力边界。

实验事实、教程文本和待运行计划的边界见
[`reports/stage2_tutorial_audit.md`](reports/stage2_tutorial_audit.md)。

## 学习报告

报告已经按周整理，不再使用 `week1a/week1b/week1c` 这种碎片编号。

| 顺序 | 报告 | 作用 |
|---:|---|---|
| 0 | `stage2_start_here.md` | 唯一学习入口、真实状态和验收纪律 |
| 1 | `reports/week0_foundation.md` | 神经网络训练基础 |
| 2 | `reports/week1_toy_rgb_denoise.md` | Toy RGB 去噪完整闭环 |
| 3 | `reports/week2_real_paired_rgb.md` | 真实成对 RGB 数据入口 |
| 4 | `reports/week3_real_rgb_experiments.md` | 真实 RGB 去噪小规模实验 |
| 5 | `reports/week4_loss_metric_visualization.md` | Loss / Metric / 可视化评估体系 |
| 6 | `reports/week5_nafnet_reproduction.md` | NAFNet / 轻量图像恢复模型复现 |
| 7 | `reports/week6_pseudo_raw_isp_bridge.md` | Pseudo RAW / ISP bridge |
| 8 | `reports/week7_low_light_rgb_enhancement.md` | 低光 RGB 增强小实验 |
| 9 | `reports/week8_failure_case_analysis.md` | Failure case 和局部 crop 分析 |
| 10 | `reports/week9_stage2_project_summary.md` | 阶段二项目总结、简历和面试表达 |
| 11 | `reports/evaluation_protocol.md` | train/val/test 与标准指标协议 |
| 12 | `deployment/README.md` | ONNX、C++ 输出对齐和 latency |
| 13 | `reports/stage2_tutorial_audit.md` | 证据链、范围边界和剩余缺口 |

推荐阅读顺序：

```text
stage2_start_here.md
  -> stage2_learning_flow.md
  -> week0_foundation.md
  -> week1_toy_rgb_denoise.md
  -> week2_real_paired_rgb.md
  -> week3_real_rgb_experiments.md
  -> week4_loss_metric_visualization.md
  -> week5_nafnet_reproduction.md
  -> week6_pseudo_raw_isp_bridge.md
  -> week7_low_light_rgb_enhancement.md
  -> week8_failure_case_analysis.md
  -> exercises/06_capstone_spec.md
  -> week9_stage2_project_summary.md
  -> deployment/README.md
```

## 当前进度

当前核心学习内容和部署工具如下：

| Week | 主题 | 状态 |
|---|---|---|
| 0 | 训练闭环基础梳理 | ✅ 完成 |
| 1 | Toy RGB 去噪闭环（TinyCNN / DnCNN / L1 vs L2 / patch size / noise type） | ✅ 完成 |
| 2 | 真实成对 RGB 数据入口（SIDD tiny 子集准备、数据检查、baseline 测量） | ✅ 完成 |
| 3 | 真实 RGB 去噪实验（DnCNN L1/L2、patch 64/128、UNet baseline、NAFNet-lite） | ✅ 完成 |
| 4 | Loss / Metric / 可视化评估体系（三联图、error map、多模型对比） | ✅ 完成 |
| 5 | NAFNet-lite 复现学习指导 | ✅ 完成 |
| 6 | Pseudo RAW / ISP bridge | ✅ 完成 |
| 7 | 低光 RGB 增强实验 | ✅ 完成 |
| 8 | Failure case 和局部 crop 分析 | ✅ 完成 |
| 9 | 阶段二项目总结、简历和面试题库 | ✅ 完成 |
| 10 | Engineering summary、测试集和工程指标协议 | ✅ 完成 |
| 11 | ONNX 导出与 PyTorch/ONNX 对齐 | ✅ 完成 |
| 12 | C++ ONNX Runtime 推理和多次 latency | ✅ 完成；OpenCV DNN 为可选 |

完整闭环：

```text
toy RGB denoise
  -> real SIDD paired RGB denoise
  -> DnCNN / UNet / NAFNet-lite comparison
  -> metric / triplet / error map / crop analysis
  -> pseudo RAW / low-light bridge
  -> portfolio and interview summary
```

## 环境

```bash
pip install -r requirements.txt
```

自动化测试：

```powershell
$env:PYTHONPATH="stage2_ai_isp"
python -m unittest discover -s stage2_ai_isp/tests -v
```

真实 paired 数据准备完成后运行 source-scene 泄漏审计：

```powershell
python stage2_ai_isp/scripts/23_audit_dataset_splits.py
```

审计会检查 train/val/test 的 noisy-clean 配对、manifest 覆盖、重复行、尺寸一致性和 source scene 交叉；任一失败都会返回非零退出码。

## Week 1 常用命令

TinyCNN probe：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_10.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_50.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

DnCNN residual：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn.yaml
```

L1 / L2 对比：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l1.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2.yaml
```

测 noisy 输入 baseline：

```bash
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

Paired RGB smoke test：

```bash
python stage2_ai_isp/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_smoke_dncnn_l2.yaml
```

## Week 2 常用命令

准备外部真实成对 RGB 小子集：

```bash
python stage2_ai_isp/scripts/04_prepare_paired_rgb_subset.py --source-noisy-dir path/to/noisy --source-clean-dir path/to/clean --output-dir stage2_ai_isp/datasets/sidd_tiny --train-count 80 --val-count 20 --size 512
```

准备 SIDD Small sRGB 小子集：

```bash
python stage2_ai_isp/scripts/07_prepare_sidd_small_subset.py --source-root stage2_ai_isp/datasets/downloads/SIDD_Small_sRGB_Only/SIDD_Small_sRGB_Only/Data --output-dir stage2_ai_isp/datasets/sidd_tiny --train-count 80 --val-count 20 --crop-size 512
```

检查 SIDD train / val 配对：

```bash
python stage2_ai_isp/scripts/06_inspect_paired_dataset.py --noisy-dir stage2_ai_isp/datasets/sidd_tiny/train/noisy --clean-dir stage2_ai_isp/datasets/sidd_tiny/train/clean --output-dir stage2_ai_isp/reports/figures/week2_sidd_tiny_dataset_inspection --max-samples 8
python stage2_ai_isp/scripts/06_inspect_paired_dataset.py --noisy-dir stage2_ai_isp/datasets/sidd_tiny/val/noisy --clean-dir stage2_ai_isp/datasets/sidd_tiny/val/clean --output-dir stage2_ai_isp/reports/figures/week2_sidd_tiny_val_inspection --max-samples 8
```

导出 Week 2 Dataset Card：

```bash
python stage2_ai_isp/scripts/14_export_week2_dataset_card.py
```

测真实子集 noisy 输入 baseline：

```bash
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_300.yaml
```

训练真实子集：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

## Week 3 常用命令

DnCNN L2 长训练：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
```

DnCNN L1 / L2 对比：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l1_2000.yaml
```

patch 64 / 128 对比：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000.yaml
```

UNet baseline：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_unet_l1_1000.yaml
```

导出 Week 3 模型对比表：

```bash
python stage2_ai_isp/scripts/15_export_week3_model_comparison.py
```

CPU 友好的 SIDD Tiny 300-step 对比：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_300.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_unet_l1_300.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_300.yaml
```

## Week 4 常用命令

检查 paired RGB 数据是否对齐，并生成样本图：

```bash
python stage2_ai_isp/scripts/06_inspect_paired_dataset.py --noisy-dir stage2_ai_isp/runs/paired_rgb_smoke/noisy --clean-dir stage2_ai_isp/runs/paired_rgb_smoke/clean --output-dir stage2_ai_isp/reports/figures/week2_smoke_dataset_inspection --max-samples 6
```

汇总多个训练 run 的 PSNR / SSIM、三联图和 error map：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/paired_rgb_smoke_dncnn_l2 stage2_ai_isp/runs/paired_rgb_smoke_nafnet_lite_l1 --output-dir stage2_ai_isp/reports/figures/week4_smoke_eval --report-md stage2_ai_isp/reports/week4_smoke_eval_results.md --title "Week 4 Smoke Evaluation Results"
```

真实 SIDD Tiny 三模型评估：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_300 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_300 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_300 --output-dir stage2_ai_isp/reports/figures/week4_sidd_tiny_eval --report-md stage2_ai_isp/reports/week4_sidd_tiny_eval_results.md --title "Week 4 SIDD Tiny Evaluation Results"
```

真实 SIDD Tiny 标准版评估：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_1000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 --output-dir stage2_ai_isp/reports/figures/week4_sidd_tiny_standard_eval --report-md stage2_ai_isp/reports/week4_sidd_tiny_standard_eval_results.md --title "Week 4 SIDD Tiny Standard Evaluation Results"
```

真实 SIDD Tiny 消融评估：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l1_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_1000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 --output-dir stage2_ai_isp/reports/figures/week4_sidd_tiny_ablation_eval --report-md stage2_ai_isp/reports/week4_sidd_tiny_ablation_eval_results.md --title "Week 4 SIDD Tiny Ablation Evaluation Results"
```

导出 Week 4 评估协议摘要：

```bash
python stage2_ai_isp/scripts/16_export_week4_evaluation_protocol.py
```

## Week 5 常用命令

NAFNet-lite smoke 训练：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_smoke_nafnet_lite_l1.yaml
```

NAFNet-lite 真实 paired RGB 小子集训练：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml
```

导出 Week 5 NAFNet-lite 专项分析：

```bash
python stage2_ai_isp/scripts/17_export_week5_nafnet_analysis.py
```

## Week 6 常用命令

生成 pseudo RAW / ISP bridge 图：

```bash
python stage2_ai_isp/scripts/08_pseudo_raw_isp_bridge.py --input stage2_ai_isp/datasets/sidd_tiny/val/clean/pair_00001.png --output-dir stage2_ai_isp/reports/figures/week6_pseudo_raw_isp --crop-size 256
```

预览 pseudo RGGB dataset：

```bash
python stage2_ai_isp/scripts/12_preview_pseudo_raw_dataset.py
```

训练 pseudo RGGB baseline：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
```

导出 RGB vs pseudo RGGB 对比：

```bash
python stage2_ai_isp/scripts/18_export_week6_pseudo_raw_summary.py
```

## Week 7 常用命令

准备 synthetic low-light RGB 数据：

```bash
python stage2_ai_isp/scripts/09_prepare_low_light_rgb_subset.py --source-root stage2_ai_isp/datasets/sidd_tiny --output-dir stage2_ai_isp/datasets/sidd_low_light_tiny --figure-dir stage2_ai_isp/reports/figures/week7_low_light_rgb --exposure 0.28 --read-noise 0.015 --shot-noise 0.025 --seed 123 --max-figure-samples 8
```

训练和评估低光增强 UNet：

```bash
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/low_light_sidd_tiny_unet_l1_300.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/low_light_sidd_tiny_unet_l1_300.yaml
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/low_light_sidd_tiny_unet_l1_300 --output-dir stage2_ai_isp/reports/figures/week7_low_light_eval --report-md stage2_ai_isp/reports/week7_low_light_eval_results.md --title "Week 7 Low-Light RGB Evaluation Results"
```

导出低光任务专属诊断指标：

```bash
python stage2_ai_isp/scripts/21_export_week7_low_light_diagnostics.py
```

## Week 8 常用命令

生成局部 crop failure case 图：

```bash
python stage2_ai_isp/scripts/10_make_failure_case_crops.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_1000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 stage2_ai_isp/runs/low_light_sidd_tiny_unet_l1_300 --output-dir stage2_ai_isp/reports/figures/week8_failure_case_crops --crop-size 96 --zoom 3
```

导出 failure taxonomy 和下一步实验建议：

```bash
python stage2_ai_isp/scripts/19_export_week8_failure_taxonomy.py
```

## Week 9 常用命令

导出阶段二总榜：

```bash
python stage2_ai_isp/scripts/11_export_stage2_summary.py --metric-csvs stage2_ai_isp/reports/figures/week4_sidd_tiny_standard_eval/metrics_summary.csv stage2_ai_isp/reports/figures/week7_low_light_eval/metrics_summary.csv --output-dir stage2_ai_isp/reports/figures/week9_stage2_summary
```

导出 Week 9 项目交付包、简历表达和最终项目报告：

```bash
python stage2_ai_isp/scripts/20_export_week9_project_pack.py
```

## 项目结构

```text
stage2_ai_isp/
├── ai_isp/      # dataset、engine、metrics、models、utils
├── configs/     # 训练配置
├── materials/   # 前置学习材料
├── reports/     # 按周整理后的学习报告
├── runs/        # 训练输出，已 git ignore
└── scripts/     # 训练、测 baseline、准备数据脚本
```

## 学习检查点

进入 Week 3 前，最好能说清楚：

1. noisy、clean、output 分别是什么；
2. loss、backward、optimizer 各自负责什么；
3. 为什么 DnCNN residual 适合去噪；
4. L1 和 L2/MSE 的差异；
5. patch size 为什么影响速度和指标；
6. 为什么比较模型前要先测 noisy 输入 baseline；
7. paired RGB 数据为什么必须保证 noisy/clean 对齐。
8. Week 2 为什么先做真实 paired RGB 数据入口，而不是直接上 RAW / SID。

如果 1-6 还不清楚，先回到 `reports/week1_toy_rgb_denoise.md`。
如果 7-8 还不清楚，先回到 `reports/week2_real_paired_rgb.md`。
