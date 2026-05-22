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

## 结果总表

| 样张 | Bayer | 候选数 | 占比 | R | Gr | Gb | B | 最大修复幅度 | 观察 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| S01 | BGGR | 371 | 0.0001 | 0 | 191 | 176 | 4 | 2696.00 | 候选点很少，符合保守检测预期 |
| S03 | RGGB | 14125 | 0.0014 | 1374 | 4257 | 4171 | 4323 | 9323.00 | 候选点偏多，需要看 mask 是否落在强边缘或高光区域 |
| S05 | RGGB | 580 | 0.0001 | 0 | 207 | 255 | 118 | 2398.00 | 候选点很少，符合保守检测预期 |

## Mask 预览

红色点表示 DPC 候选点。由于坏点通常很稀疏，全图上可能只看到少量红点；这恰好是正常现象。

### S01

![S01 DPC mask](figures/S01_a0001-jmac_DSC1459_dpc_mask_overlay.png)

### S03

![S03 DPC mask](figures/S03_a0003-NKIM_MG_8178_dpc_mask_overlay.png)

### S05

![S05 DPC mask](figures/S05_a0005-jn_2007_05_10__564_dpc_mask_overlay.png)

## 局部修复对比

每张图选一个修复幅度最大的候选点附近做 crop。左边是 DPC 前，中间是 DPC 后，右边是候选 mask。

### S01

![S01 DPC repair crop](figures/S01_a0001-jmac_DSC1459_dpc_repair_crop.png)

- 候选坐标：x `1957`，y `1900`
- 修复前后：`3509` -> `813`

### S03

![S03 DPC repair crop](figures/S03_a0003-NKIM_MG_8178_dpc_repair_crop.png)

- 候选坐标：x `2018`，y `457`
- 修复前后：`12577` -> `3254`

### S05

![S05 DPC repair crop](figures/S05_a0005-jn_2007_05_10__564_dpc_repair_crop.png)

- 候选坐标：x `2266`，y `1647`
- 修复前后：`863` -> `3261`

## 今天要记住的结论

1. DPC 的关键不是“看起来把图变漂亮”，而是避免单个异常像素污染后面的 Demosaic。
2. Bayer RAW 里必须按同色像素比较，不能直接用相邻像素判断坏点。
3. 中值适合修复孤立异常点，因为它不容易被单个极端值带偏。
4. 当前版本是学习用的保守候选检测；真正产品里通常还会结合暗场/亮场标定、温度、曝光和固定坏点表。

## 下一步

DPC 做完后，下一步可以进入最有成就感的一步：Demosaic。先实现 bilinear demosaic，把 Bayer RAW 变成第一张 RGB 图。
