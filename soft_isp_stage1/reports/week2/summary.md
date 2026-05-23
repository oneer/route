# Week 2 学习总结：BLC / DPC

Week2 的目标是做 RAW 前端校正。前端校正发生在 Demosaic 之前，仍然工作在单通道 Bayer RAW 上。本周已经完成 BLC 和 DPC 两个模块；LSC 在路线里属于 Week2 范围，但当前还没有实现，建议后续作为单独小闭环补齐。

## 本周 Pipeline 位置

```text
RAW
  -> BLC：扣除传感器黑电平偏置
  -> DPC：检测并修复坏点候选
  -> 后续 Demosaic / AWB
```

## 已完成交付物

| 模块 | 代码 | 报告 | 输出 |
|---|---|---|---|
| BLC | `soft_isp/blc.py`、`scripts/06_apply_blc.py` | `reports/week2/blc_report.md` | `reports/figures/*_blc_*.png/json` |
| DPC | `soft_isp/dpc.py`、`scripts/07_apply_dpc.py` | `reports/week2/dpc_report.md` | `reports/figures/*_dpc_*.png/json` |

## BLC 学到了什么

BLC 的全称是 Black Level Correction，黑电平校正。RAW 像素值里包含真实光信号，也包含传感器和读出电路的基线偏置。这个偏置就是 black level。

本周实现的核心公式是：

```text
corrected = raw - black_level
corrected = clip(corrected, 0, white_level - black_level)
```

如果 black level 为 0，BLC 前后应该基本不变；如果 black level 不为 0，暗部会整体向 0 移动。BLC 后有效白电平也要同步变成 `white_level - black_level`。

## DPC 学到了什么

DPC 的全称是 Dead Pixel Correction，坏点检测与修复。它的目标不是让图马上变好看，而是避免孤立异常点在后续 Demosaic 中扩散成彩色伪影。

Bayer RAW 中相邻像素不是同色，所以 DPC 不能直接拿上下左右像素比较。本周做法是：

```text
按 Bayer pattern 拆成 R / Gr / Gb / B 四个同色平面
  -> 每个同色平面做 3x3 median
  -> residual = abs(pixel - local_median)
  -> residual 超过阈值则标记为坏点候选
  -> 用 local_median 替换候选点
```

阈值由两部分共同决定：

```text
threshold = max(min_delta, median(residual) + mad_k * MAD(residual))
```

这样做可以同时保留一个固定最低门槛，并根据图像局部噪声水平自适应调整。

## 本周验证标准

1. BLC 后暗部基线应向 0 移动。
2. black level 为 0 的样张应基本不变，用来验证流程没有破坏数据。
3. DPC 候选点数量应很稀疏，不能大面积误检。
4. DPC mask 要叠到图上看，确认候选点是否集中在强边缘、高光或纹理区域。
5. DPC 修复 crop 要检查修复前后是否合理。

## 本周局限

1. 当前 DPC 是学习用候选检测，不是工厂坏点表。
2. 强边缘、高光饱和、纹理区域可能被误检。
3. 当前还没有做 LSC。镜头暗角和色彩阴影仍可能影响后续 AWB。
4. BLC/DPC 都在 Bayer RAW 上工作，不能用最终视觉效果单独评价。

## 为什么 LSC 后续还要补

LSC 是 Lens Shading Correction，镜头阴影校正。它主要解决画面边缘变暗、不同颜色通道边缘响应不一致的问题。如果不做 LSC，AWB 可能被边缘色偏影响，CCM 也可能在不同位置表现不一致。

但 LSC 通常需要 flat-field 标定图或可靠的估计策略。当前数据集没有专门的均匀白场标定图，所以建议后续先做一个“简化版径向 LSC / 低频拟合 LSC”实验，而不是把它混进 BLC/DPC 的闭环里。

## 和 Week3 的关系

```text
BLC 不干净 -> Demosaic 会把黑位偏置插值到 RGB
DPC 不干净 -> Demosaic 会把坏点扩散成彩色伪影
LSC 不干净 -> AWB 会受到位置相关亮度/色偏影响
```

一句话总结：Week2 是在给 Demosaic 准备更干净的 RAW 输入。
