# Week 1：RAW / Sensor 数据直觉

## 本周目标

理解 RAW 数值、Sensor 物理和四通道统计之间的关系。

## 样张

| 编号 | 文件名 | 场景 | 备注 |
|---|---|---|---|
| S01 | `data/raw/S01_a0001-jmac_DSC1459.dng` | FiveK 起步样张 | 12-bit，整体曝光中等，适合做首次 RAW 统计 |
| S02 | `data/raw/S02_a0002-dgw_005.dng` | FiveK 对照样张 | white level 明显更高，适合观察不同相机位深/电平定义 |
| S03 | `data/raw/S03_a0003-NKIM_MG_8178.dng` | FiveK 对照样张 | black level=1023，p99 到达高亮端，适合观察高光 clipping |
| S04 | `data/raw/S04_a0004-jmac_MG_1384.dng` | FiveK 对照样张 | black level 约 128，整体偏暗，适合观察暗部统计 |
| S05 | `data/raw/S05_a0005-jn_2007_05_10__564.dng` | FiveK 对照样张 | p50 接近 black level，p99 到达 white level，高动态范围明显 |

## Metadata 摘要

| 编号 | shape | dtype | Bayer | black level | white level | raw min/max | mean/std |
|---|---|---|---|---:|---:|---|---|
| S01 | 2014 x 3040 | uint16 | BGGR | 0 / 0 / 0 / 0 | 4095 | 2 / 3821 | 671.84 / 491.83 |
| S02 | 2844 x 4284 | uint16 | RGGB | 0 / 0 / 0 / 0 | 15892 | 0 / 16263 | 967.46 / 849.15 |
| S03 | 2602 x 3908 | uint16 | RGGB | 1023 / 1023 / 1023 / 1023 | 13600 | 1013 / 13824 | 3405.88 / 4191.59 |
| S04 | 2920 x 4386 | uint16 | RGGB | 128 / 127 / 128 / 128 | 3692 | 122 / 3692 | 380.68 / 360.00 |
| S05 | 2348 x 3522 | uint16 | RGGB | 127 / 128 / 127 / 127 | 3398 | 121 / 3398 | 524.30 / 955.04 |

## 四通道统计观察

| 编号 | R mean | Gr mean | Gb mean | B mean | 主要结论 |
|---|---:|---:|---:|---:|---|
| S01 | 473.93 | 842.36 | 837.64 | 533.45 | Gr/Gb 接近；G 明显高于 R/B，说明还没有做白平衡和颜色校正 |
| S02 | 1049.11 | 1095.92 | 1096.47 | 628.34 | Gr/Gb 几乎一致；B 通道均值较低，后续 AWB 会重点补偿 B |
| S03 | 2570.74 | 3694.28 | 3695.10 | 3663.38 | Gr/Gb 一致；整体亮度和标准差很高，p99 已到达 13824，高光风险明显 |
| S04 | 251.51 | 446.92 | 447.67 | 376.60 | Gr/Gb 一致；整体偏暗但仍有高光到达 white level |
| S05 | 384.03 | 585.93 | 585.71 | 541.52 | 中位数接近黑电平但 p99 到达 white level，暗部和高光同时存在 |

## 亮度与高光观察

| 编号 | p50 | p99 | white level | 初步判断 |
|---|---:|---:|---:|---|
| S01 | 546 | 1982 | 4095 | 主体像素离饱和较远，适合做基础统计 |
| S02 | 814 | 3910 | 15892 | 高光余量较大，整体不接近饱和 |
| S03 | 1564 | 13824 | 13600 | p99 已超过 white level，存在明显高光 clipping 风险 |
| S04 | 236 | 2036 | 3692 | 大部分像素偏暗，少量像素达到白电平 |
| S05 | 149 | 3398 | 3398 | 中位数很暗，p99 到达白电平，动态范围压力最大 |

## 关键图

