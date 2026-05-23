# Week 3 学习总结：Demosaic / AWB

Week3 的目标是把前面已经校正过的 Bayer RAW，推进到“第一版可观看 RGB”的阶段。本周不追求最终颜色完全准确，而是建立两个核心直觉：

1. Demosaic 解决的是“每个像素缺两个颜色”的问题。
2. AWB 解决的是“RGB 三通道受光源和传感器响应影响而偏色”的问题。

## 本周 Pipeline

```text
RAW
  -> BLC
  -> DPC
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

## 下一步

Week4 可以进入 CCM / Gamma / Tone。推荐顺序是：

```text
CCM：把相机 RGB 映射到更接近标准 sRGB 的颜色空间
Gamma：把线性光信号变成人眼更自然的显示亮度
Tone Mapping：压缩高光和整体动态范围
```
