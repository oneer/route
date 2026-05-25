# Week 4 总结：CCM / Gamma / Tone Mapping

Week4 的目标是把 Week3 的 AWB 后 RGB 继续推向可显示图像。三个模块分开理解：CCM 负责颜色空间/颜色混合，Gamma 负责显示编码，Tone Mapping 负责动态范围压缩。

如果只记一句话：Week3 得到的是“线性相机 RGB”，Week4 开始把它变成“更接近人眼和显示器能正常观看的图像”。

## 本周流水线

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma -> Preview
```

## 分模块报告

- [CCM 报告](ccm_report.md)
- [Gamma 报告](gamma_report.md)
- [Tone Mapping 报告](tone_mapping_report.md)

## 分模块脚本

- `scripts/10_apply_ccm.py`：只负责 CCM 对比图和 CCM 报告
- `scripts/11_apply_gamma.py`：只负责 Gamma 对比图和 Gamma 报告
- `scripts/12_apply_tone_mapping.py`：只负责 Tone Mapping 对比图和 Tone Mapping 报告
- `scripts/13_write_week4_summary.py`：只负责 Week4 综合对比图和总结
- `scripts/week4_common.py`：只放共用的 RAW -> AWB -> CCM 基础流水线和画图工具

## 核心概念速查

| 名词 | 简单理解 | 本周位置 |
|---|---|---|
| 线性 RGB | 数值和真实光强近似成正比 | Demosaic/AWB/CCM 的工作空间 |
| Linear display | 把线性 RGB 直接当显示图看 | 只用于对比，不是最终输出 |
| CCM | 用 `3x3` 矩阵混合 R/G/B，修正相机颜色空间 | AWB 之后 |
| Tone Mapping | 把高动态范围压进显示范围 | CCM 之后、Gamma 之前 |
| Gamma | 把线性亮度编码成更适合显示和视觉感知的非线性值 | 接近最终输出 |

## 为什么顺序是 CCM -> Tone Mapping -> Gamma

CCM 需要在线性 RGB 上做矩阵乘法，因为颜色混合默认基于线性光强。Tone Mapping 也最好在线性亮度上做，这样压高光、保中间调的曲线含义更清楚。Gamma 放在最后，是因为它主要是显示编码，不应该提前破坏前面算法需要的线性关系。

## 综合对比图

这组图从左到右是 AWB、CCM、Tone+Gamma、rawpy reference，用来快速观察 Week4 之后整体显示效果的变化。

### T01

![T01 Week4 pipeline compare](../figures/T01_a0006-IMG_2787_week4_pipeline_compare.png)

### T02

![T02 Week4 pipeline compare](../figures/T02_a0008-WP_CRW_3959_week4_pipeline_compare.png)

### T03

![T03 Week4 pipeline compare](../figures/T03_a0010-jmac_MG_4807_week4_pipeline_compare.png)

### T04

![T04 Week4 pipeline compare](../figures/T04_a0012-kme_143_week4_pipeline_compare.png)

### T05

![T05 Week4 pipeline compare](../figures/T05_a0014-WP_CRW_6320_week4_pipeline_compare.png)

### T06

![T06 Week4 pipeline compare](../figures/T06_a0018-kme_234_week4_pipeline_compare.png)

### T07

![T07 Week4 pipeline compare](../figures/T07_a0020-jmac_MG_6225_week4_pipeline_compare.png)

### T08

![T08 Week4 pipeline compare](../figures/T08_a0022-IMG_2380_week4_pipeline_compare.png)

### T09

![T09 Week4 pipeline compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week4_pipeline_compare.png)

### T10

![T10 Week4 pipeline compare](../figures/T10_a0026-kme_391_week4_pipeline_compare.png)

### T11

![T11 Week4 pipeline compare](../figures/T11_a0033-KE_-2590_week4_pipeline_compare.png)

### T12

![T12 Week4 pipeline compare](../figures/T12_a0034-LSYD4O2202_week4_pipeline_compare.png)

### T13

![T13 Week4 pipeline compare](../figures/T13_a0035-dgw_048_week4_pipeline_compare.png)

### T14

![T14 Week4 pipeline compare](../figures/T14_a0040-_DSC5693_week4_pipeline_compare.png)

## Week4 学习结论

1. Demosaic 之后只是有了 RGB 结构，还不是最终显示图。
2. AWB 让白点接近中性，CCM 进一步修正颜色关系。
3. Gamma 会显著影响中间调亮度，所以不能把它和曝光、AWB 混在一起理解。
4. Tone Mapping 是显示输出前非常关键的一步，决定亮部和暗部如何压缩。
5. linear display 偏暗通常不是错，而是线性数据还没经过显示编码。
6. 当前 Week4 是学习版闭环，目标是理解模块作用；产品级 ISP 还会加入色卡标定、sRGB OETF、局部 tone mapping、对比度曲线和更复杂的高光恢复。

## 当前学习版和产品级的差距

Week4 已经跑通显示输出，但还不是产品级渲染。当前 CCM 来自 DNG/rawpy 暴露的矩阵简化使用，没有做色卡最小二乘拟合；Gamma 使用简化 `1/2.2` 幂函数，不是完整 sRGB OETF；Tone Mapping 使用全局分位归一化和 Reinhard 曲线，没有局部 tone、对比度曲线或高光恢复。

因此 Week4 的正确理解是：它完成了“线性 RGB 如何走向可显示图”的学习闭环，而不是复刻 rawpy/Lightroom 的完整渲染策略。Week5 的 IQA 和消融会专门用指标说明这些差异。

OpenISP 还补充了几个 Week4 之后才会出现的传统模块：`gac.py` 用 LUT 做 Gamma，`eeh.py` 做边缘增强，`fcs.py` 做假彩抑制，`bcc.py` / `hsc.py` 做亮度、对比度、色相和饱和度控制。这些模块提醒我们：Tone/Gamma 后并不意味着 ISP 结束，最终 IQ 还依赖锐化、假彩控制和风格化参数。

结合 OpenISP 后，Week4 可以从“显示映射”扩展成“后端 IQ 链路”：

| OpenISP 模块 | 当前 Week4 对应关系 | 报告应增加的理解 |
|---|---|---|
| `ccm.py` | 我们的 `soft_isp/ccm.py` | 产品实现常用 fixed-point 矩阵和 offset，浮点矩阵只是学习表达 |
| `csc.py` | 当前未显式实现 | CCM 后常进入 RGB/YUV 等颜色空间转换，后续锐化/假彩/饱和度可能在 YUV 上做 |
| `gac.py` | 我们的 `apply_gamma()` | Gamma 可用 LUT 实现，方便端侧定点化和调曲线 |
| `eeh.py` | 当前未实现 | 锐化通常需要边缘图、阈值、gain 和 clip，不能简单 unsharp mask 一把梭 |
| `fcs.py` | 当前未实现 | 假彩抑制通常和边缘图联动，越强边缘越要小心压 UV |
| `bcc.py` / `hsc.py` | 当前未实现 | 亮度、对比度、色相、饱和度属于最终风格控制，不应和物理校正混在一起 |

所以 Week4 的结论应改成：当前完成的是显示基础链路；OpenISP 展示的是完整后端 IQ 链路。下一步如果想让项目更像传统 ISP，而不是只做 RAW 转 RGB，应优先增加 `CSC -> FCS/EE -> BCC/HSC` 的概念实验。
