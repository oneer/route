# 阶段二独立练习

这里的文件故意不提供完整答案。建议复制到个人分支或临时目录后完成，不要直接查看
`stage2_ai_isp/ai_isp/` 中的正式实现。

练习不是附录，而是正式学习路线的一部分：基础题放在 Week 1 后，Dataset/训练循环/指标
骨架分别放在 Week 2/3/4 后，Debug 放在 Week 8 后，Capstone 放在 Week 12 后。

验收顺序：

1. 先运行现有测试，确认基线正常。
2. 完成 skeleton 中的 `NotImplementedError`。
3. 为自己的实现补测试。
4. 最后才允许和正式实现逐行比较。

每个练习的可观察行为、建议测试和评分方式见
[`acceptance_rubric.md`](acceptance_rubric.md)。它只描述验收契约，不提供实现答案。

建议节奏：

| 练习 | 建议范围 | 完成证据 |
|---|---|---|
| 01 基础题 | 闭卷解释 | 每题关联一个项目文件或实验 |
| 02 Dataset | 单文件实现 + 测试 | paired/crop/shape/错误输入测试 |
| 03 Training loop | 两个函数 + 测试 | 参数更新、无梯度验证、模式恢复 |
| 04 Metrics | PSNR + 协议解释 | 已知数值、shape 和边界测试 |
| 05 Debug | 逐项诊断 | 症状→定位→根因→修复→预防测试 |
| 06 Capstone | 四个里程碑 | 独立仓库、测试、报告和部署证据 |

完成 `06_capstone_spec.md` 前，不应声称“能够独立实现阶段二核心功能”。
