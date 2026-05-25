# Week 3 学习总结：Demosaic / AWB

Week3 的目标是把前面已经校正过的 Bayer RAW，推进到“第一版可观看 RGB”的阶段。本周不追求最终颜色完全准确，而是建立两个核心直觉：

1. Demosaic 解决的是“每个像素缺两个颜色”的问题。
2. AWB 解决的是“RGB 三通道受光源和传感器响应影响而偏色”的问题。

## 本周 Pipeline

```text
RAW
  -> BLC
  -> DPC
  -> LSC
  -> Bilinear Demosaic
  -> Gray World AWB
  -> Preview PNG
```

## 已完成交付物

| 模块 | 代码 | 报告 | 输出 |
|---|---|---|---|
| Demosaic | `soft_isp/demosaic.py`、`scripts/08_apply_demosaic.py` | `reports/week3/demosaic_report.md` | `reports/figures/*_demosaic_*.png/json` |
| AWB | `soft_isp/awb.py`、`scripts/09_apply_awb.py` | `reports/week3/awb_report.md` | `reports/figures/*_awb_*.png/json` |

## Demosaic 学到了什么

Bayer RAW 是单通道二维数组，但它按位置交替记录 R/G/B。Demosaic 的任务不是调色，而是补齐每个像素缺失的颜色值。

本周实现的是 bilinear demosaic。它的核心公式是：

```text
C_hat = conv(RAW * M_C, K) / conv(M_C, K)
```

其中 `C` 可以是 R、G、B，`M_C` 是该颜色的采样 mask，`K` 是 3x3 加权核。真实采样的位置保留原值，缺失位置用周围同色像素加权平均。

## AWB 学到了什么

AWB 的输入是 Demosaic 后的线性 RGB。它通过给 R/G/B 乘不同 gain 来减轻偏色。

本周实现的是 Gray World AWB：

```text
R_gain = G_mean / R_mean
G_gain = 1
B_gain = G_mean / B_mean
```

它的假设是：一张自然图像如果包含足够多颜色，平均颜色应该接近灰色。这个方法简单、可解释，但遇到大面积单色场景或混合光源时容易失败。

## 本周如何验证

1. Demosaic 后数组形状从 `(H, W)` 变成 `(H, W, 3)`。
2. Demosaic 输出图能看到真实图像结构，不是黑图或花屏。
3. AWB 后 `R/G` 和 `B/G` 通道均值比例比 AWB 前更接近 1。
4. AWB 前后对比图能看到偏色被减轻。
5. 与 rawpy reference 对比时，只比较结构和偏色趋势，不要求完全一致。

## 本周局限

1. Bilinear demosaic 不判断边缘方向，边缘会糊，纹理区可能有假彩色。
2. Gray World AWB 只给整张图一个全局 gain，不能处理混合光源。
3. 当前输出仍然不是最终照片，因为还没有 CCM、Gamma 和 Tone Mapping。

## OpenISP 对 Week3 的启发

OpenISP 的 `cfa.py` 使用 Malvar 类插值核，比当前 bilinear 更进一步：它不只是对同色邻域做平均，还会用邻域梯度和跨通道信息修正缺失颜色。这说明 bilinear 更适合作为 baseline，而不是终点。

OpenISP 的 `awb.py` 则展示了另一种白平衡位置：在 Bayer RAW 域直接对 R/Gr/Gb/B 位置乘 gain。当前项目是在 demosaic 后用 Gray World 估计 RGB gain，两者都合理，但回答的问题不同：

- RAW 域 WB gain 更接近 ISP 前端参数控制；
- RGB 域 Gray World 更适合学习自动估计和验证通道均值是否回到中性。

后续如果升级 Week3，优先做 `Bilinear vs Malvar` 对比实验，并增加假彩/边缘 crop，而不是只看全图 PSNR。

更具体地说，Week3 可以形成三层学习：

| 层级 | Demosaic / AWB 做法 | 学习目标 |
|---|---|---|
| baseline | Bilinear Demosaic + RGB 域 Gray World AWB | 建立“Bayer 缺色插值”和“通道 gain 白平衡”的基本直觉 |
| OpenISP 对照 | `cfa.py` Malvar + `awb.py` Bayer RAW 域 WB gain | 理解传统 ISP 会在 RAW/Bayer 位置上做更细的插值和 gain 控制 |
| 后续升级 | Malvar/AHD 对比、灰点/白点 AWB、混合光源失败分析 | 从“能出图”走向“能解释边缘、假彩和白平衡失败” |

报告里需要特别补一句：**Bilinear 简单不是问题，问题是如果只停在 Bilinear，就无法解释假彩、拉链边和边缘方向选择；OpenISP 的 Malvar 正好是下一步桥梁。**

## 下一步

Week4 可以进入 CCM / Gamma / Tone。推荐顺序是：

```text
CCM：把相机 RGB 映射到更接近标准 sRGB 的颜色空间
Gamma：把线性光信号变成人眼更自然的显示亮度
Tone Mapping：压缩高光和整体动态范围
```
