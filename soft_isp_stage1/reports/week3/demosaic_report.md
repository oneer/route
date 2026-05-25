# Week 3 Demosaic 学习报告

本次只做一个小闭环：把 BLC + DPC 后的单通道 Bayer RAW，转换成三通道 RGB 图。这里实现的是最基础的 bilinear demosaic，目标是理解原理，不追求最终颜色好看。

## Demosaic 要解决什么问题

Bayer RAW 的每个像素只记录一种颜色：R、G 或 B。也就是说，原始图像不是每个位置都有完整的 RGB 三个值，而是一个马赛克排列。

以 RGGB 为例：

```text
R  G  R  G ...
G  B  G  B ...
R  G  R  G ...
```

Demosaic 的任务就是：在每一个像素位置，把缺失的另外两个颜色估计出来。做完以后，图像形状会从 `(H, W)` 变成 `(H, W, 3)`。

## 本次 bilinear 的核心思想

对某个颜色通道来说，已经采到的位置保留原值，没采到的位置用周围同色像素做加权平均。越近的像素权重越大。

```text
1 2 1
2 4 2
1 2 1
```

代码里对 R、G、B 分别做一次插值，然后 stack 成 RGB。注意 G 有两个 Bayer 位置，但它们都属于绿色通道，所以会合并成一个 G 平面。

## 从数学上怎么理解 Bayer RAW

可以把理想彩色图像写成三个完整通道：

```text
RGB(y, x) = [R(y, x), G(y, x), B(y, x)]
```

但 Bayer 传感器在每个像素位置只采一种颜色，所以 RAW 是二维数组，不是三通道数组：

```text
RAW(y, x) = R(y, x)  如果该位置是 R 像素
RAW(y, x) = G(y, x)  如果该位置是 G 像素
RAW(y, x) = B(y, x)  如果该位置是 B 像素
```

为了描述这个采样过程，可以给每个颜色定义一个 mask：

```text
M_R(y, x) = 1 表示这个位置真实采到了 R，否则为 0
M_G(y, x) = 1 表示这个位置真实采到了 G，否则为 0
M_B(y, x) = 1 表示这个位置真实采到了 B，否则为 0
```

于是 Bayer RAW 可以写成：

```text
RAW = M_R * R + M_G * G + M_B * B
```

这里的 `*` 是逐像素相乘。每个位置只会有一个 mask 等于 1，所以 RAW 里每个像素只保存一个颜色值。

Demosaic 的目标是从这个不完整采样里估计出完整的三个通道：

```text
R_hat(y, x), G_hat(y, x), B_hat(y, x)
RGB_hat(y, x) = [R_hat(y, x), G_hat(y, x), B_hat(y, x)]
```

`hat` 表示估计值。也就是说，Demosaic 输出里的很多颜色值不是传感器直接测到的，而是算法根据邻域推出来的。

## Bayer 位置关系

以 RGGB 为例，2x2 周期是：

```text
(0,0) R    (0,1) G
(1,0) G    (1,1) B
```

也就是：

```text
偶数行、偶数列 -> R
偶数行、奇数列 -> G，通常记作 Gr
奇数行、偶数列 -> G，通常记作 Gb
奇数行、奇数列 -> B
```

因此每个位置都会缺两个颜色：R 位置缺 G/B，G 位置缺 R/B，B 位置缺 R/G。Demosaic 不是简单地把图变彩色，而是在每个像素位置补两个缺失通道。

## Bilinear 插值公式

Bilinear demosaic 的基本假设是：局部区域内，同一个颜色通道变化比较平滑。一个没采到 R 的位置，它的 R 值可以用附近真实采到的 R 像素估计。

通用的加权平均公式是：

```text
C_hat(y, x) = sum(w_i * C_i) / sum(w_i)
```

其中 `C` 可以是 R/G/B，`C_i` 是附近真实采到的同色像素，`w_i` 是权重。越近的同色像素，权重越大。

本次代码用 3x3 加权核：

