# 调试挑战

为自己的简化 Pipeline 依次注入下列错误，不看现成报告定位：

1. 将 RGGB 错写成 BGGR；
2. 在 `uint16` 上直接做可能为负的减法；
3. 把 RGB 保存成 BGR；
4. 将 Gamma 放到 AWB/CCM 之前；
5. 将 `rgb @ ccm.T` 改成 `rgb @ ccm`；
6. 候选图和 reference 使用不同 orientation。

每题提交：

- 现象截图或数值；
- 最小复现；
- 根因；
- 修复；
- 防止复发的测试。
