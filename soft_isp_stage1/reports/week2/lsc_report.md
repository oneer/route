# Week 2-3 LSC 学习报告

LSC 的全称是 Lens Shading Correction，镜头阴影校正。它处理的是位置相关的亮度和颜色不均匀：常见现象是中心较亮、边缘较暗，或者边缘带一点颜色偏移。

## 本次实现边界

这里实现的是学习用径向 LSC baseline，不是产品标定版。真实产品通常用积分球或均匀白场拍摄得到 R/Gr/Gb/B 的 gain map，并按镜头、焦距、光圈、色温准备多套表。

本次默认只做保守补偿：中心 gain 为 1，越靠近边缘 gain 越高，且 R/Gr/Gb/B 可以有不同边缘增益。它的价值是把 LSC 放回 pipeline 的正确位置，并观察它如何影响后续 AWB/CCM。

## Pipeline 位置

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone/Gamma
```

LSC 放在 Demosaic 之前，因为镜头阴影发生在 RAW/Bayer 域。越早处理，越不容易把位置相关的亮度/色偏带进 AWB 的全局统计。

## 和 OpenISP 的对照

OpenISP 当前这组模块里没有直接对应的 `lsc.py`。这不是说 LSC 不重要，反而说明 LSC 往往不像 BLC/DPC/CFA 那样可以靠一段通用算法解决。真实 LSC 通常依赖镜头、sensor、光圈、焦距和色温下的 flat-field 标定数据。

当前项目的 LSC 是学习用径向模型：

```text
gain(center) = 1
gain(edge)   = edge_gain
raw_lsc      = raw * gain_map
```

它适合理解三个问题：

1. LSC 为什么应放在 Demosaic/AWB 前；
2. 边缘增益会同时放大信号和噪声；
3. R/Gr/Gb/B 的 gain map 可以不同，位置相关色偏会影响 AWB。

如果结合 OpenISP 其他模块看，LSC 的输出会直接影响后面的 `awb.py`、`cfa.py`、`cnf.py`：

| 后续模块 | LSC 不准时的影响 |
|---|---|
| AWB / WB gain | 边缘色偏混入全局通道均值，导致白平衡估计偏 |
| CFA / Demosaic | 暗角区域信噪比低，插值后边缘噪声和假彩更明显 |
| CNF / BNF | 边缘被增益放大后，色噪和亮度噪声也会被放大 |

所以 LSC 后续升级不应“照搬 OpenISP”，而应找 flat-field 或均匀白场样张，估计真实的 per-channel gain map，再和当前径向 baseline 做对照。

## 结果总表

| 样张 | Bayer | gain min | gain max | RAW mean before | RAW mean after | 观察 |
|---|---|---:|---:|---:|---:|---|
| T01 | RGGB | 1.000 | 1.220 | 1930.421 | 2034.637 | 边缘被保守抬升，噪声也会同步放大 |
| T02 | RGGB | 1.000 | 1.220 | 264.921 | 279.943 | 边缘被保守抬升，噪声也会同步放大 |
| T03 | RGGB | 1.000 | 1.220 | 477.039 | 499.067 | 边缘被保守抬升，噪声也会同步放大 |
| T04 | RGGB | 1.000 | 1.220 | 237.325 | 249.437 | 边缘被保守抬升，噪声也会同步放大 |
| T05 | RGGB | 1.000 | 1.220 | 332.391 | 348.237 | 边缘被保守抬升，噪声也会同步放大 |
| T06 | RGGB | 1.000 | 1.220 | 346.815 | 363.628 | 边缘被保守抬升，噪声也会同步放大 |
| T07 | RGGB | 1.000 | 1.220 | 570.701 | 597.001 | 边缘被保守抬升，噪声也会同步放大 |
| T08 | RGGB | 1.000 | 1.220 | 1158.834 | 1208.051 | 边缘被保守抬升，噪声也会同步放大 |
| T09 | RGGB | 1.000 | 1.220 | 164.634 | 170.800 | 边缘被保守抬升，噪声也会同步放大 |
| T10 | RGGB | 1.000 | 1.220 | 251.152 | 264.992 | 边缘被保守抬升，噪声也会同步放大 |
| T11 | BGGR | 1.000 | 1.220 | 306.211 | 317.602 | 边缘被保守抬升，噪声也会同步放大 |
| T12 | GBRG | 1.000 | 1.220 | 182.290 | 190.441 | 边缘被保守抬升，噪声也会同步放大 |
| T13 | RGGB | 1.000 | 1.220 | 3099.756 | 3177.689 | 边缘被保守抬升，噪声也会同步放大 |
| T14 | RGGB | 1.000 | 1.220 | 2198.730 | 2295.741 | 边缘被保守抬升，噪声也会同步放大 |

## LSC 对比图

### T01

![T01 LSC compare](../figures/T01_a0006-IMG_2787_lsc_compare.png)

### T02

![T02 LSC compare](../figures/T02_a0008-WP_CRW_3959_lsc_compare.png)

### T03

![T03 LSC compare](../figures/T03_a0010-jmac_MG_4807_lsc_compare.png)

### T04

![T04 LSC compare](../figures/T04_a0012-kme_143_lsc_compare.png)

### T05

![T05 LSC compare](../figures/T05_a0014-WP_CRW_6320_lsc_compare.png)

### T06

![T06 LSC compare](../figures/T06_a0018-kme_234_lsc_compare.png)

### T07

![T07 LSC compare](../figures/T07_a0020-jmac_MG_6225_lsc_compare.png)

### T08

![T08 LSC compare](../figures/T08_a0022-IMG_2380_lsc_compare.png)

### T09

![T09 LSC compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_lsc_compare.png)

### T10

![T10 LSC compare](../figures/T10_a0026-kme_391_lsc_compare.png)

### T11

![T11 LSC compare](../figures/T11_a0033-KE_-2590_lsc_compare.png)

### T12

![T12 LSC compare](../figures/T12_a0034-LSYD4O2202_lsc_compare.png)

### T13

![T13 LSC compare](../figures/T13_a0035-dgw_048_lsc_compare.png)

### T14

![T14 LSC compare](../figures/T14_a0040-_DSC5693_lsc_compare.png)

## 失败场景和注意点

1. 没有 flat-field 标定时，径向模型可能把真实场景的暗角误当成镜头问题。
2. LSC 会放大边缘信号，也会放大边缘噪声，所以不能只看亮度是否更均匀。
3. 如果不同颜色通道 gain 不合理，AWB 会被新的边缘色偏带偏。
4. 当前实现用于学习 pipeline 位置和数据域，不应当被当作相机标定结果。
5. 对照 OpenISP 后要记住：LSC 缺少通用模块并不是缺口小，而是因为它更依赖标定数据和 tuning 表。
