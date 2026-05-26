# ISP 模块掌握标准对照表

这份表用来回答一个问题：当前 Stage1 的报告是否覆盖了每个 ISP 模块从“入门”到“面试可讲”的能力要求。结论是：主链路已经覆盖到“能讲清楚基础 pipeline 和模块 tradeoff”，但部分产品级能力还停留在“已知道方向，待补实验”。

## 总体结论

| 模块 | 当前覆盖程度 | 主要证据 | 还需要补强 |
|---|---|---|---|
| RAW 读取 | 已覆盖到面试可讲 | Week1 summary / raw_statistics / ROI | 可补 RAW10/RAW12 unpack 原理 |
| BLC | 已覆盖到面试可讲 | Week2 BLC + OpenISP BLC 对照 | 可补 OB 区统计实验 |
| DPC | 已覆盖到面试可讲 | Week2 DPC + Week6 static defect map | 后续可换真实工厂 defect map |
| LSC | 已覆盖到面试可讲 | Week2 LSC + Week6 synthetic flat-field / mesh LUT | 后续需要真实 flat-field |
| Demosaic | 基本覆盖到面试可讲 | Week3 Demosaic + Week6 OpenCV baseline / edge-aware | 后续可实作 OpenISP Malvar / AHD |
| AWB | 已覆盖到面试可讲 | Week3 AWB + Week6 white patch / gray ROI | 后续可加肤色保护和时序平滑 |
| CCM | 已覆盖到面试可讲 | Week4 CCM + Week6 Lab / DeltaE / diff x8 | 后续需要真实色卡 |
| Gamma / Tone | 已覆盖到面试可讲 | Week4 Gamma/Tone + Week6 sRGB OETF / S-curve LUT | 后续可做局部 tone |
| IQA | 已覆盖到面试可讲 | Week5 full-image IQA + Week6 ROI 指标 / 主观标签 | 后续可人工固定语义 ROI |

## 1. RAW 读取

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能用 rawpy 读出 Bayer 数据 | 已覆盖。Week1 已读取 DNG visible RAW、shape、dtype、metadata。 |
| 掌握 | 能解析 black/white level、Bayer pattern、四通道统计 | 已覆盖。`raw_statistics.md` 和 `summary.md` 有 black level、white level、Bayer pattern、R/Gr/Gb/B 统计。 |
| 面试可讲 | 能解释 RAW、linear RGB、sRGB 的区别 | 已覆盖。Week1 解释 RAW 不是 RGB；Week3/Week4 解释 linear RGB、Gamma 和 sRGB preview。 |

还可以补：RAW10/RAW12 packed 格式和 DNG unpack 后 `uint16` 存储的区别。这个属于底层数据格式，不影响当前 pipeline，但面试深挖时有用。

## 2. BLC

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能扣黑电平并归一化 | 已覆盖。BLC 报告有 `raw - black_level`、clip 和 white level 更新。 |
| 掌握 | 能解释黑电平来源和扣除顺序 | 已覆盖。报告解释 sensor / ADC offset，且强调 BLC 应放在 DPC / CFA / AWB 前。 |
| 面试可讲 | 能说明黑电平错误如何影响暗部和颜色 | 已覆盖。报告说明过扣会暗部 clip，欠扣会暗部发灰、污染 AWB 和颜色。 |

还可以补：从 optical black 区域估计 black level 的实验。当前依赖 DNG metadata 和 OpenISP tuning 参数。

## 3. DPC

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能修复简单 hot pixel | 已覆盖。DPC 报告有 mask 和局部 repair crop。 |
| 掌握 | 能用同色邻域做坏点检测 | 已覆盖。当前实现按 R/Gr/Gb/B 同色平面检测；OpenISP 对照解释 5x5 同色邻域。 |
| 面试可讲 | 能解释动态检测和静态 defect map 的差异 | 已覆盖。Week6 构造静态 defect map，并和动态检测数量、mask 行为做对比。 |

已补实验：Week6 新增“小型静态 defect map 实验”，从动态候选中抽取固定坐标，比较：

```text
dynamic DPC：根据当前图像统计检测坏点
static defect map：根据标定表固定替换指定坐标
hybrid：先静态修复，再动态检测剩余异常
```

## 4. LSC

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能做径向 gain map | 已覆盖。当前有学习版径向 LSC 和对比图。 |
| 掌握 | 能做四通道独立 gain | 已覆盖。报告说明 per-channel gain map，Week6 用合成 flat-field 验证 mesh gain 估计。 |
| 面试可讲 | 能解释标定、网格 LUT、边缘噪声放大 | 已覆盖。Week2 讲风险，Week6 展示 flat-field / mesh LUT 的来源。 |

已补实验：Week6 用合成 flat-field 做 mesh gain 估计。当前仍没有真实 flat-field，所以还不能证明产品级 LSC 正确性。

