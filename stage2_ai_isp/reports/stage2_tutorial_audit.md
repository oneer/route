# 阶段二教程化审计与证据索引

本文是阶段二的事实索引，不替代周报。学习入口仍是
`stage2_ai_isp/stage2_start_here.md`。

## 1. 审查结论

阶段二已经具备可运行的 Dataset、训练、验证、checkpoint、指标、可视化、pseudo
RGGB、synthetic low-light、held-out test 和 ONNX Runtime C++ smoke test。当前主要
风险不是代码链路缺失，而是把不同协议的历史结果放在同一张“排名表”里，或把
RAW-like/synthetic/smoke test 写成真实 RAW、真实低光和量产部署。

本次审查坚持：

- 不重新声称跑过未运行的实验；
- 历史 validation SSIM 与新版标准窗口 SSIM 分开；
- `fair_compare_*.yaml` 只有配置，没有对应 run 时不产出排名；
- 自动报告保存事实，周报解释概念，总报告只做跨周总结。

## 2. 文档职责

| 类型 | 文件 | 职责 |
|---|---|---|
| 唯一入口 | `stage2_start_here.md` | 学习顺序、纪律、完成标准 |
| 教程主线 | `reports/week0_*.md`～`week12_*.md` | 原理、shape、代码、实验和练习 |
| 事实协议 | `evaluation_protocol.md`、`experiment_fairness_protocol.md` | split、指标和公平比较口径 |
| 自动证据 | `metrics.csv`、评估 CSV/JSON、图像 | 保存脚本实际输出，不承担教学叙事 |
| 总结 | `stage2_final_project_report.md`、`stage2_engineering_summary.md` | 跨周结论和工程边界 |
| 历史/规划 | `stage2_upgrade_plan.md`、`stage2_weekly_upgrade_from_reports.md` | 保留演进记录，不作为执行入口 |

## 3. 结论—证据链

| 可写结论 | 配置/代码 | run/checkpoint | 指标证据 | 可视化/测试 | 边界 |
|---|---|---|---|---|---|
| Toy RGB 训练闭环可运行 | `configs/toy_rgb_*`、`engine/train.py` | `runs/toy_rgb_*` | 各 run `metrics.csv` | `vis/`、engine tests | 合成任务，不代表真实噪声 |
| SIDD tiny paired sRGB 去噪可训练 | `paired_rgb_sidd_tiny_*.yaml` | DnCNN/UNet/NAFNet-lite runs | Week 3/4 CSV | triplet、error map | tiny 子集，不是官方 benchmark |
| train/val/test 未发现 source scene 交叉 | `07_prepare_*`、`23_audit_*` | 数据 manifest | `dataset_split_audit.json` | `test_data.py` | 只证明当前 manifest |
| DnCNN L2 冻结模型通过 held-out test | DnCNN L2 2000 config | `best_psnr.pth` | `test_set_metrics.json` | full-image test | test 只覆盖该冻结模型 |
| pseudo RGGB 4-channel 链路可训练 | pseudo RAW config/dataset | pseudo RAW 300-step run | Week 6 summary CSV | preview、shape test | 来自 sRGB，不是真实 RAW |
| synthetic low-light 链路可训练 | low-light config/script | UNet 300-step run | Week 7 CSV | triplet、diagnostics | 合成退化，不是真实采集 |
| failure ROI 可自动定位 | crop/taxonomy scripts | 读取已有 vis | crop/taxonomy CSV | crop sheet | 原因必须人工验证 |
| ONNX/Python/C++ ORT 数值对齐 | export/validate/C++ runner | DnCNN checkpoint | `deployment_evidence.json` | float tensor comparison | CPU smoke test，不是量产部署 |
| 单元测试通过 | `tests/` | 不适用 | unittest 输出 | 12 tests | 不替代大规模训练复现 |

## 4. 不能混用的结果

### 4.1 历史 validation 与最终 test

Week 0-9 的历史 SSIM 使用早期近似实现；最终 held-out test 使用 11×11 Gaussian
window。两者不能直接拼成统一排行榜。test 结果也不能反过来调参。

### 4.2 “当前最好”需要限定集合

