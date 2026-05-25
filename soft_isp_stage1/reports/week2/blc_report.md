# Week 2 BLC 学习报告

## 工程学习模板补全

### 1. 一句话定位
BLC 用来把 RAW 里的黑电平偏置扣掉，让“没有光”的位置回到 0 附近，避免暗部偏灰、偏色或后续模块在错误基线上继续处理。

### 2. Pipeline 位置
```text
RAW metadata -> BLC -> DPC -> LSC -> AWB/WB gain -> CFA -> CCM -> Tone/Gamma
```
BLC 应尽量靠前，因为 DPC、LSC、AWB、CFA 都默认输入已经是有效光信号。如果 BLC 放晚了，暗部统计、坏点阈值和 AWB gain 都会被 black level 偏置影响。

### 3. 输入输出定义
| 项目 | 定义 |
|---|---|
| 输入 | Bayer RAW，常见 RAW10/RAW12/RAW14/RAW16，本项目来自 DNG/rawpy |
| 输出 | Bayer RAW，尺寸和 Bayer pattern 不变 |
| 数据范围 | 输入约为 `black_level..white_level`，输出约为 `0..white_level-black_level` |
| 通道处理 | 按 R/Gr/Gb/B 四个 Bayer 位置分别处理 |
| 依赖信息 | `black_level_per_channel`、`raw_pattern`、`white_level`，工程版还可能依赖 OB 区统计和 tuning 参数 |

### 4. 问题来源
即使镜头完全遮黑，sensor 和读出链路也可能产生暗电流、ADC offset、黑位钳位偏差。结果是纯黑 RAW 不等于 0，而是围绕某个 black level。这个偏置如果不扣掉，会让暗部看起来发灰，并影响后续颜色和亮度统计。

### 5. 核心思想
BLC 是校正模块，不是增强模块。它的核心是假设每个 Bayer 通道都有一个黑位基线，把这个基线从对应像素中扣掉，再把负数 clamp 到 0。

### 6. 算法流程
```text
1. 读取 black level 和 Bayer pattern。
2. 根据 2x2 Bayer 位置生成 per-pixel black map。
3. 用 int32 做 raw - black_map，避免 uint 下溢。
4. 将结果 clamp 到 0..有效白电平。
5. 输出仍然保持 Bayer RAW，交给 DPC/LSC。
```

### 7. 公式解释
```text
out(y, x) = clamp(raw(y, x) - black_level[channel(y, x)], 0, white_level - black_level[channel(y, x)])
```
其中 `channel(y, x)` 由 Bayer pattern 决定。OpenISP 的符号约定可能写成 `raw + bl_*`，但目标同样是把黑位校正到 0 附近。

### 8. 参数说明
| 参数 | 作用 | 增大效果 | 减小效果 | 风险 |
|---|---|---|---|---|
| black_level | 每通道黑位偏置 | 扣得更多，暗部更黑 | 扣得更少，暗部偏灰 | 过大导致暗部截断，过小导致黑位残留 |
| white_level | 有效白电平上限 | 保留更高亮度范围 | 更容易压缩高光 | 设置错误会影响归一化和 tone mapping |
| alpha/beta | OpenISP 绿色通道串扰修正 | Gr/Gb 受 R/B 影响更强 | 修正更弱 | tuning 不准会造成绿色通道偏差 |

### 9. OpenISP 源码拆解
OpenISP BLC 的入口接收 `parameter = [bl_r, bl_gr, bl_gb, bl_b, alpha, beta]` 和 Bayer pattern 分支。主循环按 R/Gr/Gb/B 位置加对应 offset，并对 Gr/Gb 额外加入 `alpha * R / 256` 或 `beta * B / 256`。它展示的是工程模块接口：参数由外部 tuning 系统给出，而不是从 DNG metadata 自动读取。

### 10. 边界条件
BLC 不需要邻域，所以图像边缘不特殊。真正要注意的是数值边界：必须先转有符号或更高 bit depth 再减法，避免 uint underflow；减完后要 clamp；black level 为 0 时输出应接近 identity，用来检查流程没有误伤数据。

