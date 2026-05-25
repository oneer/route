# 阶段 1 实验报告

## 1. 项目目标

从真实 RAW / DNG 输入开始，实现并解释一个基础 Soft-ISP Pipeline。阶段 1 的目标不是复刻商业 ISP，而是建立可检查、可解释、可消融的数据流。

## 2. 当前完成度

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma -> sRGB Preview
```

已完成 14 张 MIT-Adobe FiveK DNG 样张的 RAW 统计、逐模块可视化、rawpy reference 对比和 Week5 指标/消融实验。

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

## 5. 与参考输出的主要差异

1. **Tone 曲线不同**：Week5 中 `gamma_only` 平均 PSNR/SSIM 反而高于 `full`，说明 rawpy 默认渲染更接近分位归一化 + 显示编码，而不是本项目学习用 Reinhard 曲线。
2. **AWB 是全局 Gray World**：大面积单色或混合光源会使全局均值假设失效，`no_awb` 消融通常显著拉低指标，说明白平衡影响很大。
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

阶段 1 已经从“能读 RAW”推进到“能逐模块解释 RAW 到可显示图的每一步”。现在最有价值的成果不是最终图像多好看，而是每个模块都有代码、图、JSON 和报告支撑，能回答输入输出、核心假设、验证方法和失败场景。

当前仍然是学习版 pipeline。下一阶段如果继续向产品级靠近，优先顺序应是：标定版 LSC、Malvar/AHD Demosaic、RAW 域 AAF/BNF 消融、更稳健 AWB、色卡 CCM、sRGB OETF/局部 tone、假彩抑制/锐化、系统化 DeltaE/LPIPS/主观评价。

## 8. 面试复述笔记

可以这样介绍本阶段：

> 我从真实 DNG 出发，搭了一个可解释 Soft-ISP。前端在 Bayer RAW 域完成 BLC、DPC 和学习用 LSC；随后用 bilinear demosaic 得到线性 RGB，再做 Gray World AWB、CCM、Tone Mapping 和 Gamma 输出可显示图。每个模块都有独立脚本、统计 JSON、对比图和 Markdown 报告。最后我用 rawpy reference 做 PSNR/SSIM/Mean Abs Diff 指标和模块消融，明确说明学习版 pipeline 与产品级 ISP 的差距。

如果面试官追问“为什么算法这么简单”，可以补充：

> 这是我刻意做的第一层 baseline，目的是把数据域和验证闭环打通。后面我参考 OpenISP 梳理了更完整的传统 ISP 模块，包括 RAW 域 AAF/BNF/CNF、Malvar demosaic、假彩抑制、锐化、Gamma LUT 和颜色/风格控制。下一步会选 Malvar demosaic 和 RAW 域降噪做消融，而不是直接堆复杂模块。