- Histogram：
  - S01：![S01 RAW histogram](figures/S01_a0001-jmac_DSC1459_histogram.png)
  - S03：![S03 RAW histogram](figures/S03_a0003-NKIM_MG_8178_histogram.png)
  - S05：![S05 RAW histogram](figures/S05_a0005-jn_2007_05_10__564_histogram.png)
- ROI 分析：已完成，详见 `reports/week1_roi_analysis.md`。

## 怎么读 Histogram

Histogram 直方图是在回答一个问题：这张 RAW 里，不同亮度数值的像素各有多少。

- 横轴 `RAW value`：像素的原始数值。越靠左越暗，越靠右越亮。
- 纵轴 `Pixel count (log)`：落在某个数值区间里的像素数量。本图用了 log 坐标，所以纵轴每高一格不是线性增加，而是成倍增加。这样做是为了同时看见大量暗部像素和少量高光像素。
- 灰色柱子 `All Bayer samples`：把 R、Gr、Gb、B 所有 Bayer 像素混在一起看的整体亮度分布。
- 彩色曲线 `Bayer channel samples`：分别看 R、Gr、Gb、B 四个采样位置的分布。它们不是最终 RGB 图像的颜色，只是传感器经过不同滤色片后的 RAW 响应。
- 黑色虚线 `black level`：相机认为“没有光时”的基准值。BLC 会把这个值扣掉，让有效信号从 0 开始。
- 红色虚线 `white level`：相机认为接近饱和的上限。像素大量堆在这附近，通常说明高光可能 clipping。

读图时先看三件事：

1. 主体峰值在哪里：大部分柱子靠左，说明整体偏暗；靠右，说明整体偏亮。
2. 是否贴近 black level：如果大量像素挤在黑电平附近，暗部细节可能少，BLC 后容易变成 0。
3. 是否贴近 white level：如果右侧在白电平附近出现尖峰，说明高光可能已经饱和，后续 tone mapping 也救不回真实细节。

## Histogram 观察

| 编号 | 图 | 观察 |
|---|---|---|
| S01 | ![S01 RAW histogram](figures/S01_a0001-jmac_DSC1459_histogram.png) | 分布主体离 white level 较远，适合用来建立正常曝光 RAW 的基础直觉 |
| S03 | ![S03 RAW histogram](figures/S03_a0003-NKIM_MG_8178_histogram.png) | p99 已超过 white level，高光端需要重点看 clipping；black level=1023，后续 BLC 影响明显 |
| S05 | ![S05 RAW histogram](figures/S05_a0005-jn_2007_05_10__564_histogram.png) | 中位数接近 black level，同时 p99 到达 white level，适合观察暗部和高光共存的高动态范围压力 |

## S01 与 S03/S05 为什么不一样

S01 的直方图和 S03/S05 明显不同，这是合理现象，不是当前脚本出错的直接证据。

| 对比点 | S01 | S03 | S05 | 解释 |
|---|---|---|---|---|
| Bayer | BGGR | RGGB | RGGB | 排列不同只影响通道标签位置，不会让整体 histogram 失真 |
| black level | 0 | 1023 | 127/128 | S03/S05 的有效信号起点不是 0，所以左侧分布会从黑电平附近开始 |
| white level | 4095 | 13600 | 3398 | 三张图的数值范围不同，横轴跨度不同，不能只凭形状直接比较亮暗 |
| p50 | 546 | 1564 | 149 | S01 中位数在低到中间亮度；S03 中位数高于黑电平较多；S05 大量像素贴近暗部 |
| p99 | 1982 | 13824 | 3398 | S01 高光离白电平较远；S03/S05 高光贴近或超过白电平 |

具体看图：

