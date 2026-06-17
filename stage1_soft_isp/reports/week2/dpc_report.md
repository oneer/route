# Week 2-2 DPC 学习报告

## 工程学习模板补全

### 1. 一句话定位
DPC 用来检测并修复 sensor 中异常偏亮或偏暗的孤立像素，避免坏点在 demosaic、gamma、锐化后被放大成明显亮点、黑点或彩点。

### 2. Pipeline 位置
```text
RAW -> BLC -> DPC -> LSC -> AWB/WB gain -> CFA -> CCM -> Tone/Gamma
```
DPC 通常放在 BLC 后、CFA 前。BLC 后数值基线更干净；CFA 前处理可以避免一个坏点被插值扩散成一片彩色伪影。

### 3. 输入输出定义
| 项目 | 定义 |
|---|---|
| 输入 | BLC 后的 Bayer RAW |
| 输出 | Bayer RAW，尺寸、bit depth、Bayer pattern 不变 |
| 数据范围 | 通常为 `0..white_level-black_level` |
| 通道处理 | 必须按同色邻域比较，不能直接拿相邻异色像素判断 |
| 依赖信息 | Bayer pattern、阈值参数、可选坏点表、ISO/温度相关 tuning |

### 4. 问题来源
坏点可能来自 sensor 制程缺陷、热噪声、长期老化或读出异常。它们常表现为单个像素远高于或远低于周围同色像素。因为 Bayer 相邻像素颜色不同，坏点检测必须回到同色采样网格上判断。

### 5. 核心思想
DPC 利用局部同色像素的连续性：正常像素通常和周围同色邻域接近，孤立异常点会和所有同色邻居差异很大。简单版用 median 修复，OpenISP 展示了沿最小梯度方向修复以保护边缘。

### 6. 算法流程
```text
1. 取当前像素 P。
2. 找到周围同色邻域。
3. 计算 P 与邻域代表值的差异。
4. 如果差异超过阈值，标记为坏点候选。
5. 用 median、mean 或最小梯度方向插值替换。
6. 否则保留原值。
```

### 7. 公式解释
```text
local_median = median(same_color_neighbors)
residual = abs(P - local_median)
threshold = max(min_delta, median(residual) + mad_k * MAD(residual))
out = local_median if residual > threshold else P
```
OpenISP 的固定阈值版本更像 tuning 参数，本项目的 MAD 阈值更自适应。

### 8. 参数说明
| 参数 | 作用 | 增大效果 | 减小效果 | 风险 |
|---|---|---|---|---|
| min_delta | 最小检测差异 | 少误杀纹理 | 更敏感 | 太大漏检，太小误检噪声 |
| mad_k | MAD 阈值倍数 | 更保守 | 更激进 | 太大坏点残留，太小误伤纹理 |
| repair_mode | 修复方式 | gradient 更保边，median 更稳健 | 取决于模式 | 方向判断错会引入结构伪影 |
| thres | OpenISP 固定阈值 | tuning 更可控 | 更敏感 | 难适配不同 ISO/曝光 |

### 9. OpenISP 源码拆解
OpenISP `dpc.py` 在完整 Bayer 上取隔 2 像素的 5x5 同色邻域，用 `p0..p8` 判断中心点是否和所有同色邻居都差异过大。修复支持 `mean` 和 `gradient`：后者比较垂直、水平、对角方向梯度，选择梯度最小的方向平均，减少边缘被抹平。

### 10. 边界条件
DPC 需要 3x3 同色邻域或原图 5x5 范围，因此最外侧一到两圈像素通常跳过或直接拷贝。实现时还要避免修复值溢出，坏点 mask 不能把高光边缘、星点、细线纹理都当成坏点。

### 11. 效果对比
本报告已有 mask 预览和局部修复对比。验证时要看三件事：候选点数量是否合理、红色 mask 是否集中在孤立异常点、修复后 crop 是否消除亮点同时没有抹掉纹理。

### 12. 常见伪影和风险
阈值太低会误杀星点、细线、纹理和高光边缘；阈值太高会漏掉坏点。median 修复稳定但可能抹边，gradient 修复保边但更依赖方向判断。

### 13. 与其他模块的关系
DPC 放在 CFA 前可以防止坏点扩散。它也会影响后续降噪和锐化：坏点没修会被锐化放大，误修太多又会让纹理变糊。BLC 不准时，暗部 residual 会偏，DPC 阈值也会被带偏。

### 14. 简化实现
```python
def dpc_pixel(p, neigh, threshold):
    med = np.median(neigh)
    return med if abs(float(p) - med) > threshold else p
```

### 15. 工程实现注意点
产品 ISP 常结合静态坏点表、动态坏点检测、ISO/温度阈值、line buffer 和硬件友好的方向插值。OpenISP 的 `gradient` 模式就是从教学版 median 走向工程版边缘保护的好桥。

### 16. 小结
DPC 的本质是 RAW 域异常点检测与替换。它要在坏点残留和纹理误杀之间平衡，核心参数是阈值和修复模式；它影响 CFA、降噪和锐化，是前端清洁度非常关键的一步。

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