```text
1 2 1
2 4 2
1 2 1
```

用 mask + 卷积可以统一写成：

```text
weighted_sum = conv(raw * mask, kernel)
weight_sum   = conv(mask,       kernel)
C_hat        = weighted_sum / weight_sum
```

为什么要除以 `weight_sum`？因为 Bayer 图上不是每个 3x3 邻域都有相同数量的同色采样点。除以有效权重和以后，结果才是真正的局部加权平均。

最后还要把真实采样位置改回原值：

```text
C_hat(y, x) = RAW(y, x)  如果 mask_C(y, x) = 1
```

真实采到的值比插值估计更可信，所以不能被卷积结果覆盖。

## 一个 5x5 小例子

只看 RGGB 里的 R 通道，R 真实存在的位置是：

```text
R  .  R  .  R
.  .  .  .  .
R  .  R  .  R
.  .  .  .  .
R  .  R  .  R
```

点号表示这个位置没有 R，需要估计。两个 R 中间的位置可以理解为：

```text
R_hat = (左边 R + 右边 R) / 2
```

四个 R 中间的位置可以理解为：

```text
R_hat = (左上 R + 右上 R + 左下 R + 右下 R) / 4
```

G 通道更密，因为 Bayer 中有两个 G，所以绿色插值通常比 R/B 更稳定。这也是 Bayer 设计中绿色像素最多的原因：人眼对亮度细节更敏感，而亮度信息很大程度来自绿色通道。

## 本次算法完整流程

```text
读取 DNG
  -> 取 raw_image_visible
  -> 从 metadata 推断 Bayer pattern
  -> BLC：扣 black level
  -> DPC：修复坏点候选
  -> Bilinear Demosaic：补齐 RGB 三通道
  -> Preview：为了保存 PNG 做显示缩放
  -> 写 JSON、PNG、Markdown 报告
```

严格来说，真正属于 Demosaic 的只有：

```text
raw_dpc -> bilinear_demosaic(raw_dpc, bayer_pattern) -> rgb_linear
```

`rgb_preview()` 只是为了把线性 RGB 映射成方便肉眼看的 8-bit PNG，不属于 Demosaic 算法本身。

## Bilinear 的优点和缺点

优点：原理直观、实现简单、速度快，适合作为第一个 baseline。

缺点：它不判断边缘方向，只做局部平均，所以边缘容易变糊；在高频纹理区可能出现假彩色、拉链边等伪影。后续更高级的 demosaic 方法会根据边缘方向选择插值方向，避免跨边缘平均。

## 和 OpenISP CFA / Malvar 的对照

OpenISP 把 Demosaic 模块命名为 `cfa.py`，全称是 Color Filter Array Interpolation。它实现的是 Malvar 类插值，而不是当前项目的 bilinear baseline。

当前 bilinear 的核心是：

```text
C_hat = conv(raw * mask, kernel) / conv(mask, kernel)
```

也就是只用同色邻域做加权平均。OpenISP 的 Malvar 思路更进一步：不同 Bayer 位置使用不同公式，除了周围同色像素，还会利用跨通道和二阶差分项修正颜色。例如在 R 像素位置估计 G/B 时，会用到中心、上下左右、对角等更多位置的组合：

```text
R 位置：R = center
       G = 由中心、上下左右、两格距离项组合估计
       B = 由中心、对角、两格距离项组合估计
```

两者对比如下：

| 维度 | 当前项目 Bilinear | OpenISP Malvar CFA | 学习结论 |
|---|---|---|---|
| 算法目标 | 建立 Bayer 补色直觉 | 提升边缘和纹理处的插值质量 | bilinear 是 baseline，Malvar 是传统 ISP 进阶 |
| 使用信息 | 同色邻域加权平均 | 同色 + 跨通道校正 + 二阶差分 | Malvar 能利用颜色通道相关性 |
| Bayer 位置 | R/G/B 三个 mask 统一公式 | R/Gr/Gb/B 四类位置分别写公式 | 工程实现会按 Bayer 位置细分 |
| 伪影控制 | 不判断边缘方向，容易糊/假彩 | 比 bilinear 更能压伪色，但仍非最强 | 后续还可继续到 AHD/MLRI/LMMSE |
| 实现代价 | 向量化简单，快 | 公式多、分支多、参数更难检查 | 适合做第二阶段对比实验 |