1. S01 的主体分布集中在 0 到 2000 左右，红色 white level 在 4095 附近，右侧没有明显贴住白电平的巨大尖峰。说明它大部分像素没有饱和，是比较适合入门观察的样张。
2. S03 的 black level 是 1023，所以左侧从 1023 附近开始才是有效暗部。它在 white level 附近出现很高的尖峰，说明有一批像素被推到高光上限附近，存在 clipping 风险。
3. S05 同时有两个特征：左侧很多像素挤在 black level 附近，右侧又有像素挤到 white level 附近。它不是“坏图”，而是动态范围压力大：暗部很暗，高光又很亮。
4. S01 的四通道分布看起来更“分开”，S03/S05 的高光端更容易挤成尖峰，这是场景曝光、相机白电平、black level 和高光饱和共同造成的。

所以当前判断是：S01、S03、S05 的差异主要来自样张内容和 metadata，不是 Bayer 自动推断或 histogram 绘图逻辑的问题。后续真正需要继续确认的是：S03/S05 右侧尖峰对应图像中的哪些区域，这要靠 ROI 或参考图来定位。

## Week 1 核心问题复盘

### 1. black level 不为 0 时，为什么不能直接做 demosaic？

black level 是传感器的暗电平偏置。它不是光信号，而是相机/传感器在“没有光”的情况下仍然存在的基础数值。

例如 S03：

```text
black level = 1023
```

如果某个像素值是 `1200`，它真实代表的光信号更接近：

```text
1200 - 1023 = 177
```

如果不先扣 black level，直接做 demosaic，就会把这 `1023` 的偏置也当成真实光信号参与插值。这个错误会继续影响后续模块：

```text
Demosaic：把错误暗部偏置插值到 RGB 图里
AWB：基于错误的 R/G/B 比例估计白平衡
CCM：在错误的线性 RGB 上做颜色映射
Gamma/Tone：把暗部整体抬亮，导致黑位发灰
```

典型现象是：

```text
黑色不黑
暗部发灰
低光区域颜色脏
对比度变低
```

正确顺序应该是：

```text
RAW
-> BLC：raw - black_level
-> normalize：/ (white_level - black_level)
-> Demosaic
-> AWB
-> CCM
-> Gamma/Tone
```

一句话：black level 不扣掉，后面的 ISP 都是在“带偏置的假信号”上工作。

### 2. 为什么 Gr/Gb 接近可以验证 Bayer 拆分大致正确？

Bayer 阵列里有两个绿色位置。例如 RGGB：

```text
R  Gr
Gb B
```

绿色出现两次，是因为人眼对亮度更敏感，而绿色通道对亮度结构贡献最大。

在自然图像里，`Gr` 和 `Gb` 不会完全一样，因为它们采样的位置不同。但从全图平均统计看，它们通常应该比较接近。当前样张里：

```text
S01:
Gr = 842.36
Gb = 837.64

S02:
Gr = 1095.92
Gb = 1096.47

S03:
Gr = 3694.28
Gb = 3695.10
```

它们非常接近，说明：

```text
Bayer pattern 大概率判断对了
通道拆分位置大概率没错
两个绿色采样位置的平均响应一致
```

如果 Gr/Gb 差异特别大，就要优先怀疑：

```text
Bayer pattern 搞错
R/B/G 位置拆反
图像有强烈方向性纹理
存在行列噪声
镜头阴影或局部照明导致统计偏移
```

一句话：自然图像里两个绿色通道应该统计上接近；如果不接近，先怀疑 Bayer 拆分或数据问题。

### 3. histogram 右侧贴近 white level 代表什么？

Histogram 横轴越靠右，RAW 值越高。`white level` 是相机认为的有效高光上限。

如果大量像素贴近 white level，说明这些像素可能已经接近传感器饱和。饱和意味着：

```text
真实世界里这个区域可能还有更亮的层次
但传感器已经记不下来了
很多不同亮度都被压成同一个最大值
```

这就是 clipping。

例如 S05：

```text
white level = 3398
p99 = 3398
```

这说明至少 1% 左右的像素已经到达白电平附近。再看 ROI：

```text
S05 highlight ROI:
p50 = 3398
p99 = 3398
```

这个 ROI 里至少一半像素已经到 white level，基本可以认为高光严重饱和。

clipping 的后果是：

