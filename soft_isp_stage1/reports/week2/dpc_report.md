# Week 2-2 DPC 学习报告

本次在 BLC 后继续做 DPC，也就是 Dead Pixel Correction，坏点检测与修复。这里先做一个保守版本：只寻找和同色邻域明显不一致的孤立异常点。

## 为什么 DPC 要在 BLC 后做

BLC 扣掉的是传感器基线偏置。DPC 判断的是某个像素是否相对邻域异常。如果不先做 BLC，像素值里还带着 black level 偏置，暗部异常的判断会不干净。所以顺序通常是：RAW -> BLC -> DPC -> 后续 Demosaic/AWB。

## 本次算法

Bayer RAW 相邻像素不是同一种颜色，所以不能直接拿上下左右像素比较。脚本先把 RAW 按 Bayer pattern 拆成 R / Gr / Gb / B 四个同色平面，然后在每个同色平面上做 3x3 中值检测。

```text
local_median = median(同色 3x3 邻域)
residual = abs(pixel - local_median)
threshold = max(min_delta, median(residual) + mad_k * MAD(residual))
如果 residual > threshold，就标记为坏点候选
修复值 = local_median
```

这里输出的是“坏点候选”，不是最终工厂标定意义上的永久坏点表。高光边缘、强纹理和噪声也可能被少量误检，所以后面要结合局部 crop 图判断。

## 和 OpenISP DPC 的对照

当前项目的 DPC 是“同色平面 + robust threshold + median repair”的学习版。它先把 Bayer RAW 拆成 R/Gr/Gb/B 四个同色平面，再在每个平面里用 3x3 median 判断孤立异常点。这种写法优点是概念清楚：坏点一定要和同色邻域比较，阈值由 MAD 自适应估计。

OpenISP 的 `openisp/dpc.py` 采用另一种更工程直觉的写法：直接在完整 Bayer RAW 上取隔 2 像素的 5x5 同色邻域，中心点 `p0` 周围有 8 个同色点：

```text
p1 p2 p3
p4 p0 p5
p6 p7 p8
```

检测条件是：如果 `p0` 和 8 个同色邻居的差异都超过固定阈值，就认为它是坏点候选。修复时有两种模式：

```text
mean 模式：     p0 = (p2 + p4 + p5 + p7) / 4
gradient 模式： 选择垂直/水平/对角线中梯度最小的方向做平均
```

两者对比如下：

| 维度 | 当前项目 DPC | OpenISP DPC | 学习结论 |
|---|---|---|---|
| 同色处理方式 | 先拆 R/Gr/Gb/B 平面 | 在原 Bayer 图上隔 2 像素取同色邻域 | 本质都是同色比较，只是数据组织不同 |
| 检测阈值 | `max(min_delta, median + mad_k * MAD)` | 固定 `thres` | 当前版本更自适应；OpenISP 更接近 tuning 参数 |
| 邻域大小 | 同色平面 3x3 | 原图 5x5 中的 3x3 同色点 | 对应关系相近，都是 8 邻域同色判断 |
| 修复方式 | local median | mean 或 gradient direction average | median 抗孤立异常；gradient repair 更保护边缘方向 |
| 工程风险 | 强纹理/highlight 仍可能误检 | 固定阈值对不同 ISO/曝光不够自适应 | 产品级通常会结合坏点表、ISO、温度和边缘保护 |

因此 DPC 报告里要多记一层：**坏点修复不是只有“检测到就换成 median”。在边缘区域，沿最小梯度方向修复能减少抹边；在不同噪声水平下，自适应阈值又比固定阈值更稳。**

后续如果升级当前 DPC，可以加入一个 `repair_mode` 参数：

```text
median：当前版本，稳健简单
gradient：参考 OpenISP，按最小梯度方向修复
```

然后专门看强边缘 crop：median 是否把边缘抹平，gradient 是否更保结构。

## 结果总表

