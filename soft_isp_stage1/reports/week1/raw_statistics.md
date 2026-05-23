# Week 1：RAW / Sensor 数据直觉

本报告已更新为当前主样张集 `T01-T14`。这些样张来自 MIT-Adobe FiveK，覆盖水面纹理、人像、天空、建筑、室内暖光、隧道暗部、大面积绿色/蓝色等场景，用来暴露不同 ISP 模块的问题。

## 本周目标

理解 RAW 数值、Sensor metadata、Bayer 四通道统计、histogram 和 ROI 之间的关系。Week1 不做校正，只建立后续 BLC、DPC、Demosaic、AWB 的数据坐标系。

## 样张清单

| 编号 | 文件名 | 建议用途 |
|---|---|---|
| T01 | `T01_a0006-IMG_2787.dng` | 水面细节 / 高频纹理 / Demosaic |
| T02 | `T02_a0008-WP_CRW_3959.dng` | 人像 / 肤色 / AWB |
| T03 | `T03_a0010-jmac_MG_4807.dng` | 天空 / 彩虹 / AWB 风险 |
| T04 | `T04_a0012-kme_143.dng` | 建筑直线 / 边缘伪影 |
| T05 | `T05_a0014-WP_CRW_6320.dng` | 黑白边界 / DPC 误检 / Demosaic |
| T06 | `T06_a0018-kme_234.dng` | 风景 / 高动态范围 / Tone |
| T07 | `T07_a0020-jmac_MG_6225.dng` | 大面积绿色 / AWB 失败案例 |
| T08 | `T08_a0022-IMG_2380.dng` | 大面积蓝色 / AWB 失败案例 |
| T09 | `T09_a0023-07-06-02-at-15h06m48-s_MG_1489.dng` | 室内人物 / 混合光 / AWB |
| T10 | `T10_a0026-kme_391.dng` | 隧道 / 暗部 / 高对比 |
| T11 | `T11_a0033-KE_-2590.dng` | 室内暖光 / 食物 / 肤色 |
| T12 | `T12_a0034-LSYD4O2202.dng` | 树林绿色 / 高频叶子 |
| T13 | `T13_a0035-dgw_048.dng` | 城市建筑 / 高频边缘 |
| T14 | `T14_a0040-_DSC5693.dng` | 蓝天建筑 / CCM / 边缘 |

## Metadata 摘要

| 编号 | shape | dtype | Bayer | black level | white level | raw min/max | mean/std |
|---|---|---|---|---:|---:|---|---|
| T01 | 2856 x 4290 | uint16 | RGGB | 1024 / 1024 / 1023 / 1024 | 16000 | 1044 / 16383 | 2954.50 / 1530.56 |
| T02 | 2055 x 3088 | uint16 | RGGB | 127 / 128 / 128 / 127 | 4000 | 114 / 952 | 392.42 / 171.52 |
| T03 | 2348 x 3522 | uint16 | RGGB | 128 / 128 / 127 / 128 | 4095 | 118 / 4095 | 604.79 / 459.15 |
| T04 | 2348 x 3522 | uint16 | RGGB | 128 / 128 / 127 / 127 | 4095 | 121 / 4095 | 365.07 / 330.55 |
| T05 | 2055 x 3088 | uint16 | RGGB | 127 / 126 / 126 / 127 | 4000 | 126 / 3514 | 458.89 / 377.94 |
| T06 | 2348 x 3522 | uint16 | RGGB | 128 / 128 / 127 / 127 | 4095 | 130 / 1717 | 474.31 / 291.06 |
| T07 | 2920 x 4386 | uint16 | RGGB | 128 / 128 / 128 / 128 | 3692 | 120 / 3692 | 698.73 / 813.59 |
| T08 | 2856 x 4290 | uint16 | RGGB | 1024 / 1024 / 1024 / 1024 | 16000 | 941 / 16383 | 2190.95 / 778.05 |
| T09 | 2920 x 4386 | uint16 | RGGB | 127 / 128 / 127 / 128 | 3692 | 97 / 3692 | 292.13 / 186.89 |
| T10 | 2348 x 3522 | uint16 | RGGB | 128 / 128 / 127 / 127 | 4095 | 124 / 4095 | 378.73 / 287.09 |
| T11 | 2014 x 3040 | uint16 | BGGR | 0 / 0 / 0 / 0 | 4095 | 0 / 4095 | 306.21 / 414.80 |
| T12 | 3335 x 5010 | uint16 | GBRG | 128 / 128 / 128 / 128 | 3711 | 119 / 3711 | 310.46 / 282.91 |
| T13 | 2844 x 4284 | uint16 | RGGB | 0 / 0 / 0 / 0 | 15892 | 26 / 16383 | 3149.35 / 4770.17 |
| T14 | 2844 x 4284 | uint16 | RGGB | 0 / 0 / 0 / 0 | 15892 | 21 / 16383 | 2205.75 / 2623.68 |

## 四通道统计观察

