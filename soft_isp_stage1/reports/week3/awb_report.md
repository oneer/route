# Week 3 AWB 学习报告

本次完成 Week3 的第二个核心模块：AWB，也就是 Auto White Balance，自动白平衡。输入是 Demosaic 后的线性 RGB，输出仍然是线性 RGB，只是每个颜色通道乘了不同的 gain。

## AWB 解决什么问题

Demosaic 只是把 Bayer RAW 补成 RGB，它不会让颜色变准。传感器的 R/G/B 响应、光源颜色、镜头透过率都会让图像偏色。AWB 的目标是估计光源颜色，并用通道增益把中性物体拉回接近灰色。

白平衡最核心的形式很简单：

```text
R_awb = R * R_gain
G_awb = G * G_gain
B_awb = B * B_gain
```

本次为了学习，固定 `G_gain = 1`，让 R 和 B 向 G 对齐。

## Gray World 假设

Gray World 的假设是：如果一张图包含足够多不同颜色的物体，那么整张图的平均颜色应该接近灰色。灰色意味着 R、G、B 三个通道平均值接近。

所以可以用下面的公式估计 gain：

```text
R_gain = G_mean / R_mean
G_gain = 1
B_gain = G_mean / B_mean
```

本次实现会先排除最暗的 5% 和最亮的 5% 像素，再计算均值。这样可以减少黑场噪声和高光饱和区域对白平衡估计的影响。

## 结果总表

| 样张 | Bayer | R gain | G gain | B gain | R/G before | B/G before | R/G after | B/G after | 观察 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| T01 | RGGB | 2.345 | 1.000 | 1.498 | 0.425 | 0.682 | 0.991 | 1.020 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T02 | RGGB | 1.281 | 1.000 | 1.688 | 0.774 | 0.590 | 0.992 | 0.996 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T03 | RGGB | 2.125 | 1.000 | 1.360 | 0.477 | 0.722 | 1.013 | 0.982 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T04 | RGGB | 2.165 | 1.000 | 1.268 | 0.455 | 0.790 | 0.985 | 1.001 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T05 | RGGB | 2.434 | 1.000 | 1.091 | 0.408 | 0.912 | 0.992 | 0.994 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T06 | RGGB | 1.721 | 1.000 | 1.424 | 0.548 | 0.683 | 0.943 | 0.973 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T07 | RGGB | 2.218 | 1.000 | 1.456 | 0.464 | 0.701 | 1.005 | 0.996 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T08 | RGGB | 2.608 | 1.000 | 1.544 | 0.397 | 0.624 | 1.033 | 0.963 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T09 | RGGB | 1.470 | 1.000 | 1.994 | 0.689 | 0.488 | 1.013 | 0.972 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T10 | RGGB | 0.738 | 1.000 | 6.358 | 1.339 | 0.177 | 0.988 | 1.007 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T11 | BGGR | 1.177 | 1.000 | 2.587 | 0.789 | 0.411 | 0.929 | 1.035 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T12 | GBRG | 1.755 | 1.000 | 3.321 | 0.577 | 0.325 | 1.012 | 1.064 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T13 | RGGB | 1.275 | 1.000 | 1.064 | 0.770 | 0.923 | 0.860 | 0.951 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |
| T14 | RGGB | 2.195 | 1.000 | 0.983 | 0.528 | 0.933 | 1.014 | 0.917 | 通道均值更接近，但颜色仍未经过 CCM/Gamma |

## AWB 前后对比

### T01

![T01 AWB compare](../figures/T01_a0006-IMG_2787_awb_compare.png)

### T02

![T02 AWB compare](../figures/T02_a0008-WP_CRW_3959_awb_compare.png)

### T03

![T03 AWB compare](../figures/T03_a0010-jmac_MG_4807_awb_compare.png)

### T04

![T04 AWB compare](../figures/T04_a0012-kme_143_awb_compare.png)

### T05

![T05 AWB compare](../figures/T05_a0014-WP_CRW_6320_awb_compare.png)

### T06

![T06 AWB compare](../figures/T06_a0018-kme_234_awb_compare.png)

### T07

![T07 AWB compare](../figures/T07_a0020-jmac_MG_6225_awb_compare.png)

### T08

![T08 AWB compare](../figures/T08_a0022-IMG_2380_awb_compare.png)

### T09

![T09 AWB compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_awb_compare.png)

### T10

![T10 AWB compare](../figures/T10_a0026-kme_391_awb_compare.png)

### T11

![T11 AWB compare](../figures/T11_a0033-KE_-2590_awb_compare.png)

### T12

![T12 AWB compare](../figures/T12_a0034-LSYD4O2202_awb_compare.png)

### T13

![T13 AWB compare](../figures/T13_a0035-dgw_048_awb_compare.png)

### T14

![T14 AWB compare](../figures/T14_a0040-_DSC5693_awb_compare.png)

## 怎么验证 AWB 是否有效

第一，看数值：AWB 后的 `R/G` 和 `B/G` 应该比 AWB 前更接近 1。第二，看图像：明显偏绿、偏蓝或偏红的趋势应该减轻。第三，不能只看是否“好看”，因为当前还没有做 CCM、Gamma 和 Tone Mapping。

## 失败场景

Gray World 很简单，也很容易失败。比如画面里大面积草地、天空、红墙、舞台灯，整张图的平均颜色本来就不该是灰色，这时它会把真实颜色错误地中和掉。混合光源也会失败，因为不同区域需要不同白平衡，单一 RGB gain 无法同时修正。

## 今天要记住的结论

1. AWB 的输入是 Demosaic 后的线性 RGB，不是 sRGB 图片。
2. AWB 本质是估计并应用每通道 gain，不是复杂调色。
3. Gray World 是一个可解释的 baseline，适合学习和建立直觉。
4. AWB 后颜色仍然不等于最终照片，因为还缺 CCM、Gamma/Tone。