| 样张 | Bayer | 候选数 | 占比 | R | Gr | Gb | B | 最大修复幅度 | 观察 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| T01 | RGGB | 1429 | 0.0001 | 37 | 496 | 560 | 336 | 9989.00 | 候选点很少，符合保守检测预期 |
| T02 | RGGB | 0 | 0.0000 | 0 | 0 | 0 | 0 | 0.0000 | 候选点很少，符合保守检测预期 |
| T03 | RGGB | 1 | 0.0000 | 0 | 0 | 1 | 0 | 1188.00 | 候选点很少，符合保守检测预期 |
| T04 | RGGB | 1235 | 0.0001 | 182 | 388 | 406 | 259 | 3764.00 | 候选点很少，符合保守检测预期 |
| T05 | RGGB | 6 | 0.0000 | 0 | 1 | 5 | 0 | 1271.00 | 候选点很少，符合保守检测预期 |
| T06 | RGGB | 0 | 0.0000 | 0 | 0 | 0 | 0 | 0.0000 | 候选点很少，符合保守检测预期 |
| T07 | RGGB | 335 | 0.0000 | 2 | 133 | 192 | 8 | 2249.00 | 候选点很少，符合保守检测预期 |
| T08 | RGGB | 44262 | 0.0036 | 5869 | 15862 | 15985 | 6546 | 13639.00 | 候选点偏多，需要看 mask 是否落在强边缘或高光区域 |
| T09 | RGGB | 0 | 0.0000 | 0 | 0 | 0 | 0 | 0.0000 | 候选点很少，符合保守检测预期 |
| T10 | RGGB | 551 | 0.0001 | 154 | 153 | 188 | 56 | 3651.00 | 候选点很少，符合保守检测预期 |
| T11 | BGGR | 1 | 0.0000 | 1 | 0 | 0 | 0 | 1204.00 | 候选点很少，符合保守检测预期 |
| T12 | GBRG | 2501 | 0.0001 | 75 | 1150 | 1212 | 64 | 2528.00 | 候选点很少，符合保守检测预期 |
| T13 | RGGB | 186184 | 0.0153 | 43979 | 49743 | 49454 | 43008 | 15149.00 | 候选点偏多，需要看 mask 是否落在强边缘或高光区域 |
| T14 | RGGB | 65144 | 0.0053 | 14240 | 18805 | 18887 | 13212 | 14597.00 | 候选点偏多，需要看 mask 是否落在强边缘或高光区域 |

## Mask 预览

红色点表示 DPC 候选点。由于坏点通常很稀疏，全图上可能只看到少量红点；这恰好是正常现象。

### T01

![T01 DPC mask](../figures/T01_a0006-IMG_2787_dpc_mask_overlay.png)

### T02

![T02 DPC mask](../figures/T02_a0008-WP_CRW_3959_dpc_mask_overlay.png)

### T03

![T03 DPC mask](../figures/T03_a0010-jmac_MG_4807_dpc_mask_overlay.png)

### T04

![T04 DPC mask](../figures/T04_a0012-kme_143_dpc_mask_overlay.png)

### T05

![T05 DPC mask](../figures/T05_a0014-WP_CRW_6320_dpc_mask_overlay.png)

### T06

![T06 DPC mask](../figures/T06_a0018-kme_234_dpc_mask_overlay.png)

### T07

![T07 DPC mask](../figures/T07_a0020-jmac_MG_6225_dpc_mask_overlay.png)

### T08

![T08 DPC mask](../figures/T08_a0022-IMG_2380_dpc_mask_overlay.png)

### T09

![T09 DPC mask](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_dpc_mask_overlay.png)

### T10

![T10 DPC mask](../figures/T10_a0026-kme_391_dpc_mask_overlay.png)

### T11

![T11 DPC mask](../figures/T11_a0033-KE_-2590_dpc_mask_overlay.png)

### T12

![T12 DPC mask](../figures/T12_a0034-LSYD4O2202_dpc_mask_overlay.png)

### T13

![T13 DPC mask](../figures/T13_a0035-dgw_048_dpc_mask_overlay.png)

