# 阶段二练习验收 Rubric

本文件只给出行为契约和评分方式，不给出完整实现。先完成练习和自己的测试，再对照
`stage2_ai_isp/ai_isp/` 正式实现。

## 通用评分

每项按0～2分评分：

- 0分：没有实现，或只能在单个示例上偶然运行；
- 1分：正常输入可用，但缺少边界验证、测试或解释；
- 2分：正常与错误输入都有测试，行为可解释，能指出结果边界。

每个练习至少达到80%才进入下一项。代码能运行但无法解释，只按1分计。

## 01 基础理解题

检查四类能力：训练/验证边界、shape/感受野、residual 语义、数据与评估泄漏。每个回答
至少包含“一句话结论、一个原因、一个本项目证据”。只背定义、不关联项目，不能满分。

## 02 Paired Dataset

必须验证：

1. 只配对 noisy/clean 同名图像，空交集时给出明确异常；
2. 输出为 RGB、float32、CHW、`[0,1]`；
3. noisy 和 clean 使用完全相同的 crop 坐标；
4. 同 seed/index 重复读取结果一致；
5. 尺寸不一致、图片小于 patch、文件损坏时失败信息可定位。

最低测试集：正常 pair、同图恒等 pair、错配文件名、shape mismatch、过小图片。

## 03 Training Loop

必须验证：

1. `train_step` 清旧梯度、前向、loss、反向、更新，并返回 Python `float`；
2. 至少一个参数在训练 step 后改变；
3. `validate_step` 不创建新梯度，并把输出 clamp 到 `[0,1]`；
4. 验证结束后恢复调用前的 train/eval 状态；
5. 输入输出 shape 一致。

把 `optimizer.step()` 放进 validation 是直接不通过项，因为它破坏评估边界。

## 04 Metrics

PSNR 在值域 `[0,1]` 下使用：

```text
PSNR = 10 * log10(1 / MSE)
```

必须验证：

- MSE=`0.01` 时 PSNR=`20 dB`；
- 恒等输入在 `eps=1e-8` 时接近 `80 dB`；
- 返回每个 batch 样本一个值；
- shape 不一致时主动报错；
- 能解释 RGB/Y、border crop、量化和值域为什么会改变 benchmark 数值。

## 05 Debug

每个问题使用同一模板：

```text
症状 -> 最小复现 -> 检查证据 -> 根因 -> 最小修复 -> 防回归测试
```

不能只写“改回来”或“换模型”。满分答案必须说明为什么该错误会产生对应症状，以及哪个
自动化测试可以在训练前阻止它。

## 06 Capstone

按 `06_capstone_spec.md` 的四个里程碑验收。总分建议分配：

| 部分 | 权重 |
|---|---:|
| Dataset、split 和防泄漏 | 25% |
| 模型、训练和 checkpoint | 25% |
| 指标、可视化和消融 | 25% |
| 测试、ONNX 对齐和报告边界 | 25% |

以下任一情况不能通过：test 被用于调参、paired crop 不同步、没有 noisy baseline、只提交
ONNX 文件而没有数值对齐、把 pseudo RAW 写成真实 sensor RAW。
