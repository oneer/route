# Stage 1 报告导航

这里同时保存教程正文、模块实验、全量结果和历史复盘。第一次学习不要按文件大小顺序阅读，也不要从 T01–T14 全量图片开始。

四阶段统一教程标准见[Week Report 教程化要求大纲](../../study-roadmap/四阶段周报告教程化要求大纲.md)。Week 1–6 主线报告均补充了关键词/参数验收表和对应面试闭环。

本目录按“读完即可复现和讲解”的统一闭环组织。每篇主线报告都能找到：本周在全链路的位置、输入输出合同、背景与公式、代码入口、完整参数方向、实验与结果解释、failure/RCA、trade-off、证据等级、跨周连接、五类面试题和动手验收。若某项只能在模块详解中展开，summary 会给出明确导航，不把未运行方案写成结果。

证据标签统一使用：

| 标签 | 含义 | 可以怎样表述 |
|---|---|---|
| `verified_real` | 自采真实设备/受控实验已验证 | 仅在保留采集协议、设备和产物时使用 |
| `verified_public` | 公开真实数据已实际运行 | 可描述当前数据集趋势，不外推到自有 Sensor |
| `verified_synthetic` | 合成输入或故障注入已运行 | 可证明数学/流程/方向，不证明真实分布 |
| `verified_proxy` | reference 或代理指标已运行 | 只能写“相对该 reference/proxy” |
| `verified_partial` | 只验证链路的一部分 | 必须点明缺失环节 |
| `not_run` | 方案、模板或待采集 | 不得出现在“已完成结果”中 |

## 推荐主线

1. 先完成[前置自测](../materials/prerequisites.md)和[15 分钟冒烟验证](../materials/stage1_start_here.md)。
2. 每周先读 summary，再做练习，最后查看模块报告中的参考结果。
3. 用[教程化审查表](stage1_tutorial_audit.md)追踪代码、配置、命令、产物和测试。
4. 遇到指标或实验边界问题时查[参考文献与外部资料](references.md)。

每周建议采用同一个学习循环：

```text
先读定位与输入合同
  -> 不看结果先写参数方向预测
  -> 运行单样张最小命令
  -> 查看中间 JSON/曲线/mask/crop
  -> 完成故障注入或单变量 sweep
  -> 对照现成全量结果
  -> 闭卷回答五类面试题
  -> 勾选学习验收
```

只读完文字、只生成最终 PNG，或只记住平均指标，都不算完成该周。

阅读每个概念时，不要只记“要做什么”，至少要回答下面四个问题：

1. **它是什么：** 这个字段、数据域或算法在物理上代表什么。
2. **为什么需要：** 它为哪一个后续步骤提供输入、尺度或空间约定。
3. **错了会怎样：** 错误会表现为偏色、截断、伪影，还是坐标错位。
4. **如何验证：** 用什么断言、统计量、局部 crop 或对照实验确认理解和实现正确。

主线 summary 用于建立这四层认识；模块详解给出公式、代码和完整实验；全量图表只用于查证，不替代原因分析。

## 文档类型

| 标记 | 用途 | 阅读方式 |
|---|---|---|
| 主线 | 建立学习顺序和核心概念 | 按周必读 |
| 详解 | 模块原理、实现、参数和失败案例 | 完成预测后阅读 |
| 实验附录 | T01–T14 全量图表和 JSON 结果 | 按问题查证，不要求逐项背诵 |
| 审计 | 证据边界、完成状态和缺口 | 写报告或求职前复核 |
| 历史 | 早期版本或阶段性改进计划 | 不作为当前状态来源 |

## 总览与审计

