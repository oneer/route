# AI-ISP Stage 2

阶段二聚焦 AI-ISP 和图像恢复。从 toy RGB 去噪起步，逐步走向真实成对 RGB
数据（SIDD），最终形成训练、严格评估、独立实现和部署验证闭环。

**状态：** ✅ Week 0–12 工程基线已完成。已加入 held-out test、自动化测试、
ONNX/PyTorch 对齐以及 ONNX Runtime C++ CPU 推理与 latency。学习者仍需完成
`exercises/` 和独立 capstone，才能证明个人独立掌握。

第一次学习请从 [`stage2_start_here.md`](stage2_start_here.md) 开始。该文件是唯一执行入口，
并包含自动化测试、独立练习和能力边界。

全新环境先运行 [`quickstart.md`](quickstart.md)。它提供不依赖外部数据的 smoke 路径，
用于在正式学习前验证安装、测试、训练、checkpoint 和可视化。

实验事实、教程文本和待运行计划的边界见
[`reports/stage2_tutorial_audit.md`](reports/stage2_tutorial_audit.md)。

## 高通岗位面试入口

- [Job ID 3083325 面试就绪与差距审计](../study-roadmap/高通3083325-Camera-ISP-Algorithm-System-Engineer定向提升报告.md#十四2026-07-19-面试就绪审计与二次补强)
- [Week 10：Camera Feature 准入、fallback、时序与发布门槛](reports/week10_engineering_summary.md#12-高通岗位补强从离线模型到-camera-feature)
- [跨阶段 Camera Systems Capstone](../camera_system_capstone/reports/qualcomm_3083325_capstone_report.md)

这部分用于把模型指标转成 Camera feature 决策；真实 Sensor RAW、连续视频、肤色专项、Snapdragon runtime 和线上客户闭环仍为 `not_run`。

## 学习报告

建议不要按“脚本列表”阅读本阶段。统一入口是
[`stage2_start_here.md`](stage2_start_here.md)，事实与证据边界先看
[`reports/stage2_tutorial_audit.md`](reports/stage2_tutorial_audit.md)。每一周都按下面的闭环学习：

```text
问题背景 -> 数据合同 -> 模型/公式 -> 单变量实验 -> 指标与图像
-> failure 定位 -> 结论边界 -> 面试复述 -> 独立练习
```

| 学习段 | 周次 | 学完后应能独立完成 |
|---|---|---|
| 训练闭环 | Week 0-1 | 手写最小训练循环，解释 residual、loss、patch 和 baseline |
| 真实 paired RGB | Week 2-4 | 审计配对/split，设计公平实验，并联合解读 PSNR、SSIM、crop 和 error map |
| AI-ISP 扩展 | Week 5-8 | 解释轻量恢复块、pseudo RAW、合成低光和 failure taxonomy 的作用与边界 |
| 冻结与部署 | Week 9-12 | 冻结模型与合同，完成 ONNX/Python/C++ CPU 数值对齐并报告测量口径 |

报告中的 `verified_*` 只描述证据类型，不代表量产成熟度：`verified_public`
是公开真实数据，`verified_synthetic` 是合成任务，`verified_partial` 是局部链路实测，
`not_run` 是计划。尤其不得把 SIDD tiny、pseudo RGGB、synthetic low-light 或 x64 CPU
ORT smoke test改写为真实 RAW、自采低光或 Snapdragon 量产结果。

报告已经按周整理，不再使用 `week1a/week1b/week1c` 这种碎片编号。

| 顺序 | 报告 | 作用 |
|---:|---|---|
| 0 | `stage2_start_here.md` | 唯一学习入口、真实状态和验收纪律 |
| 1 | `quickstart.md` | 全新环境、无外部数据 smoke 和 SIDD 数据入口 |
| 2 | `reports/week0_foundation.md`～`week9_stage2_project_summary.md` | 从训练基础到项目总结 |
| 3 | `reports/week10_engineering_summary.md` | 工程汇总、冻结设计和 held-out test |
| 4 | `reports/week11_onnx_export.md` | ONNX 导出、checker 和 Python ORT 对齐 |
| 5 | `reports/week12_onnx_cpp_deployment.md` | C++ ORT 对齐和 latency 验收 |
| 6 | `deployment/README.md` | Week 11-12 的命令操作手册 |
| 7 | `exercises/06_capstone_spec.md` | 完成全部教学后的独立结项 |
| 8 | `reports/evaluation_protocol.md` | train/val/test 与标准指标协议 |
| 9 | `reports/stage2_tutorial_audit.md` | 证据链、范围边界和剩余缺口 |

推荐阅读顺序：

```text
stage2_start_here.md
  -> quickstart.md
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
  -> week9_stage2_project_summary.md
  -> week10_engineering_summary.md
  -> week11_onnx_export.md
  -> week12_onnx_cpp_deployment.md + deployment/README.md
  -> exercises/06_capstone_spec.md
  -> stage2_final_project_report.md
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

所有命令默认从仓库根目录运行。完整的环境检查、Windows UTF-8 设置、smoke 训练、
SIDD 数据入口和停止条件见 [`quickstart.md`](quickstart.md)。最小安装命令：

```powershell
python -m pip install -r stage2_ai_isp/requirements.txt
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

## Camera scene evaluation backfill

`scripts/24_evaluate_camera_scenes.py` evaluates frozen scene/method rows and
reports PSNR gain, noise RMSE reduction, texture retention, edge loss, color
bias, and a deterministic failure label. `scripts/25_export_scene_failure_matrix.py`
aggregates those labels.

Run `scripts/23_prepare_camera_scene_comparison.py` first. It consumes the
frozen SIDD evaluation split, reuses the Stage 1 bilateral implementation, and
records the existing aligned DnCNN ORT FP32 outputs. Then run scripts 24 and 25
to regenerate the device-group summaries, failure matrix, and trade-off report.

This evidence is paired public sRGB restoration, not self-captured Camera data
or Sensor RAW AI-ISP. FP16 is not included in the image-quality comparison until
a complete frozen-split FP16 output set is available.