因此，本报告里的 bilinear 不是“最终 demosaic”，而是第一层可解释 baseline。结合 OpenISP 后，下一步最自然的实验是：

```text
BLC/DPC/LSC -> Bilinear Demosaic
BLC/DPC/LSC -> Malvar Demosaic
```

对比时不要只看全图 PSNR，而要专门截取高频纹理、斜边、文字、树枝、格子等区域，看 false color、zipper 和边缘糊化。

## 它和 rawpy reference 为什么不一样

下面的左图是我们自己的结果，右图是 rawpy 的完整 ISP 参考图。两者不能直接按颜色好坏比较，因为 rawpy reference 通常还做了白平衡、颜色矩阵、gamma、亮度映射等步骤。本次输出只验证 demosaic 是否把图像结构补出来，颜色偏绿或偏暗是正常现象。

## 结果总表

| 样张 | Bayer | RAW shape | RGB shape | display white p99.5 | R mean | G mean | B mean | 观察 |
|---|---|---|---|---:|---:|---:|---:|---|
| T01 | RGGB | (2856, 4290) | (2856, 4290, 3) | 6162.00 | 1056.04 | 2485.63 | 1694.52 | 结构正常，颜色还不是最终 ISP 颜色 |
| T02 | RGGB | (2055, 3088) | (2055, 3088, 3) | 615.00 | 243.78 | 314.97 | 185.94 | 结构正常，颜色还不是最终 ISP 颜色 |
| T03 | RGGB | (2348, 3522) | (2348, 3522, 3) | 2444.25 | 284.56 | 596.40 | 430.78 | 结构正常，颜色还不是最终 ISP 颜色 |
| T04 | RGGB | (2348, 3522) | (2348, 3522, 3) | 1351.00 | 133.25 | 292.53 | 231.03 | 结构正常，颜色还不是最终 ISP 颜色 |
| T05 | RGGB | (2055, 3088) | (2055, 3088, 3) | 2437.75 | 163.34 | 400.60 | 365.15 | 结构正常，颜色还不是最终 ISP 颜色 |
| T06 | RGGB | (2348, 3522) | (2348, 3522, 3) | 1108.00 | 235.25 | 429.35 | 293.36 | 结构正常，颜色还不是最终 ISP 颜色 |
| T07 | RGGB | (2920, 4386) | (2920, 4386, 3) | 3564.00 | 334.59 | 721.27 | 505.82 | 结构正常，颜色还不是最终 ISP 颜色 |
| T08 | RGGB | (2856, 4290) | (2856, 4290, 3) | 3671.75 | 609.07 | 1534.41 | 957.41 | 结构正常，颜色还不是最终 ISP 颜色 |
| T09 | RGGB | (2920, 4386) | (2920, 4386, 3) | 981.75 | 142.86 | 207.30 | 101.07 | 结构正常，颜色还不是最终 ISP 颜色 |
| T10 | RGGB | (2348, 3522) | (2348, 3522, 3) | 1435.00 | 382.56 | 285.75 | 50.68 | 结构正常，颜色还不是最终 ISP 颜色 |
| T11 | BGGR | (2014, 3040) | (2014, 3040, 3) | 2262.00 | 302.08 | 382.78 | 157.14 | 结构正常，颜色还不是最终 ISP 颜色 |
| T12 | GBRG | (3335, 5010) | (3335, 5010, 3) | 1472.00 | 144.94 | 251.27 | 81.68 | 结构正常，颜色还不是最终 ISP 颜色 |
| T13 | RGGB | (2844, 4284) | (2844, 4284, 3) | 15892.00 | 2584.68 | 3357.85 | 3098.79 | 结构正常，颜色还不是最终 ISP 颜色 |
| T14 | RGGB | (2844, 4284) | (2844, 4284, 3) | 15892.00 | 1342.06 | 2540.77 | 2371.25 | 结构正常，颜色还不是最终 ISP 颜色 |

