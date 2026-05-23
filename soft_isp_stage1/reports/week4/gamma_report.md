# Week 4-2 Gamma 学习报告

Gamma 是把线性 RGB 映射到更适合显示和人眼感知的非线性 RGB。线性图直接显示通常会显得偏暗，因为显示编码和人眼感知都不是简单的线性关系。

这一节重点解释两个词：`linear display` 和 `gamma`。你看到的现象是：左边线性 RGB 直接显示更暗，右边加 gamma 后中间调和暗部被抬起来。这个现象是正常的，而且可以用数学直接解释。

## 背景：什么是线性 RGB

线性 RGB 的意思是：数值和真实光强成正比。假设一个像素的线性值是 `0.2`，另一个是 `0.4`，后者代表的光强大约是前者的两倍。

线性空间对 ISP 算法很重要，因为很多物理计算都默认光是线性叠加的。例如 demosaic 插值、AWB 乘增益、CCM 矩阵乘法，都应该尽量在线性空间里完成。

## 什么是 linear display

报告图里的 `Linear display` 不是一个新的 ISP 算法，它只是为了对比，把线性 RGB 归一化到 `0..1` 后直接保存成图片：

```text
rgb_display = clip(rgb_linear / display_white, 0, 1)
```

问题在于，普通图片文件和普通显示链路通常默认输入已经是类似 sRGB/gamma 编码后的值。如果我们把线性值直接当成显示值，中间调会显得偏暗。

举个数字例子：线性值 `0.25` 代表 25% 的物理光强。直接显示时它就是 0.25，看起来偏暗；做 gamma 后：

```text
0.25 ** (1 / 2.2) = 0.533
```

同一个线性中间调被编码成 0.533，所以视觉上明显变亮。线性值 `0.5` 也会变成：

```text
0.50 ** (1 / 2.2) = 0.730
```

这就是你看到“暗部和中间调被拉起来”的根本原因。

## 数学形式

本周使用最常见的简化 gamma：

```text
rgb_gamma = rgb_linear ** (1 / gamma)
gamma = 2.2
```

如果输入已经归一化到 `0..1`，并且 `gamma > 1`，那么 `1/gamma < 1`。对 `0..1` 之间的数做小于 1 的幂，会让它变大：

```text
x = 0.10 -> x ** (1/2.2) = 0.351
x = 0.25 -> x ** (1/2.2) = 0.533
x = 0.50 -> x ** (1/2.2) = 0.730
x = 1.00 -> x ** (1/2.2) = 1.000
```

所以 gamma 不是平均地把整张图加亮。越靠近黑色的中低亮度区域变化越明显，纯白 `1.0` 仍然是 `1.0`。

## 本周的计算过程

本周 gamma 的输入是 CCM 后的线性 RGB。流程是：

```text
rgb_ccm -> percentile normalize -> gamma encode -> uint8 preview
```

具体步骤：

1. 先用 `99.5%` 分位点估计一个显示白点 `display_white`。
2. 用 `rgb_ccm / display_white` 把图像归一化到大致 `0..1`。
3. 对归一化结果做 `rgb ** (1/2.2)`。
4. 乘 255 并转成 `uint8`，保存为可直接查看的 PNG。

这里的 gamma 是简化版。严格的 sRGB OETF 在暗部有一段线性分段，不完全等于单纯 `1/2.2` 幂函数。本周先用简化公式，是为了看清楚非线性显示编码的核心作用。

## Gamma 前后对比

左边是线性 RGB 直接显示，右边是加 gamma 后。重点看中间调和暗部是不是被抬起来了。它们被抬起来不是因为曝光变了，而是同一批线性数值换了一种更适合显示的编码方式。

### T01

![T01 gamma compare](../figures/T01_a0006-IMG_2787_gamma_compare.png)

### T02

![T02 gamma compare](../figures/T02_a0008-WP_CRW_3959_gamma_compare.png)

### T03

![T03 gamma compare](../figures/T03_a0010-jmac_MG_4807_gamma_compare.png)

### T04

![T04 gamma compare](../figures/T04_a0012-kme_143_gamma_compare.png)

### T05

![T05 gamma compare](../figures/T05_a0014-WP_CRW_6320_gamma_compare.png)

### T06

![T06 gamma compare](../figures/T06_a0018-kme_234_gamma_compare.png)

### T07

![T07 gamma compare](../figures/T07_a0020-jmac_MG_6225_gamma_compare.png)

### T08

![T08 gamma compare](../figures/T08_a0022-IMG_2380_gamma_compare.png)

### T09

![T09 gamma compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_gamma_compare.png)

### T10

![T10 gamma compare](../figures/T10_a0026-kme_391_gamma_compare.png)

### T11

![T11 gamma compare](../figures/T11_a0033-KE_-2590_gamma_compare.png)

### T12

![T12 gamma compare](../figures/T12_a0034-LSYD4O2202_gamma_compare.png)

### T13

![T13 gamma compare](../figures/T13_a0035-dgw_048_gamma_compare.png)

### T14

![T14 gamma compare](../figures/T14_a0040-_DSC5693_gamma_compare.png)

## 今天要记住的结论

1. Gamma 不是白平衡，也不是颜色校正，它主要改变亮度编码方式。
2. 大多数 ISP 算法应在线性空间里做，gamma 通常放在接近显示输出的位置。
3. `1/2.2` 会抬高中间调，让线性图更适合普通显示器观看。
4. Gamma 不等于 Tone Mapping。Gamma 主要解决显示编码和感知亮度，Tone Mapping 主要解决动态范围压缩。
5. 看到 linear display 偏暗不是算法错了，而是线性数据还没有进入适合显示的编码状态。