### 11. 效果对比
本报告已有“结果总表”“视觉前后对比”“对比直方图”。看 BLC 是否有效，重点不是照片是否好看，而是暗部 histogram 是否整体左移、black level 非 0 的样张是否回到 0 附近、black level 为 0 的样张是否基本不变。

### 12. 常见伪影和风险
BLC 过强会造成暗部 clipping、黑色块死黑、低亮纹理消失；BLC 过弱会造成暗部发灰、暗部偏色、AWB 统计被污染。四通道 black level 不一致时，如果只用单一 offset，可能让暗部出现色偏。

### 13. 与其他模块的关系
BLC 影响 DPC 的 residual、LSC 的增益后噪声、AWB 的中性统计和 CFA 后的暗部颜色。它是后续模块的数值地基，地基偏了，后面越调越像在补偿错误。

### 14. 简化实现
```python
def blc(raw, black_map, white):
    out = raw.astype("int32") - black_map.astype("int32")
    return np.clip(out, 0, white).astype("uint16")
```

### 15. 工程实现注意点
真实 ISP 可能使用 OB 区统计、温度/ISO 相关黑位表、per-channel tuning、fixed-point 饱和运算和硬件 clamp。OpenISP 的 `alpha/beta` 提醒我们：工程 BLC 有时还会顺手处理绿色通道串扰或读出通道耦合。

### 16. 小结
BLC 的本质是 RAW 域基线校正。它越早做越好，最重要的参数是 per-channel black level，最常见风险是暗部截断或黑位残留。理解 BLC 时要同时看 metadata 学习版和 OpenISP tuning 版：前者自动、可复现，后者更接近产品 ISP 接口。

本次只做一个小闭环：读取 RAW metadata 里的 black level，按 Bayer 位置扣除黑电平，然后观察直方图和统计量的变化。

## BLC 做了什么

BLC 的全称是 Black Level Correction，中文可以理解为黑电平校正。RAW 数值里不只有真实光信号，还包含传感器和读出电路带来的基础偏置。这个偏置就是 black level。

本次实现的公式是：

```text
corrected = raw - black_level
corrected = clip(corrected, 0, white_level - black_level)
```

如果一张图的 black level 是 0，那么 BLC 前后应该几乎不变；如果 black level 不为 0，暗部会向 0 移动，后续 demosaic、AWB、颜色校正才是在真实光信号上继续做。

## 和 OpenISP BLC 的对照

当前项目的 BLC 是一个“metadata 驱动的最小正确实现”：从 DNG/rawpy 读取 `black_level_per_channel` 和 `raw_pattern`，生成逐像素 black map，然后执行减法和 clip。它的重点是把 RAW 数值从“带偏置的传感器读数”变成“以 0 为起点的有效光信号”。

OpenISP 的 `openisp/blc.py` 则更像一个工程 ISP 模块接口。它不直接从 DNG metadata 取 black level，而是接收一组外部参数：

```text
[bl_r, bl_gr, bl_gb, bl_b, alpha, beta]
```

前四个参数对应 R、Gr、Gb、B 四个 Bayer 位置的黑电平偏移；`alpha` 和 `beta` 是额外的绿色通道串扰修正项。以 RGGB 为例，OpenISP 的核心逻辑可以写成：

```text
R  = R_raw  + bl_r
B  = B_raw  + bl_b
Gr = Gr_raw + bl_gr + alpha * R / 256
Gb = Gb_raw + bl_gb + beta  * B / 256
```

这比我们当前实现多了两层工程含义：

1. **参数来源不同。** 我们依赖 DNG metadata，适合真实 DNG 学习闭环；OpenISP 假设黑电平和串扰参数已经由外部配置、标定或 tuning 系统给出。
2. **BLC 不一定只是减常数。** OpenISP 里 Gr/Gb 还会根据 R/B 做一个比例修正，说明工程 BLC 可能顺手处理读出通道串扰、OB 统计偏差或绿色通道不一致。

