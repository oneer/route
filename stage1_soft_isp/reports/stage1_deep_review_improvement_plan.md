# Stage 1 ISP 学习报告深度复盘与改进计划

> 状态说明：这是历史改进计划，用来保留当时发现问题的推理过程。部分项目已由 Week 6、`feasible_raw_quality_audit.md` 和后续测试完成；当前完成状态以 `stage1_tutorial_audit.md` 为准，不应把本文件中的“待补”直接当成现状。

这份文档用于承接对 Stage 1 Soft-ISP 报告的深度审阅意见。它不是替代原来的 Week1-Week6 报告，而是把现有报告从“能跑通、能解释”继续推进到“能量化、能验证、能接近产品级思维”的改进清单。

## 0. 总体判断

当前 Stage 1 已经完成一条可解释 Soft-ISP 主链路：

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma -> sRGB Preview
```

报告的优点是：

- 主 pipeline 完整；
- 每个模块有代码、图像、JSON 和 Markdown 记录；
- 能说明学习版和产品级 ISP 的差距；
- 已经引入 OpenISP 作为工程参考；
- Week6 已经补过一轮 DPC、LSC、Demosaic、AWB、CCM、Tone 和 ROI IQA 短板。

但如果目标是更扎实的技术报告或面试作品集，目前仍有四类主要不足：

| 问题 | 当前表现 | 改进方向 |
|---|---|---|
| 理论深度不足 | 多数模块给出公式和现象，但推导、假设边界较少 | 增加数学原理和失败条件 |
| 实验验证不充分 | 很多验证依赖全图平均指标或 rawpy reference | 加入局部 crop、参数扫描、标准数据 |
| 产品级标定缺失 | LSC、CCM、AWB 仍缺真实 flat-field / ColorChecker | 增加真实标定流程和数据需求 |
| 质量评价体系偏弱 | PSNR/SSIM/MAD 解释力有限 | 增加 DeltaE、ROI IQA、主观标签和失败模式分类 |

## 1. Week 1：RAW 统计分析补强

### 当前覆盖

Week1 已经覆盖：

- 14 张 DNG 的 metadata；
- black level / white level；
- Bayer pattern；
- 四通道均值和 histogram；
- 暗部、中间调、高光 ROI 分析。

### 主要缺口

| 缺口 | 当前问题 | 优先级 |
|---|---|---|
| Sensor 差异分析 | 多相机样张被放在一起统计，但没有展开 sensor 差异 | 中 |
| 噪声模型分析 | 只有均值/标准差，缺少 read noise、shot noise、dark noise 解释 | 高 |
| 动态范围估计 | 没有把 white level、black level、noise floor 连接成 DR | 中 |
| ROI 选择透明度 | 自动 ROI 有图，但选择标准和失败情况还可以更明确 | 中 |

### 建议新增章节

#### 1.1 Sensor metadata 对比表

建议在 Week1 增加一张表：

| 样张 | 相机/机型 | ISO | black level | white level | Bayer pattern | 预期噪声风险 |
|---|---|---:|---:|---:|---|---|
| T01 | 待从 DNG metadata 读取 | 待填写 | 待填写 | 待填写 | 待填写 | 待分析 |

说明重点：

```text
不同相机、ISO、white level 和 black level 不一定可直接横向比较。
RAW 统计值先是“这张图的传感器状态”，再是“场景亮度状态”。
```

#### 1.2 噪声模型分析

建议补充三类噪声：

| 噪声 | 直觉 | 可做实验 |
|---|---|---|
| read noise | 读出电路带来的底噪 | 暗部 ROI 标准差估计 |
| shot noise | 光子计数带来的信号相关噪声 | 不同亮度 ROI 的 mean/std 曲线 |
| quantization noise | ADC 量化误差 | 结合 bit depth 估算理论下限 |

最小可落地版本：

```text
按亮度分桶统计每个 bin 的 mean 和 std。
如果 std 随 mean 上升，说明噪声具有 signal-dependent 特征。
```

#### 1.3 动态范围估计

建议增加近似公式：

```text
usable_signal = white_level - black_level
noise_floor ≈ dark_roi_std
DR_dB = 20 * log10(usable_signal / noise_floor)
```

注意写清楚限制：

```text
这是学习用近似 DR，不等于厂商实验室标定的 sensor DR。
没有真正 dark frame 时，dark ROI 会混入场景纹理和欠曝结构。
```

#### 1.4 ROI 选择算法说明

需要讲清楚：

- dark ROI 怎么选；
- highlight ROI 如何避开饱和；
- texture ROI 是否基于梯度；
- 自动 ROI 失败时怎么看。

## 2. Week 2：BLC / DPC / LSC 补强

### 当前覆盖

Week2 已经覆盖：

- BLC 公式和前后 histogram；
- DPC 动态坏点检测、mask overlay、repair crop；
- 学习用径向 LSC；
- Week6 增加了 static defect map、synthetic flat-field 和 mesh LSC。

### 主要缺口

| 缺口 | 当前问题 | 优先级 |
|---|---|---|
| DPC 定量验证 | 有局部 crop，但缺少注入已知坏点的 recall / precision | 高 |
| DPC 参数敏感性 | `mad_k`、阈值变化未系统扫描 | 中 |
| BLC 误差传播 | black level 扣错对 DPC/AWB/暗部的影响未量化 | 中 |
| 真实 LSC 标定 | Week6 是 synthetic flat-field，不是真实标定 | 高 |

### 建议新增实验

#### 2.1 BLC 误差传播

在同一张 RAW 上测试：

```text
black_level + (-10, 0, +10)
```

观察：

| 项目 | 观察 |
|---|---|
| 暗部 histogram | 是否左移、clip 或发灰 |
| DPC 检测点数 | 阈值是否被噪声分布影响 |
| AWB gain | 黑位错误是否改变通道均值 |
| 最终 sRGB | 暗部是否偏色或压死 |

#### 2.2 DPC 参数扫描

建议新增表：

| `mad_k` | 检测点数 | 注入坏点召回率 | 误检风险 | 结论 |
|---:|---:|---:|---|---|
| 1.0 | 待填写 | 待填写 | 高 | 过敏感 |
| 2.0 | 待填写 | 待填写 | 中 | 候选 |
| 3.0 | 待填写 | 待填写 | 低 | 可能漏检 |

最可靠做法是注入人工坏点：

```text
选择若干非边缘像素 -> 人为置 0 或 white_level -> 跑 DPC -> 看是否找回。
```

#### 2.3 真实 LSC 标定流程

报告中要明确区分：

```text
当前径向/合成 flat-field LSC：学习用。
产品级 LSC：来自真实 flat-field 标定。
```

真实流程：

1. 使用积分球或均匀光源拍 flat-field；
2. 多帧平均降低噪声；
3. 分 Bayer 四通道估计 gain；
4. 生成 mesh LUT；
5. 插值到全图；
6. 验证中心、边缘、四角残差。

目标可以写成：

```text
flat-field 校正后，中心到边缘亮度残差尽量低于 2%-5%。
```

## 3. Week 3：Demosaic / AWB 补强

### 当前覆盖

Week3 已经覆盖：

- bilinear demosaic；
- Gray World AWB；
- R/G、B/G 比值；
- rawpy / OpenCV / edge-aware 方向性对比。

### 主要缺口

| 缺口 | 当前问题 | 优先级 |
|---|---|---|
| Demosaic 伪影分析 | 假彩、拉链、摩尔纹没有独立局部分析框架 | 高 |
| AWB 定量评估 | 只靠 R/G、B/G 接近 1 不够 | 高 |
| Gray World 失败案例 | 大面积单色、混合光源案例需要更具体 | 中 |
| 高频细节评估 | 暂无 MTF 或边缘响应分析 | 中 |

### 建议新增章节

#### 3.1 Demosaic 伪影检查表

| 伪影 | 典型位置 | 检查方法 | 视觉现象 |
|---|---|---|---|
| zipper effect | 高对比斜边 | 放大 crop / 边缘剖面 | 边缘锯齿或拉链纹 |
| false color | 黑白细纹、树枝 | 色度变化图 | 无色区域出现彩色边 |
| moire | 细密重复纹理 | 频谱或局部 crop | 彩色波纹 |
| blur | 细节区域 | 与 rawpy/OpenCV 对比 | 高频细节丢失 |

#### 3.2 AWB 评估升级

R/G、B/G 只能回答：

```text
全图平均是否接近灰。
```

它不能回答：

```text
中性灰是否真的中性；
肤色是否自然；
大面积绿色/蓝色是否误导 AWB。
```

建议补充：

- gray ROI 上的 R/G、B/G；
- 如果有色卡，计算中性灰 patch DeltaE；
- 按场景记录 Gray World 失败原因。

#### 3.3 Gray World 失败案例库

| 场景 | 失败原因 | 预期表现 | 改进方向 |
|---|---|---|---|
| 大面积绿色 | 全图均值被绿色主导 | R/B gain 被错误拉高 | gray point / ROI AWB |
| 大面积蓝天 | 蓝色占比过大 | R gain 可能过高 | 排除高饱和区域 |
| 混合光源 | 单一 gain 无法解释局部光源 | 局部偏色 | 多区域 AWB / 时序策略 |

## 4. Week 4：CCM / Gamma / Tone Mapping 补强

### 当前覆盖

Week4 已经覆盖：

- 3x3 CCM；
- Gamma power law；
- Reinhard tone mapping；
- Week6 sRGB OETF / S-curve 对比；
- 相对 rawpy 的 Lab / DeltaE 学习版指标。

### 主要缺口

| 缺口 | 当前问题 | 优先级 |
|---|---|---|
| CCM 来源 | 不是 ColorChecker 标定矩阵 | 高 |
| DeltaE 标准性 | 当前主要相对 rawpy reference，不是标准色卡 Lab | 高 |
| Gamma 曲线解释 | 已有 sRGB OETF，但可以更明确和 power law 对比 | 中 |
| 色域外处理 | CCM 后 clip / soft clip / hue preserving 未展开 | 中 |

### 建议新增章节

#### 4.1 CCM 标定原理

标准 CCM 标定流程：

1. 标准光源下拍 ColorChecker；
2. 提取 24 个色块线性 RGB；
3. 获取标准色块 XYZ / Lab / sRGB；
4. 用最小二乘拟合 3x3 矩阵；
5. 验证 DeltaE。

学习版报告里要明确：

```text
当前 CCM 是 metadata / rawpy 方向性对齐，不等于产品级色卡标定。
```

#### 4.2 Gamma 与 sRGB OETF 对比

建议放一张表：

| 曲线 | 公式 | 用途 | 风险 |
|---|---|---|---|
| Power 1/2.2 | `V_out = V_in^(1/2.2)` | 简单显示编码 | 暗部和 sRGB 标准有差异 |
| sRGB OETF | 分段函数 | 标准 sRGB 输出 | 实现稍复杂 |
| S-curve LUT | 查表 | 风格化 tone | 需要 tuning |

#### 4.3 色域外处理

需要说明：

- 直接 clip 到 `[0, 1]` 会丢色彩层次；
- soft clipping 可以减少硬截断；
- hue preserving compression 可以尽量保持色相。

## 5. Week 5：IQA / 消融实验补强

### 当前覆盖

Week5 已经覆盖：

- PSNR；
- SSIM；
- Mean Abs Diff；
- 模块开关消融；
- rawpy reference 局限性讨论。

### 主要缺口

| 缺口 | 当前问题 | 优先级 |
|---|---|---|
| 指标解释力 | 全图 PSNR/SSIM 对稀疏坏点、局部假彩不敏感 | 高 |
| rawpy reference | rawpy 不是 ground truth | 高 |
| 参数消融 | 主要是模块开关，参数扫描较少 | 中 |
| 局部质量 | 自动 ROI 有了，但语义 ROI 还不够 | 中 |

### 建议新增评价框架

#### 5.1 局部 IQA

建议将 ROI 固定为：

```text
center / corner / dark / highlight / texture / skin / sky / edge
```

每个 ROI 记录：

| ROI | PSNR | SSIM | MAD | 主观标签 | 备注 |
|---|---:|---:|---:|---|---|
| dark | 待填写 | 待填写 | 待填写 | noise / color shift | 待填写 |

#### 5.2 主观评价量表

| 维度 | 评分关注 | 权重建议 |
|---|---|---:|
| 颜色准确性 | 中性灰、肤色、天空是否自然 | 30% |
| 细节清晰度 | 边缘、纹理是否糊 | 25% |
| 噪声控制 | 暗部是否干净 | 20% |
| 伪影抑制 | 假彩、拉链、摩尔纹、halo | 15% |
| 整体观感 | 是否自然、是否过度处理 | 10% |

#### 5.3 参数敏感性

建议从少量参数开始：

| 参数 | 扫描范围 | 观察指标 |
|---|---|---|
| DPC `mad_k` | 1.0 / 2.0 / 3.0 / 4.0 | 检测点数、误检、修复 crop |
| LSC gain strength | 0.5 / 0.75 / 1.0 | 角落亮度、噪声放大 |
| tone strength | 多档曲线 | 高光保留、整体灰度 |

## 6. Week 6：补短板实验再升级

### 当前覆盖

Week6 已经补了很多短板：

- static / dynamic DPC；
- synthetic flat-field mesh LSC；
- bilinear / OpenCV / edge-aware demosaic；
- gray world / white patch / gray ROI AWB；
- CCM DeltaE 学习版评估；
- sRGB OETF / S-curve；
- ROI IQA 和主观标签。

### 仍需说明的限制

| 限制 | 为什么重要 | 下一步 |
|---|---|---|
| synthetic flat-field | 不能替代真实镜头/传感器 shading | 拍真实 flat-field |
| DeltaE 相对 rawpy | rawpy 不是标准颜色真值 | 拍 ColorChecker |
| 自动 ROI 标签 | 标签标准仍偏学习版 | 人工固定语义 ROI |
| 无时序稳定性 | 视频 ISP 需要 AWB/DPC/tone 稳定 | 后续做 burst/video |
| 无性能基准 | 产品级 ISP 关注时延和内存 | 增加 per-module timing |

## 7. 跨周共性改进

### 7.1 降低 rawpy reference 依赖

rawpy 适合做方向性参考，但不是 ground truth。

建议后续参考体系变成：

| 参考类型 | 用途 |
|---|---|
| rawpy / LibRaw | 对照成熟 pipeline 的趋势 |
| OpenCV / OpenISP | 对照具体算法模块 |
| ColorChecker | 颜色准确性 ground truth |
| flat-field | LSC ground truth |
| 主观评分 | 最终观感判断 |

### 7.2 补产品级差距表

建议每个模块加一张表：

| 模块 | 学习版 | 产品级 | 差距 |
|---|---|---|---|
| DPC | 动态同色邻域 | 工厂 defect map + 动态保护 | 误检/漏检控制 |
| LSC | 径向/合成 mesh | 真实 flat-field per-channel mesh LUT | 标定真实性 |
| Demosaic | bilinear / OpenCV edge-aware | Malvar / AHD / proprietary | 高频伪影控制 |
| AWB | gray world / gray ROI | 灰点、肤色、色温、时序 | 鲁棒性 |
| CCM | metadata 近似 | ColorChecker 标定 | DeltaE |
| Tone | Reinhard / S-curve | 场景自适应 tone | 高光和风格 |

### 7.3 增加复现指南

每个实验报告建议固定包含：

```text
输入文件
运行命令
输出图像
输出 JSON
评价指标
局限性
下一步
```

### 7.4 增加 100% crop 证据

每个关键模块至少保留三类局部图：

- 暗部；
- 高光；
- 高频纹理或边缘；
- 如果是 DPC，再加坏点修复 crop；
- 如果是 Demosaic，再加假彩/拉链 crop；
- 如果是 AWB/CCM，再加中性灰/肤色/天空 crop。

## 8. 优先级路线图

### 高优先级

1. **ColorChecker CCM / DeltaE。** 获取标准色卡图，做 24 色块 Lab / DeltaE。
2. **DPC 注入坏点验证。** 人工注入 hot/dead pixel，计算召回和误检。
3. **真实 flat-field LSC。** 用真实白场图生成 per-channel mesh LUT。

### 中优先级

4. **Demosaic 伪影库。** 建立 zipper / false color / moire crop。
5. **AWB 失败案例库。** 大面积绿色、蓝天、混合光源、低光。
6. **语义 ROI IQA。** 手动固定 skin / sky / dark / highlight / texture。

### 低优先级

7. per-module runtime / memory benchmark；
8. AWB / tone 时序稳定性；
9. HDR / WCG 扩展讨论。

## 9. 最小落地顺序

为了避免改进范围过大，建议按下面顺序推进：

```text
Step 1: 先写清楚每周报告的“当前限制”和“下一步实验”
Step 2: 新增 DPC 注入坏点参数扫描
Step 3: 新增 Demosaic 伪影 crop 分析
Step 4: 新增 Gamma vs sRGB OETF 曲线说明
Step 5: 等真实标定数据到位后，再做 ColorChecker 和 flat-field
```

其中 Step 1 可以立即完成；Step 2-4 依赖现有数据和代码，大概率也能完成；Step 5 需要额外拍摄或准备标准数据。

## 10. 总结

当前 Stage 1 已经达到“可解释学习版 Soft-ISP”的标准，但如果继续向更扎实的技术文档靠近，重点不应该是盲目增加模块，而是补三件事：

```text
标准数据：ColorChecker / flat-field / defect map
局部证据：100% crop / 语义 ROI / 失败案例
量化方法：DeltaE / 参数扫描 / 置信区间 / 主观评分
```

真正的下一阶段目标是：

```text
从“我知道这个模块怎么写”
推进到
“我知道这个模块什么时候有效、什么时候失败、怎么标定、怎么量化”。
```