### T14

![T14 DPC mask](../figures/T14_a0040-_DSC5693_dpc_mask_overlay.png)

## 局部修复对比

每张图选一个修复幅度最大的候选点附近做 crop。左边是 DPC 前，中间是 DPC 后，右边是候选 mask。

### T01

![T01 DPC repair crop](../figures/T01_a0006-IMG_2787_dpc_repair_crop.png)

- 候选坐标：x `3009`，y `1171`
- 修复前后：`14687` -> `4698`

### T02

![T02 DPC repair crop](../figures/T02_a0008-WP_CRW_3959_dpc_repair_crop.png)

这张图没有检测到候选点，所以 crop 使用图像中心区域。

### T03

![T03 DPC repair crop](../figures/T03_a0010-jmac_MG_4807_dpc_repair_crop.png)

- 候选坐标：x `768`，y `1871`
- 修复前后：`1644` -> `456`

### T04

![T04 DPC repair crop](../figures/T04_a0012-kme_143_dpc_repair_crop.png)

- 候选坐标：x `1235`，y `1034`
- 修复前后：`3967` -> `203`

### T05

![T05 DPC repair crop](../figures/T05_a0014-WP_CRW_6320_dpc_repair_crop.png)

- 候选坐标：x `601`，y `1004`
- 修复前后：`783` -> `2054`

### T06

![T06 DPC repair crop](../figures/T06_a0018-kme_234_dpc_repair_crop.png)

这张图没有检测到候选点，所以 crop 使用图像中心区域。

### T07

![T07 DPC repair crop](../figures/T07_a0020-jmac_MG_6225_dpc_repair_crop.png)

- 候选坐标：x `2926`，y `1395`
- 修复前后：`2753` -> `504`

### T08

![T08 DPC repair crop](../figures/T08_a0022-IMG_2380_dpc_repair_crop.png)

- 候选坐标：x `1506`，y `1993`
- 修复前后：`14976` -> `1337`

### T09

![T09 DPC repair crop](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_dpc_repair_crop.png)

这张图没有检测到候选点，所以 crop 使用图像中心区域。

### T10

![T10 DPC repair crop](../figures/T10_a0026-kme_391_dpc_repair_crop.png)

- 候选坐标：x `1746`，y `1045`
- 修复前后：`3968` -> `317`

### T11

![T11 DPC repair crop](../figures/T11_a0033-KE_-2590_dpc_repair_crop.png)

- 候选坐标：x `2141`，y `1995`
- 修复前后：`4055` -> `2851`

### T12

![T12 DPC repair crop](../figures/T12_a0034-LSYD4O2202_dpc_repair_crop.png)

- 候选坐标：x `843`，y `303`
- 修复前后：`3347` -> `819`

### T13

![T13 DPC repair crop](../figures/T13_a0035-dgw_048_dpc_repair_crop.png)

- 候选坐标：x `2106`，y `404`
- 修复前后：`15847` -> `698`

### T14

![T14 DPC repair crop](../figures/T14_a0040-_DSC5693_dpc_repair_crop.png)

- 候选坐标：x `611`，y `1298`
- 修复前后：`15892` -> `1295`

## 今天要记住的结论

1. DPC 的关键不是“看起来把图变漂亮”，而是避免单个异常像素污染后面的 Demosaic。
2. Bayer RAW 里必须按同色像素比较，不能直接用相邻像素判断坏点。
3. 中值适合修复孤立异常点，因为它不容易被单个极端值带偏。
4. 当前版本是学习用的保守候选检测；真正产品里通常还会结合暗场/亮场标定、温度、曝光和固定坏点表。
5. 对照 OpenISP 后要补充：DPC 的修复策略可以沿最小梯度方向选择邻居，以减少边缘被 median 抹平。

## 下一步

DPC 做完后，下一步可以进入最有成就感的一步：Demosaic。先实现 bilinear demosaic，把 Bayer RAW 变成第一张 RGB 图。