```text
高光没有纹理
天空/灯/反光区域变成一片白
后续 tone mapping 只能压亮度，不能恢复真实细节
AWB/CCM 也可能被饱和区域误导
```

一句话：histogram 右侧贴近 white level，表示高光可能已经饱和；贴成尖峰越明显，clipping 风险越高。

### 4. S05 为什么同时适合看暗部和高光？

因为 S05 同时满足两个特征：

```text
暗部很暗
高光很亮
```

从全图统计看：

```text
S05 black level = 127 / 128
S05 white level = 3398
S05 p50 = 149
S05 p99 = 3398
```

`p50 = 149` 说明一半像素低于或接近 149，而 black level 是 127/128。也就是说，大量像素非常接近黑电平。

同时，`p99 = 3398` 且 `white level = 3398`，说明高光端已经到达白电平。

ROI 也验证了这一点：

```text
S05 dark ROI:
p50 = 136
接近 black level

S05 highlight ROI:
p50 = 3398
p99 = 3398
接近 white level
```

所以 S05 对后续模块特别有用：

```text
BLC：看暗部扣黑电平后是否大量变成 0
Tone mapping：看高光怎么压回来
Demosaic：看暗部噪声和高光边缘是否出伪色
AWB：看高光饱和区域是否影响白平衡估计
```

一句话：S05 一边有贴近 black level 的暗部，一边有贴近 white level 的高光，所以它很适合测试 ISP 对动态范围极端区域的处理。

### 5. ROI 分析为什么比只看全图 mean 更有用？

全图 mean 只有一个数字，它会把整张图所有区域混在一起。

例如 S05：

```text
S05 mean = 524.30
```

如果只看 mean，可能会误以为这张图只是“整体不算特别暗”。但 ROI 告诉我们：

```text
dark ROI p50 = 136，接近 black level
highlight ROI p50 = 3398，接近 white level
```

这说明它不是简单的平均亮度 `524`，而是：

```text
暗部非常暗
高光已经饱和
动态范围压力很大
```

ROI 能回答更具体的问题：

```text
暗部是否贴近 black level？
高光是否贴近 white level？
中间亮度是否稳定？
四通道在局部区域是否仍然合理？
BLC 前后暗部 ROI 怎么变？
AWB 前后中性区域 R/G/B 是否更接近？
Tone mapping 后高光 ROI 是否被压回可显示范围？
```

全图 mean 只能回答“全图平均大概多亮”，它太粗了。后续做 ISP 模块时，ROI 是更重要的对比单位。

一句话：全图 mean 是粗略总览，ROI 是局部诊断。ISP 问题通常发生在局部，所以 ROI 更有用。

## 本周结论

1. 5 张样张的 Bayer pattern 已能由脚本自动从 metadata 推断；S01 是 BGGR，其余 4 张是 RGGB，后续不需要手动传 `--pattern`。
2. black level 不同相机差异很大：S01/S02 为 0，S03 为 1023，S04/S05 约 128；后续做 BLC 前必须先读取 metadata，不能写死常数。
3. Gr 和 Gb 在 5 张图中都非常接近，说明 Bayer 拆分基本正确，也说明两个绿色采样位置的平均响应一致。
4. S03/S05 已经出现高光端压力，适合后续做 clipping、tone mapping 和 ROI 分析；S05 同时有很暗的中位数，是观察高动态范围的好样张。
5. R/G/B 均值差异不能直接解释成最终颜色偏差，因为当前仍是 RAW 线性传感器响应，还没有经过 AWB、CCM、Gamma/Tone。
6. 已生成 S01/S03/S05 的 RAW histogram 和 ROI 分析，下一步可以进入 BLC，但仍要保留这些 ROI 作为前后对比区域。

## 还没想清楚的问题

- 需要查看 5 张 rawpy 参考图，给每张样张补上更准确的场景标签。
- S02/S03 的 raw max 超过 white level，后续要确认 rawpy metadata 中 white level 和实际饱和值的关系。
