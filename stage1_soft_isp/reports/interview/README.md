# Stage 1 分周面试题导航

这组题库按阶段一六周学习路径组织。每题都按同一思路回答：

1. **先下定义：** 说明对象、输入输出和所在数据域。
2. **再讲原因：** 说明物理来源、数学假设或工程约束。
3. **指出错误后果：** 说明做错后会出现什么数值异常或画质现象。
4. **给出验证方法：** 关联本项目中的测试、统计、局部 crop、参数实验或失败案例。
5. **限定证据边界：** 区分学习版 baseline、仓库实测和产品级结论。

## 分周题库

| 周次 | 主题 | 题库 |
|---|---|---|
| Week 1 | RAW、DNG metadata、Bayer、Histogram、ROI | [Week 1 面试题](week1_raw_sensor_questions.md) |
| Week 2 | BLC、DPC、LSC 与 RAW 前端校正 | [Week 2 面试题](week2_frontend_correction_questions.md) |
| Week 3 | Demosaic、AWB 与线性 RGB | [Week 3 面试题](week3_demosaic_awb_questions.md) |
| Week 4 | CCM、Tone Mapping、Gamma 与显示编码 | [Week 4 面试题](week4_color_tone_questions.md) |
| Week 5 | IQA、消融、ROI 与参数评价 | [Week 5 面试题](week5_iqa_ablation_questions.md) |
| Week 6 | 综合验收、故障诊断与产品级差距 | [Week 6 面试题](week6_system_debug_questions.md) |

原有 [Week 1–3 综合题库](isp_algorithm_questions_week1_3.md) 和 [Week 1–4 深度复盘](isp_interview_deep_notes_week1_4.md) 保留作为跨模块追问材料。分周题库用于按学习进度复习，综合题库用于模拟完整面试。

## 推荐练习方式

- 第一轮：只看题目，口述 60–90 秒答案。
- 第二轮：补充“错了会怎样”和“怎么验证”。
- 第三轮：把答案落到本项目的文件、参数、图表和测试。
- 最后一轮：压缩成一句定义、三点主体和一句边界声明，避免背诵长文。