| 编号 | R mean | Gr mean | Gb mean | B mean | 主要结论 |
|---|---:|---:|---:|---:|---|
| T01 | 2080.26 | 3513.32 | 3506.98 | 2717.46 | Gr/Gb 接近；R 偏低，AWB 可能需要提升 R |
| T02 | 370.78 | 441.87 | 443.07 | 313.94 | Gr/Gb 接近；B 偏低，AWB 可能需要提升 B |
| T03 | 412.52 | 726.15 | 722.65 | 557.83 | Gr/Gb 接近；R 偏低，AWB 可能需要提升 R |
| T04 | 261.42 | 421.07 | 419.59 | 358.18 | Gr/Gb 接近；R 偏低，AWB 可能需要提升 R |
| T05 | 290.35 | 525.15 | 529.04 | 491.12 | Gr/Gb 接近；R 偏低，AWB 可能需要提升 R |
| T06 | 363.32 | 557.92 | 555.78 | 420.25 | Gr/Gb 接近；R 偏低，AWB 可能需要提升 R |
| T07 | 462.77 | 848.85 | 849.80 | 633.49 | Gr/Gb 接近；B 偏低，AWB 可能需要提升 B；R 偏低，AWB 可能需要提升 R |
| T08 | 1636.89 | 2571.70 | 2569.48 | 1985.73 | Gr/Gb 接近；R 偏低，AWB 可能需要提升 R |
| T09 | 269.86 | 336.05 | 334.55 | 228.07 | Gr/Gb 接近；B 偏低，AWB 可能需要提升 B |
| T10 | 510.49 | 413.27 | 413.42 | 177.74 | Gr/Gb 接近；B 偏低，AWB 可能需要提升 B |
| T11 | 302.14 | 382.67 | 382.89 | 157.14 | Gr/Gb 接近；B 偏低，AWB 可能需要提升 B |
| T12 | 272.95 | 379.18 | 380.00 | 209.72 | Gr/Gb 接近；B 偏低，AWB 可能需要提升 B；R 偏低，AWB 可能需要提升 R |
| T13 | 2648.51 | 3392.62 | 3396.86 | 3159.39 | Gr/Gb 接近 |
| T14 | 1349.48 | 2546.64 | 2548.40 | 2378.49 | Gr/Gb 接近；R 偏低，AWB 可能需要提升 R |

## 亮度与高光观察

| 编号 | p50 | p99 | white level | 初步判断 |
|---|---:|---:|---:|---|
| T01 | 2410 | 7018 | 16000 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T02 | 394 | 740 | 4000 | 中位数靠近黑电平，适合观察暗部、BLC 和噪声 |
| T03 | 544 | 2318 | 4095 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T04 | 218 | 1441 | 4095 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T05 | 374 | 2357 | 4000 | 中位数靠近黑电平，适合观察暗部、BLC 和噪声 |
| T06 | 382 | 1218 | 4095 | 中位数靠近黑电平，适合观察暗部、BLC 和噪声 |
| T07 | 357 | 3692 | 3692 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T08 | 2074 | 4638 | 16000 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T09 | 232 | 1043 | 3692 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T10 | 298 | 1260 | 4095 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T11 | 163 | 1940 | 4095 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T12 | 201 | 1495 | 3711 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T13 | 1166 | 16383 | 15892 | 高光接近或达到白电平，适合观察 clipping / tone mapping |
| T14 | 1541 | 15891 | 15892 | 高光接近或达到白电平，适合观察 clipping / tone mapping |

## Histogram 图

Histogram 用来观察 RAW 值分布、黑电平附近像素、高光是否贴近白电平，以及四个 Bayer 通道的响应差异。

### T01

![T01 RAW histogram](../figures/T01_a0006-IMG_2787_histogram.png)

### T02

![T02 RAW histogram](../figures/T02_a0008-WP_CRW_3959_histogram.png)

### T03

![T03 RAW histogram](../figures/T03_a0010-jmac_MG_4807_histogram.png)

### T04

![T04 RAW histogram](../figures/T04_a0012-kme_143_histogram.png)

### T05

![T05 RAW histogram](../figures/T05_a0014-WP_CRW_6320_histogram.png)

### T06

![T06 RAW histogram](../figures/T06_a0018-kme_234_histogram.png)

### T07

![T07 RAW histogram](../figures/T07_a0020-jmac_MG_6225_histogram.png)

### T08

![T08 RAW histogram](../figures/T08_a0022-IMG_2380_histogram.png)

### T09

![T09 RAW histogram](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_histogram.png)

### T10

![T10 RAW histogram](../figures/T10_a0026-kme_391_histogram.png)

### T11

![T11 RAW histogram](../figures/T11_a0033-KE_-2590_histogram.png)

### T12

![T12 RAW histogram](../figures/T12_a0034-LSYD4O2202_histogram.png)

### T13

![T13 RAW histogram](../figures/T13_a0035-dgw_048_histogram.png)

### T14

![T14 RAW histogram](../figures/T14_a0040-_DSC5693_histogram.png)

## 怎么读 Histogram

- 横轴 `RAW value`：传感器原始数值，越右越亮。
- 纵轴 `Pixel count (log)`：该数值区间内像素数量，log 坐标便于同时看暗部主体和少量高光。
- 黑电平线：BLC 会扣掉的基线。
- 白电平线：接近饱和的上限，右侧堆积通常意味着 clipping。
- 四通道曲线：R/Gr/Gb/B 的 RAW 响应，不是最终 RGB 颜色。

## ROI 分析

ROI 分析已重新生成，详见 `reports/week1/roi_analysis.md`。暗部 ROI 用来看黑电平和噪声，中间调 ROI 用作模块前后对比，高光 ROI 用来观察 clipping 和 tone mapping 风险。

## 本周结论

1. 当前主样张集比旧的 S01-S05 覆盖面更完整，包含 AWB 失败、大面积单色、暗部、高动态范围、强边缘和人像肤色。
2. `T07/T08/T12` 这类大面积绿色或蓝色图，很适合检验 Gray World AWB 的失败场景。
3. `T04/T05/T13/T14` 适合观察 Demosaic 边缘伪影。
4. `T10` 适合观察暗部、BLC 和后续 tone mapping。
5. Week1 的重点仍然是读懂 RAW 数值分布，不要直接用最终视觉效果判断模块对错。