两者对比如下：

| 维度 | 当前项目 BLC | OpenISP BLC | 学习结论 |
|---|---|---|---|
| 参数来源 | rawpy/DNG metadata | 外部参数列表 `[bl_r, bl_gr, bl_gb, bl_b, alpha, beta]` | DNG 学习版重在自动读取，工程模块重在可 tuning |
| Bayer 位置 | `raw_pattern` 生成 black map | 手写 `rggb/bggr/gbrg/grbg` 四套分支 | 两种方式本质相同，都是按 2x2 Bayer 位置处理 |
| 黑电平处理 | `raw - black_level` | `raw + bl_*`，通常 `bl_*` 可表示负偏移 | 符号约定不同，目标都是把黑位移到 0 附近 |
| 绿色通道修正 | 未做 | `Gr += alpha * R / 256`，`Gb += beta * B / 256` | 工程 BLC 可能包含串扰/通道耦合补偿 |
| 输出范围 | clip 到 `0..white_level-black_level` | clip 到 `0..clip` | 我们显式更新有效白电平，OpenISP 使用统一 clip 参数 |
| 数据类型 | int32 中间计算，uint16 输出 | int16 中间数组，clip 后输出 | 中间计算要避免 underflow/overflow |

因此，当前 BLC 报告不能只停留在“扣 black level”。更完整的理解是：

```text
学习版 BLC：metadata -> black map -> raw - black -> 更新有效 white
工程版 BLC：tuning 参数 -> per-Bayer-position offset -> 可选串扰修正 -> clip
```

后续如果要把当前 BLC 向 OpenISP 靠近，最小升级不是直接照搬代码，而是增加一个可选的 `green_crosstalk` 实验参数，观察 `alpha/beta` 对 Gr/Gb 均值、暗部中性和 AWB gain 的影响。

## 结果总表

| 样张 | Bayer | black level | white before | white after | p50 before | p50 after | mean before | mean after | 结论 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| T01 | RGGB | 1024/1024/1023/1024 | 16000 | 14976-14977 | 2410.00 | 1386.00 | 2954.50 | 1930.56 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T02 | RGGB | 127/128/128/127 | 4000 | 3872-3873 | 394.00 | 267.00 | 392.42 | 264.92 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T03 | RGGB | 128/128/127/128 | 4095 | 3967-3968 | 544.00 | 417.00 | 604.79 | 477.04 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T04 | RGGB | 128/128/127/127 | 4095 | 3967-3968 | 218.00 | 91.00 | 365.07 | 237.57 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T05 | RGGB | 127/126/126/127 | 4000 | 3873-3874 | 374.00 | 247.00 | 458.89 | 332.39 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T06 | RGGB | 128/128/127/127 | 4095 | 3967-3968 | 382.00 | 255.00 | 474.31 | 346.81 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T07 | RGGB | 128/128/128/128 | 3692 | 3564 | 357.00 | 229.00 | 698.73 | 570.73 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T08 | RGGB | 1024/1024/1024/1024 | 16000 | 14976 | 2074.00 | 1050.00 | 2190.95 | 1166.90 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T09 | RGGB | 127/128/127/128 | 3692 | 3564-3565 | 232.00 | 105.00 | 292.13 | 164.63 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T10 | RGGB | 128/128/127/127 | 4095 | 3967-3968 | 298.00 | 170.00 | 378.73 | 251.23 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T11 | BGGR | 0/0/0/0 | 4095 | 4095 | 163.00 | 163.00 | 306.21 | 306.21 | black level 为 0，BLC 是 identity case |
| T12 | GBRG | 128/128/128/128 | 3711 | 3583 | 201.00 | 73.00 | 310.46 | 182.46 | 暗部基线被扣除，RAW 数值回到真实信号起点 |
| T13 | RGGB | 0/0/0/0 | 15892 | 15892 | 1166.00 | 1166.00 | 3149.35 | 3120.66 | black level 为 0，BLC 是 identity case |
| T14 | RGGB | 0/0/0/0 | 15892 | 15892 | 1541.00 | 1541.00 | 2205.75 | 2203.62 | black level 为 0，BLC 是 identity case |