## 5. Demosaic

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能实现 bilinear | 已覆盖。Week3 Demosaic 有公式、mask、卷积和结果图。 |
| 掌握 | 能对比 OpenCV baseline 和伪影 | 已覆盖。Week6 对比本项目 bilinear、OpenCV bilinear、OpenCV edge-aware。 |
| 面试可讲 | 能解释 AHD / 方向自适应为什么更好 | 基本覆盖。Week6 用 OpenCV edge-aware 作为方向自适应入门对照；AHD/Malvar 仍可后续实作。 |

已补实验：Week6 增加 `Bilinear vs OpenCV bilinear vs OpenCV edge-aware` 对比。下一步如果继续加深，可把 OpenISP Malvar 或 AHD 接进同一套评估。

## 6. AWB

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能实现 gray world / white patch | 已覆盖。Week3 做 Gray World，Week6 增加 White Patch。 |
| 掌握 | 能做简单 ROI 筛选 | 已覆盖。Week6 增加 Gray ROI 候选筛选和覆盖率统计。 |
| 面试可讲 | 能解释混合光、纯色场景、饱和区域导致的失败 | 已覆盖。AWB 报告和面试题都解释了大面积单色、混合光源、饱和区域问题。 |

已补实验：Week6 新增 `gray_world vs white_patch vs gray_roi` 小实验，并输出 gain、指标和对比图。

## 7. CCM

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能应用 3x3 矩阵 | 已覆盖。Week4 CCM 有 `rgb @ ccm.T`、clip 和前后对比。 |
| 掌握 | 能解释线性 RGB 和 Lab / DeltaE | 已覆盖。Week4 讲线性 RGB，Week6 计算 no-CCM / CCM 相对 rawpy reference 的 DeltaE。 |
| 面试可讲 | 能说明 CCM、AWB、Gamma 的顺序关系 | 已覆盖。报告明确 CCM 在 AWB 后、Gamma 前，且应在线性 RGB 上做。 |

已补实验：Week6 增加 CCM 前后差异放大图、Lab / DeltaE 与 rawpy reference 的比较。这样可以回答“为什么 CCM 看起来不明显，但数值上确实改变了颜色关系”。

## 8. Gamma / Tone

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能实现 sRGB gamma | 已覆盖。Week6 增加 sRGB OETF 对比。 |
| 掌握 | 能做简单 S-curve | 已覆盖。Week6 增加 S-curve LUT 曲线和指标。 |
| 面试可讲 | 能解释显示编码和动态范围压缩的区别 | 已覆盖。Gamma 报告解释显示编码，Tone 报告解释动态范围压缩，Week5 分析了 `gamma_only` 与 Reinhard 的差异。 |

已补实验：Week6 新增 `pow gamma vs sRGB OETF vs S-curve LUT` 实验。OpenISP 的 `gac.py` LUT 可以继续作为工程实现对照。

## 9. IQA

| 层级 | 标准 | 当前覆盖 |
|---|---|---|
| 入门 | 能算 PSNR / SSIM | 已覆盖。Week5 脚本和报告计算 PSNR、SSIM、Mean Abs Diff。 |
| 掌握 | 能做 ROI + 指标 + 主观标签 | 已覆盖。Week6 自动选 center/dark/highlight/texture/corner ROI，输出指标和主观标签。 |
| 面试可讲 | 能解释指标和主观画质冲突 | 已覆盖。Week5 明确解释 PSNR/SSIM 高不等于主观更好，rawpy reference 不是 ground truth。 |

已补实验：Week6 已经给每张样张增加自动 ROI 和主观标签。后续可以进一步改成人工固定语义 crop，例如：

```text
skin / sky / edge / dark / highlight / texture
```

然后对每个 crop 记录 `PSNR / SSIM / Mean Abs Diff / 主观问题标签`，比如偏色、假彩、噪声、过锐、偏灰、clip。

## 下一步优先级

如果按“最补短板”的顺序，建议接下来这样做：

1. **真实标定数据。** 用真实 flat-field 做 LSC，用 ColorChecker 做 CCM / DeltaE。
2. **更强 demosaic。** 把 OpenISP Malvar 或 AHD 接进 Week6 的 demosaic 对比框架。
3. **语义 ROI。** 手动固定肤色、天空、高光、暗部、纹理 crop，替代自动 ROI。
4. **局部 tone 和后端 IQ。** 接入 FCS / EE / BCC / HSC 这类 OpenISP 后端模块。

一句话总结：当前报告已经能支撑“我搭过一个可解释 Soft-ISP，并知道每个模块的输入输出、验证方法和失败场景”。如果要进一步接近“面试可讲得很扎实”，下一步不是继续堆模块，而是把 CCM、Demosaic、Tone/IQA 这几个弱项做成可量化、可局部观察的对比实验。