## 对比图

这组图从左到右展示模块前后关系：左边是 Demosaic 之前的单通道 Bayer RAW，中间是我们用 bilinear 算法补齐后的 RGB，右边是 rawpy 的完整 ISP 参考。这里重点看结构是否从“灰度马赛克采样”变成“完整 RGB 图像”，不要直接用颜色好不好看来评价 demosaic 本身。

### T01

![T01 demosaic compare](../figures/T01_a0006-IMG_2787_demosaic_compare.png)

### T02

![T02 demosaic compare](../figures/T02_a0008-WP_CRW_3959_demosaic_compare.png)

### T03

![T03 demosaic compare](../figures/T03_a0010-jmac_MG_4807_demosaic_compare.png)

### T04

![T04 demosaic compare](../figures/T04_a0012-kme_143_demosaic_compare.png)

### T05

![T05 demosaic compare](../figures/T05_a0014-WP_CRW_6320_demosaic_compare.png)

### T06

![T06 demosaic compare](../figures/T06_a0018-kme_234_demosaic_compare.png)

### T07

![T07 demosaic compare](../figures/T07_a0020-jmac_MG_6225_demosaic_compare.png)

### T08

![T08 demosaic compare](../figures/T08_a0022-IMG_2380_demosaic_compare.png)

### T09

![T09 demosaic compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_demosaic_compare.png)

### T10

![T10 demosaic compare](../figures/T10_a0026-kme_391_demosaic_compare.png)

### T11

![T11 demosaic compare](../figures/T11_a0033-KE_-2590_demosaic_compare.png)

### T12

![T12 demosaic compare](../figures/T12_a0034-LSYD4O2202_demosaic_compare.png)

### T13

![T13 demosaic compare](../figures/T13_a0035-dgw_048_demosaic_compare.png)

### T14

![T14 demosaic compare](../figures/T14_a0040-_DSC5693_demosaic_compare.png)

## 代码怎么读

本次新增的核心代码在 `soft_isp/demosaic.py`，可以按这条线看：

1. `bayer_positions()`：根据 RGGB/BGGR/GRBG/GBRG 找到 R、G、B 在 2x2 Bayer block 里的位置。
2. `_known_mask()`：生成一个 mask，标记某个颜色真实存在的位置。比如 R mask 只在 R 像素位置为 1。
3. `_interpolate_channel()`：先算 `conv(raw * mask, kernel)`，再除以 `conv(mask, kernel)`，得到缺失位置的同色加权平均值，并把真实采样位置改回原值。
4. `bilinear_demosaic()`：分别补 R/G/B，再合成 `(H, W, 3)`。
5. `rgb_preview()`：只是为了保存 PNG 做显示缩放，不属于严格意义上的 demosaic。

## 今天要记住的结论

1. BLC 和 DPC 仍然在单通道 Bayer 上工作；Demosaic 是第一次把 RAW 变成 RGB 三通道。
2. Demosaic 本质是估计缺失颜色，不是调色。
3. bilinear 很容易理解，但边缘容易糊，也可能产生彩色伪影；后面更高级的方法会重点改善边缘。
4. Demosaic 后的图还不是最终照片，因为还缺 AWB、CCM、gamma/tone mapping。
5. 对照 OpenISP 后要记住：Malvar 通过按 Bayer 位置使用不同校正公式，把 demosaic 从“同色平均”推进到“跨通道校正”。

## 下一步

下一步最自然的是 AWB，也就是白平衡。因为现在已经有 RGB 三个通道了，我们可以开始估计每个通道应该乘多少增益，让灰色物体重新接近灰色。