## 视觉前后对比

这组图把 BLC 前后的 RAW 当成灰度图显示，并用同一个显示上限做缩放。重点不是看颜色，而是看暗部基线有没有被扣掉。当前这批样张大多 black level 为 0，所以视觉上通常几乎不变；这反而说明 BLC 在这些样张上是一个 identity case。

### T01

![T01 BLC visual compare](../figures/T01_a0006-IMG_2787_blc_visual_compare.png)

### T02

![T02 BLC visual compare](../figures/T02_a0008-WP_CRW_3959_blc_visual_compare.png)

### T03

![T03 BLC visual compare](../figures/T03_a0010-jmac_MG_4807_blc_visual_compare.png)

### T04

![T04 BLC visual compare](../figures/T04_a0012-kme_143_blc_visual_compare.png)

### T05

![T05 BLC visual compare](../figures/T05_a0014-WP_CRW_6320_blc_visual_compare.png)

### T06

![T06 BLC visual compare](../figures/T06_a0018-kme_234_blc_visual_compare.png)

### T07

![T07 BLC visual compare](../figures/T07_a0020-jmac_MG_6225_blc_visual_compare.png)

### T08

![T08 BLC visual compare](../figures/T08_a0022-IMG_2380_blc_visual_compare.png)

### T09

![T09 BLC visual compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_blc_visual_compare.png)

### T10

![T10 BLC visual compare](../figures/T10_a0026-kme_391_blc_visual_compare.png)

### T11

![T11 BLC visual compare](../figures/T11_a0033-KE_-2590_blc_visual_compare.png)

### T12

![T12 BLC visual compare](../figures/T12_a0034-LSYD4O2202_blc_visual_compare.png)

### T13

![T13 BLC visual compare](../figures/T13_a0035-dgw_048_blc_visual_compare.png)

### T14

![T14 BLC visual compare](../figures/T14_a0040-_DSC5693_blc_visual_compare.png)


## 对比直方图

看图时重点看两件事：第一，after BLC 的分布是否整体左移；第二，暗部是否从 black level 附近移动到 0 附近。

### T01

![T01 BLC histogram compare](../figures/T01_a0006-IMG_2787_blc_hist_compare.png)

### T02

![T02 BLC histogram compare](../figures/T02_a0008-WP_CRW_3959_blc_hist_compare.png)

### T03

![T03 BLC histogram compare](../figures/T03_a0010-jmac_MG_4807_blc_hist_compare.png)

### T04

![T04 BLC histogram compare](../figures/T04_a0012-kme_143_blc_hist_compare.png)

### T05

![T05 BLC histogram compare](../figures/T05_a0014-WP_CRW_6320_blc_hist_compare.png)

### T06

![T06 BLC histogram compare](../figures/T06_a0018-kme_234_blc_hist_compare.png)

### T07

![T07 BLC histogram compare](../figures/T07_a0020-jmac_MG_6225_blc_hist_compare.png)

### T08

![T08 BLC histogram compare](../figures/T08_a0022-IMG_2380_blc_hist_compare.png)

### T09

![T09 BLC histogram compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_blc_hist_compare.png)

### T10

![T10 BLC histogram compare](../figures/T10_a0026-kme_391_blc_hist_compare.png)

### T11

![T11 BLC histogram compare](../figures/T11_a0033-KE_-2590_blc_hist_compare.png)

### T12

![T12 BLC histogram compare](../figures/T12_a0034-LSYD4O2202_blc_hist_compare.png)

### T13

![T13 BLC histogram compare](../figures/T13_a0035-dgw_048_blc_hist_compare.png)

### T14

![T14 BLC histogram compare](../figures/T14_a0040-_DSC5693_blc_hist_compare.png)