- 三模型历史表中 DnCNN L2 高于当前 UNet/NAFNet-lite 配置；
- DnCNN L1 loss ablation 的历史 validation PSNR 略高于 DnCNN L2；
- 这些架构 run 的 loss、steps、batch 和宽度并未全部统一；
- 只有 DnCNN L2 冻结 checkpoint 有当前协议下的 held-out test。

因此应写“在指定表、split、配置和指标协议下最好”，不能写成模型普遍排名。

### 4.3 公平比较配置尚未形成实验结论

`configs/fair_compare_dncnn_mse_1000.yaml`、
`fair_compare_unet_mse_1000.yaml` 和
`fair_compare_nafnet_lite_mse_1000.yaml` 已固定主要变量，但当前没有对应
`runs/fair_compare_*` 证据。它们是待运行实验计划，不是已完成结果。

## 5. 数据域边界

| 名称 | 实际输入/GT | 可以证明 | 不能证明 |
|---|---|---|---|
| SIDD tiny | ISP 后 paired sRGB noisy/GT | paired RGB restoration | RAW sensor denoise、官方榜单 |
| pseudo RGGB | 从 sRGB 固定 RGGB 采样并 pack | 4-channel shape/training bridge | black level、线性 RAW、真实噪声 |
| synthetic low-light | clean sRGB 经固定曝光和噪声公式合成 | 受控低光增强闭环 | 真实短/长曝光采集能力 |
| ONNX Runtime C++ | x64 CPU `Session::Run` | backend 数值对齐和核心 latency | 端侧内存、功耗、量化和量产稳定性 |

SIDD GT 也不是天然无噪真值；学习者需要回到 Week 2 的 Dataset Card，理解其采集、
对齐、融合/估计方式及 sRGB ISP 处理带来的限制。

## 6. 复现顺序

```text
unittest
  -> dataset split audit
  -> noisy input baseline
  -> 1～5 image overfit
  -> frozen config training
  -> validation checkpoint selection
  -> triplet/error map/crop
  -> freeze design
  -> held-out test once
  -> ONNX export and backend alignment
```

代表性命令：

```powershell
$env:PYTHONPATH="stage2_ai_isp"
python -m unittest discover -s stage2_ai_isp/tests -v
python stage2_ai_isp/scripts/23_audit_dataset_splits.py
python stage2_ai_isp/scripts/22_evaluate_test_set.py `
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml `
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth
```

大规模训练不应为了“文档看起来完整”而盲目重跑。若要重跑，先保存环境、数据
manifest、配置、git commit、seed 和设备信息。

## 7. 验收矩阵

| 能力 | 当前材料 | 学习者仍需亲自完成 |
|---|---|---|
| 从零训练闭环 | 正式代码和测试齐全 | exercises 02～04、独立 capstone |
| SIDD/synthetic/pseudo RAW 区分 | Week 2/6/7 已说明 | 闭卷解释 GT 与 domain gap |
| 公平比较模型/loss | 协议和配置齐全 | 运行同协议多 seed，不能沿用历史排名 |
| 从失败反推问题 | top-error ROI 和模板齐全 | 人工标签与单变量验证实验 |
| 阶段一到阶段二连接 | Week 6 映射表 | 实现至少一个更完整 unprocessing 步骤 |
| ONNX/C++ 对齐 | 已有实测证据 | 在新配置上独立重复导出和比较 |

## 8. 尚存缺口

1. 缺少真实 sensor RAW / SID 短长曝光数据实验；
2. 缺少三个模型在完全相同协议下的多 seed 公平 run；
3. 缺少人工标注并由对照实验验证的代表性 failure case；
4. 未可靠记录训练峰值内存、统一线程 latency 和 MACs/FLOPs；
5. 未验证 TensorRT/INT8、移动端内存功耗或量产平台稳定性。

最值得继续补的三项：

1. 运行 `fair_compare_*` 的 3-seed 对比并单独发布结果；
2. 建立 6～10 个带人工语义标签和验证实验的 failure case 卡片；
3. 用真实 RAW 数据补一个最小 SID/RAW denoise overfit 与 domain-gap 对照。
