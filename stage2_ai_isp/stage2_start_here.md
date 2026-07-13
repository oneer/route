# 阶段二唯一学习入口

阶段二的目标不是“把现有命令全部运行一遍”，而是逐步达到四个能力层级：

```text
看懂 -> 能修改 -> 能独立实现 -> 能解释设计取舍
```

## 当前真实状态

| 周次 | 内容 | 状态 |
|---|---|---|
| Week 0-9 | 训练基础、SIDD paired RGB、模型对比、评估、RAW-like、低光和 failure analysis | 已有代码与实验记录 |
| Week 10 | 参数量、checkpoint 和工程汇总 | 已完成；含 held-out test 与工程指标 |
| Week 11 | ONNX 导出与 PyTorch/ONNX 对齐 | 已实测完成 |
| Week 12 | C++ ONNX Runtime 推理与 latency | 已实测完成；OpenCV DNN 为可选扩展 |

阶段二工程基线已闭环。学习者本人仍需完成 exercises 和独立 capstone，才能把状态从
“项目材料完整”提升为“个人独立掌握”。

## 必须遵循的学习顺序

0. `quickstart.md`：先验证环境、测试和最小 smoke。
1. `reports/week0_foundation.md`
2. `reports/week1_toy_rgb_denoise.md`
3. `exercises/01_foundation_questions.md`
4. `reports/week2_real_paired_rgb.md`
5. `exercises/02_dataset_skeleton.py`
6. `reports/week3_real_rgb_experiments.md`
7. `exercises/03_training_loop_skeleton.py`
8. `reports/week4_loss_metric_visualization.md`
9. `exercises/04_metrics_skeleton.py`
10. `reports/week5_nafnet_reproduction.md`
11. `reports/week6_pseudo_raw_isp_bridge.md`
12. `reports/week7_low_light_rgb_enhancement.md`
13. `reports/week8_failure_case_analysis.md`
14. `exercises/05_debug_broken_training.md`
15. `reports/week9_stage2_project_summary.md`
16. `reports/week10_engineering_summary.md`
17. `reports/week11_onnx_export.md`
18. `reports/week12_onnx_cpp_deployment.md`，操作手册配合 `deployment/README.md`。
19. `exercises/06_capstone_spec.md`
20. `reports/stage2_final_project_report.md`

Capstone 放在 Week 12 之后，因为它要求学习者独立完成 ONNX 导出与输出对齐。没有完成
Week 10-12 时，不应跳过部署知识直接做结项。

## 学习优先级

| 优先级 | 内容 | 要求 |
|---|---|---|
| 第一遍必须掌握 | Week 0-4、Week 8、Week 10-12、对应 skeleton | 能独立解释并完成最小实验 |
| 第二遍深入 | Week 5 NAFNet、Week 6 pseudo RAW、Week 7 low-light | 完成主线后再分析结构和 domain gap |
| 了解即可 | LPIPS、完整官方 NAFNet、OpenCV DNN 可选样例 | 知道用途和边界，不作为阶段二通过条件 |
| 后续阶段再做 | 真实 RAW/SID、TensorRT/INT8、移动端功耗 | 阶段三/四或扩展项目 |

优先级不是让学习者跳过报告，而是防止第一遍同时深挖所有模型、指标和部署后端。

`../study-roadmap/阶段2-AI-ISP图像恢复学习路线.md` 中的 Week 0-12 是正式路线。
其中“旧版 8 周路线”只用于查看历史规划，不作为执行入口。

开始前先读 `reports/stage2_tutorial_audit.md`。它负责说明哪些结论有
config/run/checkpoint/CSV/图像证据，哪些只是教程、历史记录或待运行计划。

## 三条评估纪律

1. validation 用于选模型和调参，test 只在方案冻结后评估。
2. 本仓库指标只用于同一协议下比较；不能直接冒充 SIDD 官方 benchmark。
3. pseudo RGGB 来自已渲染 sRGB，只能称为 RAW-like shape bridge，不能称为真实 sensor RAW。

## 每周完成标准

每周都必须留下四类证据：

- 理解：闭卷解释输入、输出和核心原理。
- 实现：完成对应 exercises，不复制正式代码。
- 调试：至少定位一个故意制造或真实遇到的问题。
- 证据：保存配置、指标、图像和一段自己的结论。

只完成运行命令，不算完成该周。

每周复盘统一回答以下问题：

1. 输入域、输出域和 GT 从哪里来，tensor shape 是什么；
2. split 是否按 source scene 隔离，是否可能泄漏；
3. 模型、loss、optimizer、scheduler 和 validation 如何连接；
4. baseline、output、GT、error map 和 crop 分别说明什么；
5. 结果证明什么、不证明什么；
6. 下一步实验只改变哪个变量，如何判定假设成立；
7. 完成一个 shape 跟踪、一个小样本 overfit 或一个独立实现练习。

## 自动化检查

在仓库根目录运行：

```powershell
$env:PYTHONPATH="stage2_ai_isp"
python -m unittest discover -s stage2_ai_isp/tests -v
```

所有测试通过，才允许修改模型、数据集或训练引擎后继续做实验。
