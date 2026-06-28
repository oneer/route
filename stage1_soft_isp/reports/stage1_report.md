# 阶段 1 实验报告

## 1. 项目目标

从真实 RAW / DNG 输入开始，实现并解释一个基础 Soft-ISP Pipeline。阶段 1 的目标不是复刻商业 ISP，而是建立可检查、可解释、可消融的数据流。

## 2. 当前完成度

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma -> sRGB Preview
```

仓库现有 14 张 MIT-Adobe FiveK DNG 的 RAW 统计、逐模块可视化、rawpy reference 对比、Week5 指标/消融和 Week6 局部综合实验。上述结论可追溯到 `reports/raw_stats/`、`reports/figures/*.json` 和对应脚本；证据索引见 [教程化审查与证据对应表](stage1_tutorial_audit.md)。

## 3. 样张说明

当前样张位于 `data/raw/`，编号为 T01-T14。它们覆盖室外、室内、低光、高动态范围、纹理/纯色等不同场景。参考输出位于 `data/references/`，用于方向性对比。

| 范围 | 文件 | 用途 |
|---|---|---|
| T01-T05 | 第一批入门样张 | 建立 RAW metadata、histogram、ROI 和基础模块直觉 |
| T06-T14 | 扩展样张 | 验证 pipeline 在更多曝光、色彩和 Bayer pattern 下能稳定运行 |

## 4. 模块实验

| 模块 | 输入 | 输出 | 核心参数 | 验证方法 | 失败场景 |
|---|---|---|---|---|---|
| BLC | Bayer RAW | Bayer RAW | black/white level | 暗部基线、histogram、identity case | black level 扣错导致黑位发灰或暗部 clip |
| DPC | BLC RAW | Bayer RAW | `min_delta`、`mad_k` | mask 稀疏性、crop 修复、Demosaic 前后伪影 | 高频纹理/高光边缘误检，真实坏点漏检 |
| LSC | DPC RAW | Bayer RAW | R/Gr/Gb/B gain map | 四角亮度、gain map、Week5 消融 | 未标定时误修真实场景亮度，边缘噪声放大 |
| Demosaic | Bayer RAW | linear RGB | Bayer pattern、插值核 | shape、结构恢复、rawpy 方向对比 | false color、zipper、边缘变糊 |
| AWB | linear RGB | linear RGB | R/G/B gain、统计百分位 | R/G 和 B/G 是否接近 1、前后对比 | 大面积纯色、混合光源、LSC 不准 |
| CCM | linear RGB | linear RGB | 3x3 matrix | rawpy reference 趋势、颜色关系变化 | 矩阵方向错、光源不匹配、缺色卡标定 |
| Tone/Gamma | linear RGB | sRGB preview | percentile、Reinhard、gamma | 中间调/高光观察、Week5 指标 | 高光压缩过度、整体偏灰、与 rawpy 曲线不一致 |

### 4.1 完整数据域

| 阶段 | shape / dtype | 范围与线性状态 | clip / 归一化 |
|---|---|---|---|
| DNG visible RAW | `(H,W)` / 通常 `uint16` | black level 到 white level，线性 Bayer 采样 | 未归一化 |
| BLC / DPC | `(H,W)` / `uint16` | 以 0 为黑位的线性 Bayer | BLC 减逐位置 black map 并 clip；DPC 只替换检测点 |
| 学习版 LSC | `(H,W)` / `float32` | gain 后线性 Bayer | 四通道径向 gain，按 white level 限制 |
| Demosaic / AWB / CCM | `(H,W,3)` / `float32` | 线性 RGB 码值尺度 | AWB/CCM 可能放大或产生越界，当前实现按 white level 限制 |
| Tone | `(H,W,3)` / `float32` | `0..1`，曲线前仍是线性量 | percentile 或 Reinhard 归一化 |
| Gamma / sRGB OETF | `(H,W,3)` / `float32` | `0..1`，非线性显示编码 | 最后量化为 `uint8` PNG |

更完整的逐模块约定见 [数据域总表](stage1_tutorial_audit.md#3-数据域总表)。

## 5. 与参考输出的主要差异

1. **Tone 曲线不同**：Week5 的 `gamma_only` 在该批样张上平均更接近 rawpy reference。它只说明当前 Reinhard 参数与 rawpy 渲染策略不同，不能反推出 rawpy 内部采用了哪条具体曲线。
2. **AWB 是全局 Gray World**：大面积单色或混合光源会使全局均值假设失效。部分样张关闭 AWB 反而更接近 rawpy reference，恰好说明“均值拉平”不等于颜色正确。
3. **CCM 没有色卡标定**：当前 CCM 来自 DNG/rawpy metadata 的简化使用，不等于标准光源下的 ColorChecker 拟合。
4. **LSC 是径向 baseline**：没有 flat-field 标定图时，LSC 不一定让全图更接近 rawpy；它主要用于理解位置和风险。
5. **Demosaic 是 bilinear**：边缘和高频纹理不如 rawpy/LibRaw 的高级算法，可能出现边缘糊、假彩色和拉链纹。

## 6. OpenISP 参考后的补充认识

引入 OpenISP 模块后，可以更清楚地看到当前项目的定位：Week1-4 已经覆盖了主干数据域转换，但还不是完整传统 ISP。OpenISP 里有 AAF、BNF、CNF、NLM、Malvar CFA、False Color Suppression、Edge Enhancement、Brightness/Contrast/Hue/Saturation 等模块，说明产品或教学完整 pipeline 还会包含更多 IQ 调参和伪影控制环节。

最值得吸收的点有三类：

1. **Demosaic 前的 RAW 域处理更多。** AAF 用同色低通抑制混叠；BNF/CNF/NLM 说明降噪不是只有坏点修复。
2. **Demosaic 可以升级。** 当前 bilinear 适合建立直觉，OpenISP 的 Malvar 插值可作为下一阶段对照。
3. **后处理也属于 ISP。** 假彩抑制、锐化、Gamma LUT、色相/饱和度/亮度/对比度控制都是最终图像风格和伪影控制的一部分。

详见 [OpenISP 模块参考笔记](openisp_reference_notes.md)。

## 7. 阶段复盘

阶段 1 已经从“能读 RAW”推进到“主链路有代码、图、JSON 和报告支撑”。但“仓库有证据”不等于“学习者已经掌握”；掌握必须由独立实现、测试、参数预测和陌生 DNG 毕业任务证明。

更细的模块掌握标准已经整理到 [ISP 模块掌握标准对照表](module_mastery_matrix.md)。这张表按“入门 / 掌握 / 面试可讲”检查 RAW、BLC、DPC、LSC、Demosaic、AWB、CCM、Gamma/Tone 和 IQA 的覆盖情况。此前标出的短板已集中放到 [Week6 阶段毕业实验报告](week6/mastery_gap_closure_report.md) 中串联，包括静态/动态 DPC、合成 flat-field / mesh LSC、OpenCV demosaic baseline、AWB white patch / gray ROI、相对 rawpy 的 CCM DeltaE、sRGB OETF / S-curve 和 ROI IQA。

当前仍然是学习版 pipeline。下一阶段如果继续向产品级靠近，优先顺序应是：真实 flat-field 标定版 LSC、ColorChecker CCM / DeltaE、Malvar/AHD Demosaic、RAW 域 AAF/BNF 消融、语义 ROI 主观评价、局部 tone、假彩抑制/锐化和后端 IQ 模块。

对现有报告的更细缺陷分析和后续补强路线，已整理到 [Stage 1 ISP 学习报告深度复盘与改进计划](stage1_deep_review_improvement_plan.md)。这份计划把 Week1-Week6 的不足拆成“可立即补的报告说明”“可用现有数据补的实验”和“需要 ColorChecker / flat-field 等真实标定数据才能完成的产品级验证”三类，后续可以按优先级逐项推进。

在没有新增手机 DNG、ColorChecker 或 flat-field 数据的前提下，已补充一份 [可落地 RAW 体检与画质诊断补强](feasible_raw_quality_audit.md)。它用现有 DNG 生成 RAW 直方图与 ROI 标注图、clipping、ROI SNR proxy、DR 估算、MTF50 proxy、DPC 注入召回、DPC 参数扫描和 AWB baseline 对比。该报告只作为可复现诊断证据，不把自然图 ROI 指标包装成工业实验室 SNR/MTF 或量产 tuning 经验。

根据这轮深度复盘，Week1-Week6 报告已经补充了以下内容：

| 周次 | 已补强内容 |
|---|---|
| Week1 | Sensor 差异、噪声模型、动态范围估计、ROI 选择透明度 |
| Week2 | BLC 误差传播、DPC 注入坏点验证思路、参数敏感性、真实 LSC 标定流程 |
| Week3 | Demosaic 伪影检查框架、AWB ROI / 色卡评估、Gray World 失败案例 |
| Week4 | ColorChecker CCM 标定路径、sRGB OETF、Tone 参数、色域外处理 |
| Week5 | 局部 IQA、主观评价量表、参数敏感性、rawpy reference 边界 |
| Week6 | synthetic flat-field / rawpy DeltaE 的限制、标签定义、时序稳定性、性能基准 |

这些补充主要增强“解释和验证框架”。其中 DPC 注入坏点、Demosaic 伪影 crop、语义 ROI IQA 可以用现有数据继续落地；ColorChecker CCM 和真实 flat-field LSC 仍需要额外标准数据。

## 8. 面试复述笔记

可以这样介绍本阶段：

> 我从真实 DNG 出发，搭了一个可解释 Soft-ISP。前端在 Bayer RAW 域完成 BLC、DPC 和学习用 LSC；随后用 bilinear demosaic 得到线性 RGB，再做 Gray World AWB、CCM、Tone Mapping 和 Gamma 输出可显示图。每个模块都有独立脚本、统计 JSON、对比图和 Markdown 报告。最后我用 rawpy reference 做 PSNR/SSIM/Mean Abs Diff 指标和模块消融，明确说明学习版 pipeline 与产品级 ISP 的差距。

如果面试官追问“为什么算法这么简单”，可以补充：

> 这是我刻意做的第一层 baseline，目的是把数据域和验证闭环打通。后面我参考 OpenISP 梳理了更完整的传统 ISP 模块，包括 RAW 域 AAF/BNF/CNF、Malvar demosaic、假彩抑制、锐化、Gamma LUT 和颜色/风格控制。下一步会选 Malvar demosaic 和 RAW 域降噪做消融，而不是直接堆复杂模块。
