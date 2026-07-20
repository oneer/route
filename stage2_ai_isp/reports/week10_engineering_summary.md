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

### 1.1 在阶段流程中的位置与代码导航

Week 9 交付多个候选实验和 failure 证据；本周选择一个**设计版本**并封存其全部合同；
Week 11 只允许导出这一个冻结对象。这里的“冻结”不是把文件设为只读，而是停止使用 test
反馈修改选择过程。

```text
configs/*.yaml + runs/*/metrics.csv
  -> scripts/13_export_engineering_summary.py（候选质量/成本汇总）
  -> 人工写冻结理由与 checkpoint rule
  -> scripts/22_evaluate_test_set.py（held-out test）
  -> test_set_metrics.json/csv + frozen tensor contract
  -> deployment/export_onnx.py（Week 11）
```

冻结输入合同为 NCHW、RGB、`float32 [0,1]`；当前数据是 SIDD tiny paired sRGB。若后来
改变 resize、颜色顺序、metric 或 checkpoint，即使模型权重没变，也已经是另一个实验版本。

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

## 7. 冻结设计关键词与参数表

| 关键词/参数 | 定义 | 为什么现在冻结 | 违规后果 |
|---|---|---|---|
| validation | 用于 checkpoint/设计选择的未训练数据 | 允许做有限模型选择 | 反复调到 validation 会过拟合选择过程 |
| held-out test | 设计冻结后只做最终验收的数据 | 提供相对独立的泛化估计 | 看 test 后改设计再复用会泄漏 |
| checkpoint rule | 例如 validation PSNR 最优 | 明确为什么选择这组权重 | 事后挑最有利 checkpoint 产生偏差 |
| params | 可训练参数数量 | 近似权重规模的一部分 | 不能推出 activation memory 或 latency |
| checkpoint MB | 序列化文件大小 | 验证实际交付物体积 | 可能包含 optimizer/metadata，不等于纯权重 |
| frozen tensor contract | NCHW、RGB、float32、`[0,1]` | 为 ONNX/C++ 提供唯一接口 | 后端对齐失败时无法判断模型还是预处理问题 |

## 8. Week 10 面试五问

1. validation 与 held-out test 的职责为什么不同？
2. test 后发现问题还能不能修改模型，怎样建立新的合法验收集？
3. 参数量、checkpoint 大小、FLOPs、峰值内存和 latency 各回答什么问题？
4. 为什么冻结时必须记录指标实现版本和 data manifest？
5. 当前 37.0044 dB/0.91110 能支持什么结论，不能支持什么跨数据集或量产结论？

## 9. 冻结到部署的流程

```text
validation 选设计
  -> 写冻结理由和 checkpoint rule
  -> 固定 tensor/metric contract
  -> held-out test 一次
  -> 锁定 checkpoint hash
  -> 交给 Week 11 ONNX 导出
```

## 10. 设计冻结参数卡与失败处理

| 项目 | 冻结内容 | 为什么 | 改变后怎样处理 |
|---|---|---|---|
| data manifest/split | 文件 identity 与 source scene 分组 | 排除样本集合漂移/泄漏 | 创建新版本并重新验证，不能沿用旧 test 结论 |
| metric implementation | range、window、边界与聚合方式 | 数值依赖实现 | 新旧结果分表，不直接拼榜 |
| checkpoint rule | validation PSNR 最优 | 防止事后挑权重 | test 前改规则并记录；test 后改则建立新 test |
| tensor contract | RGB/NCHW/FP32/`[0,1]`/动态 H,W | 后端对齐的共同语言 | 重新导出并全链路回归 |
| success threshold | 对齐误差、质量下降和 latency 口径 | 防止看结果后移动门槛 | 失败则记录，不得事后放宽冒充通过 |

如果 test 失败，先保存结果并分类：实现 bug 可以修复后以明确版本重验；设计泛化失败则回到
train/validation，建立新的冻结版本和从未查看的新 test。不能删除不利 test 记录继续报告原
协议。系统权衡来自质量、文件大小、速度和内存互相制约：更大模型可能提高质量，却增加权重/activation
和 latency；因此 engineering summary 必须并列这些轴，而非压成一个“最好”。

证据等级：当前 held-out 结果为 `verified_public` tiny sRGB；冻结/工程汇总为
`verified_partial` 工程流程。它不证明跨设备泛化或端侧可部署性。

## 11. 学习验收与面试追问路径

- 独立写一份不超过一页的 freeze card，包含 manifest/config/commit/seed/checkpoint hash、
  metric version、tensor contract、成功阈值和时间戳。
- 故意改为 BGR 或不同 metric window，说明为何它不是“同一模型的同一次验证”。
- 从参数量估算纯 FP32 权重下界，再解释 checkpoint 与运行时内存为何可能更大。
- 闭卷回答：概念题讲 freeze；原理题讲 test selection bias；参数题讲 threshold/hash；
  调试题讲 test 失败分流；系统题讲质量—内存—latency 取舍。