## 分样张观察

### T01

- black level: `[1024, 1024, 1023, 1024]`
- BLC 前：min `1044.00`，p50 `2410.00`，p99 `7018.00`
- BLC 后：min `20.00`，p50 `1386.00`，p99 `5994.00`

### T02

- black level: `[127, 128, 128, 127]`
- BLC 前：min `114.00`，p50 `394.00`，p99 `740.00`
- BLC 后：min `0.00`，p50 `267.00`，p99 `612.00`

### T03

- black level: `[128, 128, 127, 128]`
- BLC 前：min `118.00`，p50 `544.00`，p99 `2318.00`
- BLC 后：min `0.00`，p50 `417.00`，p99 `2190.00`

### T04

- black level: `[128, 128, 127, 127]`
- BLC 前：min `121.00`，p50 `218.00`，p99 `1441.00`
- BLC 后：min `0.00`，p50 `91.00`，p99 `1313.00`

### T05

- black level: `[127, 126, 126, 127]`
- BLC 前：min `126.00`，p50 `374.00`，p99 `2357.00`
- BLC 后：min `0.00`，p50 `247.00`，p99 `2230.00`

### T06

- black level: `[128, 128, 127, 127]`
- BLC 前：min `130.00`，p50 `382.00`，p99 `1218.00`
- BLC 后：min `3.00`，p50 `255.00`，p99 `1090.00`

### T07

- black level: `[128, 128, 128, 128]`
- BLC 前：min `120.00`，p50 `357.00`，p99 `3692.00`
- BLC 后：min `0.00`，p50 `229.00`，p99 `3564.00`

### T08

- black level: `[1024, 1024, 1024, 1024]`
- BLC 前：min `941.00`，p50 `2074.00`，p99 `4638.00`
- BLC 后：min `0.00`，p50 `1050.00`，p99 `3614.00`

### T09

- black level: `[127, 128, 127, 128]`
- BLC 前：min `97.00`，p50 `232.00`，p99 `1043.00`
- BLC 后：min `0.00`，p50 `105.00`，p99 `915.00`

### T10

- black level: `[128, 128, 127, 127]`
- BLC 前：min `124.00`，p50 `298.00`，p99 `1260.00`
- BLC 后：min `0.00`，p50 `170.00`，p99 `1133.00`

### T11

- black level: `[0, 0, 0, 0]`
- BLC 前：min `0.00`，p50 `163.00`，p99 `1940.00`
- BLC 后：min `0.00`，p50 `163.00`，p99 `1940.00`

### T12

- black level: `[128, 128, 128, 128]`
- BLC 前：min `119.00`，p50 `201.00`，p99 `1495.00`
- BLC 后：min `0.00`，p50 `73.00`，p99 `1367.00`

### T13

- black level: `[0, 0, 0, 0]`
- BLC 前：min `26.00`，p50 `1166.00`，p99 `16383.00`
- BLC 后：min `26.00`，p50 `1166.00`，p99 `15892.00`

### T14

- black level: `[0, 0, 0, 0]`
- BLC 前：min `21.00`，p50 `1541.00`，p99 `15891.00`
- BLC 后：min `21.00`，p50 `1541.00`，p99 `15891.00`

## 今天要记住的结论

1. BLC 不是调亮或调暗图片，而是把传感器的基线偏置扣掉。
2. black level 为 0 时，BLC 可以保留这个步骤，但结果应基本不变，用来验证流程没有破坏数据。
3. black level 不为 0 时，必须先扣除，再进入 demosaic/AWB；否则后面的颜色和亮度判断都会带着偏置。
4. BLC 后有效白电平变成 `white_level - black_level`；如果四通道 black level 不完全一样，有效白电平也会按 Bayer 位置略有差异。
5. 对照 OpenISP 后要记住：工程 BLC 还可能包含 per-channel tuning、绿色通道串扰修正和 fixed-point/clip 约定，不只是一个固定减法。
