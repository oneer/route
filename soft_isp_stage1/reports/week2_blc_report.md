# Week 2 BLC 学习报告

本次只做一个小闭环：读取 RAW metadata 里的 black level，按 Bayer 位置扣除黑电平，然后观察直方图和统计量的变化。

## BLC 做了什么

BLC 的全称是 Black Level Correction，中文可以理解为黑电平校正。RAW 数值里不只有真实光信号，还包含传感器和读出电路带来的基础偏置。这个偏置就是 black level。

本次实现的公式是：

```text
corrected = raw - black_level
corrected = clip(corrected, 0, white_level - black_level)
```

如果一张图的 black level 是 0，那么 BLC 前后应该几乎不变；如果 black level 不为 0，暗部会向 0 移动，后续 demosaic、AWB、颜色校正才是在真实光信号上继续做。

## 结果总表

| 样张 | Bayer | black level | white before | white after | p50 before | p50 after | mean before | mean after | 结论 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| S01 | BGGR | 0/0/0/0 | 4095 | 4095 | 546.00 | 546.00 | 671.84 | 671.84 | black level 为 0，BLC 是 identity case |
| S03 | RGGB | 1023/1023/1023/1023 | 13600 | 12577 | 1564.00 | 541.00 | 3405.88 | 2355.00 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| S05 | RGGB | 127/128/127/127 | 3398 | 3270-3271 | 149.00 | 22.00 | 524.30 | 397.05 | 暗部基线被扣除，RAW 数值回到真实信号起点 |

## 对比直方图

看图时重点看两件事：第一，after BLC 的分布是否整体左移；第二，暗部是否从 black level 附近移动到 0 附近。

### S01

![S01 BLC histogram compare](figures/S01_a0001-jmac_DSC1459_blc_hist_compare.png)

### S03

![S03 BLC histogram compare](figures/S03_a0003-NKIM_MG_8178_blc_hist_compare.png)

### S05

![S05 BLC histogram compare](figures/S05_a0005-jn_2007_05_10__564_blc_hist_compare.png)

## 分样张观察

### S01

- black level: `[0, 0, 0, 0]`
- BLC 前：min `2.00`，p50 `546.00`，p99 `1982.00`
- BLC 后：min `2.00`，p50 `546.00`，p99 `1982.00`

### S03

- black level: `[1023, 1023, 1023, 1023]`
- BLC 前：min `1013.00`，p50 `1564.00`，p99 `13824.00`
- BLC 后：min `0.00`，p50 `541.00`，p99 `12577.00`

### S05

- black level: `[127, 128, 127, 127]`
- BLC 前：min `121.00`，p50 `149.00`，p99 `3398.00`
- BLC 后：min `0.00`，p50 `22.00`，p99 `3271.00`

## 今天要记住的结论

1. BLC 不是调亮或调暗图片，而是把传感器的基线偏置扣掉。
2. black level 为 0 时，BLC 可以保留这个步骤，但结果应基本不变，用来验证流程没有破坏数据。
3. black level 不为 0 时，必须先扣除，再进入 demosaic/AWB；否则后面的颜色和亮度判断都会带着偏置。
4. BLC 后有效白电平变成 `white_level - black_level`；如果四通道 black level 不完全一样，有效白电平也会按 Bayer 位置略有差异。