## 12. 高通岗位补强：从离线模型到 Camera Feature

模型在 SIDD tiny 上提升 PSNR，只回答“固定公开 sRGB 分布上的 restoration 是否有效”；Camera feature 还必须回答何时启用、何时拒绝、如何回退、连续帧是否稳定，以及性能/内存/功耗预算是否允许。这个层次比继续堆网络更接近 ISP Algorithm/System 岗位。

### 12.1 Feature 决策链

```text
camera metadata / scene statistics / input tensor
  -> domain & integrity checks
  -> scene gate（照度、噪声、运动、饱和、纹理、脸部等）
  -> traditional / ML / bypass 路径选择
  -> inference + artifact/confidence check
  -> accept output 或 fallback
  -> temporal smoothing / downstream ISP
  -> telemetry + regression case
```

gate 不是为了“让测试集分数更好看”，而是把模型的训练域和已知 failure 转成可执行的准入条件。例如 motion 高、输入 range 错、极端 clipping、模型输出越界或 runtime 超时，都可能触发传统路径或 bypass。当前仓库已经有 traditional-vs-ML 同输入对比和 failure taxonomy，但没有实现真实 Camera runtime gate。

### 12.2 评价必须从单张均值升级为场景矩阵

| 维度 | 至少分组 | 观察指标 | 典型风险 |
|---|---|---|---|
| 亮度/噪声 | bright、normal、dark；低/高噪声 | PSNR/SSIM、dark ROI、residual noise | 暗部过平滑、颜色漂移 |
| 纹理 | flat、edge、fine texture、text | edge/texture retention、crop MAE | 蜡感、文字断裂、伪纹理 |
| 动态范围 | normal、highlight clipping、backlight | clipping、local contrast、halo | 高光偏色、halo |
| 内容 | skin/face、foliage、repeating pattern | 语义 ROI 与人工标签 | 肤质异常、纹理幻觉 |
| 运动/时序 | static、pan、object motion、scene cut | flicker、ghost、recovery frames | 帧间亮度/纹理跳变 |
| 系统 | cold/warm/thermal、内存压力 | p50/p90、timeout、RSS/power | 降频或资源抢占造成回退 |

测试集应先冻结场景标签和接受门槛，再看最终结果。只有平均 gain 没有 worst bucket，会掩盖 feature 在少数关键场景的灾难性退化。

### 12.3 Accept、reject 与 fallback

一个项目级决策可以写成多约束而非单指标：

```text
accept = quality_gain >= Q_min
     and worst_bucket_drop <= D_max
     and latency_p90 <= L_budget
     and memory_peak <= M_budget
     and no_critical_artifact
```

`Q_min/D_max/L_budget/M_budget` 是产品和项目预算，不是行业统一常数。fallback 还要定义切换迟滞，避免 traditional/ML 在连续帧间来回跳变；输出域、颜色、锐度和噪声风格也要匹配，否则路径切换本身会形成 flicker。

常见 failure 定位顺序：先查输入合同和 scene/domain，再查 checkpoint/precision/backend，随后检查模型 artifact，最后才调整 gate。不能把 layout bug 用“低置信回退”掩盖，也不能依据 test failure 事后移动门槛。

### 12.4 发布、监控与回滚证据

即使个人项目没有真实客户，也可以按工程流程回答：冻结模型和 manifest hash；保存 per-scene 指标与 worst crop；建立旧版/新版 A-B；把关键 failure 固定为 regression；定义超时、内存、输出越界和质量 reject；保留可复现的回滚版本。商业客户支持、线上 telemetry 和量产签核仍属于工作经历缺口，不能用这套设计冒充。

### 12.5 面试练习

1. 为什么 SIDD PSNR 提升不能直接决定 Camera feature 上线？
2. 如何从 failure taxonomy 推导 scene gate，而不是凭感觉写阈值？
3. traditional 与 ML 切换为什么需要输出风格匹配和 temporal hysteresis？
4. 如果平均质量提高但肤色 bucket 退化，怎样做 accept/reject 和下一实验？
5. INT8 latency 更快但最差 ROI 变差时，怎样联合精度、性能和 fallback 决策？
6. runtime timeout、OOM、NaN、backend fallback 分别应该怎样回退和留证？

当前可验证证据见[Camera scene ML evaluation](camera_scene_ml_evaluation.md)和[Traditional vs ML trade-off](traditional_vs_ml_tradeoff.md)。它们是公开冻结 sRGB 的离线比较；真实 Camera scene gate、视频时序、肤色专项、线上回退和 Snapdragon feature integration 均为 `not_run`。