| 类型 | 文档 | 用途 |
|---|---|---|
| 主线 | [阶段一总报告](stage1_report.md) | 项目目标、完整 Pipeline、能力边界和阶段结论 |
| 审计 | [教程化审查与证据对应表](stage1_tutorial_audit.md) | 报告—代码—配置—脚本—产物—测试对应关系 |
| 审计 | [模块掌握标准](module_mastery_matrix.md) | 入门、掌握、面试可讲的证据标准 |
| 审计 | [可落地 RAW 体检与画质诊断](feasible_raw_quality_audit.md) | clipping、ROI proxy、DPC 注入/扫描和 AWB baseline |
| 参考 | [参考文献与外部资料](references.md) | 规范、论文、官方文档和开源项目来源 |
| 参考 | [OpenISP 模块笔记](openisp_reference_notes.md) | 从学习 baseline 过渡到更完整 ISP 模块表 |
| 历史 | [深度复盘与改进计划](stage1_deep_review_improvement_plan.md) | 历史缺陷清单；当前状态以教程化审查表为准 |
| 历史 | [Week 3 Demosaic 早期报告](week3_demosaic_report.md) | 归档；主线使用 `week3/demosaic_report.md` |

## Week 1：RAW / Sensor 数据直觉

- 主线：[Week 1 总结](week1/summary.md)
- 详解/附录：[RAW metadata 与统计](week1/raw_statistics.md)
- 详解/附录：[暗部、中间调、高光 ROI](week1/roi_analysis.md)
- 练习：[陌生 DNG 输入合同](../exercises/week1_raw_contract.md)

## Week 2：BLC / DPC / LSC

- 主线：[Week 2 总结](week2/summary.md)
- 详解/附录：[BLC](week2/blc_report.md) · [DPC](week2/dpc_report.md) · [LSC](week2/lsc_report.md)
- 练习：[DPC 注入与 precision/recall](../exercises/week2_dpc_injection.py)
- 已完成实测：[DPC 参数扫描](feasible_raw_quality_audit.md#dpc-参数扫描)

## Week 3：Demosaic / AWB

- 主线：[Week 3 总结](week3/summary.md)
- 详解/附录：[Demosaic](week3/demosaic_report.md) · [AWB](week3/awb_report.md)
- 练习：[最小 RGGB bilinear demosaic](../exercises/week3_demosaic_todo.py)

## Week 4：CCM / Gamma / Tone Mapping

- 主线：[Week 4 总结](week4/summary.md)
- 详解/附录：[CCM](week4/ccm_report.md) · [Gamma](week4/gamma_report.md) · [Tone Mapping](week4/tone_mapping_report.md)
- 练习：[调试挑战 4–5](../exercises/debug_challenges.md)

## Week 5–6：评价与毕业验收

- 主线/实验：[Week 5 IQA 与消融](week5/iqa_ablation_report.md)
- 主线/实验：[Week 6 综合验收](week6/mastery_gap_closure_report.md)
- 练习：[调试挑战](../exercises/debug_challenges.md) · [独立毕业任务](../exercises/final_project.md)

## 面试材料

- [分周面试题导航](interview/README.md)
- [Week 1：RAW、DNG Metadata 与 Sensor 数据直觉](interview/week1_raw_sensor_questions.md)
- [Week 2：BLC、DPC、LSC 与 RAW 前端校正](interview/week2_frontend_correction_questions.md)
- [Week 3：Demosaic、AWB 与线性 RGB](interview/week3_demosaic_awb_questions.md)
- [Week 4：CCM、Tone Mapping、Gamma 与显示编码](interview/week4_color_tone_questions.md)
- [Week 5：IQA、消融、ROI 与参数评价](interview/week5_iqa_ablation_questions.md)
- [Week 6：综合验收、故障诊断与产品级差距](interview/week6_system_debug_questions.md)
- [Week 1–3 算法问答](interview/isp_algorithm_questions_week1_3.md)
- [Week 1–4 深度笔记](interview/isp_interview_deep_notes_week1_4.md)

历史报告和全量图片是参考答案，不是学习完成证明。完成标准仍然是：能在陌生 DNG 上独立预测、实现、测试、解释失败并留下可复核证据。
