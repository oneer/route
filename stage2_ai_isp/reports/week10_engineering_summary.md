# Week 10：Engineering Summary 与冻结设计

Week 10 的目标是把“模型指标不错”升级成“实验对象、质量、模型成本和证据边界都说得清”。
本周不继续调模型，而是冻结设计，为 held-out test 和部署导出建立唯一输入。

## 1. 输入、处理与输出

```text
输入：已完成的 config、run、checkpoint、validation CSV 和图像
处理：核对实验协议，汇总质量与模型成本，选择并冻结一个 checkpoint
输出：engineering summary、冻结理由、held-out test 结果和部署输入
```

本周使用的自动汇总脚本：

```powershell
python stage2_ai_isp/scripts/13_export_engineering_summary.py
```

主要输出：

```text
stage2_ai_isp/reports/stage2_engineering_summary.md
stage2_ai_isp/reports/figures/week10_engineering_summary/stage2_engineering_summary.csv
```

## 2. 为什么必须先冻结设计

Validation 可以用于选择 checkpoint 和设计；test 只能在方案冻结后使用。如果看完 test
结果又修改 loss、模型或步数，再次把同一 test 当最终成绩，就相当于间接在 test 上调参。

正确顺序：

```text
train -> validation 选设计 -> 写下冻结理由 -> test 一次 -> 不再回头调参
```

冻结记录至少包含：

- 数据 manifest 与 split audit；
- config 路径、git commit、seed 和设备；
- checkpoint 路径及选择规则；
- 指标实现版本；
- test 前已经确定的成功标准。

## 3. 工程表应该怎么读

质量和成本回答不同问题：

| 字段 | 回答的问题 | 不能单独证明 |
|---|---|---|
| PSNR/SSIM | 当前协议下恢复质量如何 | 主观画质、跨数据集泛化 |
| Params | 模型有多少可训练参数 | 实际 latency、峰值内存 |
| Checkpoint MB | 权重文件有多大 | 运行时内存、算力 |
| Channels | 输入协议是 RGB 还是 RAW-like | 数据是否是真实 sensor RAW |
| Latency | 指定 backend/shape/线程下多快 | 其他设备或量产平台性能 |

参数量和 checkpoint 大小相关，但不相等。以 float32 权重为例，理论权重大小约为：

```text
weight_bytes ~= parameter_count * 4
```

例如 29,507 个参数的纯 float32 权重约为 `29,507 × 4 = 118,028 bytes`。实际
checkpoint 还可能包含 optimizer、step 和元数据，所以必须测文件，而不是只用公式猜。

## 4. 当前冻结结果

当前冻结的 DnCNN L2 checkpoint 在20张 held-out full-image test pairs 上得到：

| 指标 | 结果 |
|---|---:|
| PSNR | 37.0044 dB |
| SSIM | 0.91110 |

运行方式：

```powershell
python stage2_ai_isp/scripts/22_evaluate_test_set.py `
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml `
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth
```

这只证明该冻结模型在当前 tiny split 和当前指标协议下的结果。历史 validation 使用过早期
SSIM 实现，不能与当前 test SSIM 拼成一张无条件排行榜。

## 5. 常见误区

1. 参数少就一定快：算子、shape、内存访问、线程和 backend 都会影响速度。
2. checkpoint 小就能上手机：还缺运行时内存、算子支持、功耗、量化和稳定性验证。
3. test 比 validation 高就是泄漏：tiny split 难度不同也可能造成差异，应先审计 scene。
4. 更复杂模型分数低就是结构差：当前历史 run 的 loss、步数和宽度并未完全统一。

## 6. 练习与验收

1. 不看现有总结，自己从3个 run 提取 params、checkpoint MB、PSNR 和 SSIM；
2. 写一段不超过100字的冻结理由；
3. 指出表中哪些比较公平、哪些只能视为历史观察；
4. 解释 test 为什么只能在冻结后使用；
5. 给出下一周 ONNX 对齐的数值验收阈值，并说明理由。

通过标准：能同时解释质量、模型成本、协议限制和冻结纪律，并且不会把 params、文件大小、
latency 和端侧可部署性混为一谈。
