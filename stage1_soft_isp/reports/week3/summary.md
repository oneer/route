# Week 3 学习总结：Demosaic / AWB

## 本周学习闭环

| 项目 | 要求 |
|---|---|
| 目标 | 从 Bayer 恢复 RGB，并能分别诊断插值伪影和 AWB 场景假设失败 |
| 前置 | 确认 Bayer pattern、black level 和 DPC/LSC 输出仍在线性 RAW 域 |
| 运行前预测 | 指出真实采样值应该保留在哪里；预测大面积绿色、蓝天或混合光对 Gray World 的影响 |
| 最小实验 | 独立补全 8×8 bilinear；对 T01 做 Demosaic，对 T07 做 AWB 失败分析 |
| 验收 | 常量 Bayer 输出常量 RGB；采样值不被覆盖；至少固定一个 edge/texture crop |

```powershell
python exercises/week3_demosaic_todo.py
python scripts/08_apply_demosaic.py data/raw/T01_a0006-IMG_2787.dng `
  --out-dir outputs/tutorial/week3/demosaic `
  --report outputs/tutorial/week3/demosaic_report.md
python scripts/09_apply_awb.py data/raw/T07_a0020-jmac_MG_6225.dng `
  --out-dir outputs/tutorial/week3/awb `
  --report outputs/tutorial/week3/awb_report.md
```

先记录结构、假彩、拉链和 gain 预测，再查看参考结果。Malvar 与 OpenCV baseline 的来源见[参考文献](../references.md#week-3demosaic-与-awb)。

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

## 深度补强：Demosaic 伪影和 AWB 定量评价

Week3 已经能从 Bayer RAW 得到第一版 RGB，但“能出图”不等于 demosaic 和 AWB 已经可靠。这里需要增加两个评价框架：伪影检查和白平衡定量验证。

### 1. Demosaic 不能只看整体结构

Bilinear demosaic 的典型问题通常是局部问题，全图指标不一定敏感。

建议每张代表样张固定检查这些 crop：

| 伪影 | 典型区域 | 检查方法 |
|---|---|---|
| zipper effect | 高对比斜边、建筑边缘 | 100% crop + 边缘剖面 |
| false color | 黑白纹理、树枝、文字 | 看无色区域是否出现彩边 |
| moire | 细密重复纹理 | 放大 crop 或频谱观察 |
| blur | 毛发、树叶、织物 | 与 rawpy/OpenCV edge-aware 对比 |

报告里要明确：

```text
Bilinear 是 baseline，不是终点。
它能建立缺色插值直觉，但解释不了边缘方向选择和高频伪影控制。
```

### 2. AWB 不能只看全图 R/G、B/G 接近 1

Gray World 的全图均值接近灰，只能说明平均通道被拉平。它不能证明颜色准确。

更好的验证层次：

| 层次 | 评价方法 | 作用 |
|---|---|---|
| 全图 | R/G、B/G | 快速 sanity check |
| 灰色 ROI | 中性区域 R/G、B/G | 判断白平衡是否真让灰物体中性 |
| 色卡 | 灰阶 patch DeltaE | 标准定量评价 |
| 场景失败 | 大面积绿色/蓝天/混合光源 | 验证 Gray World 鲁棒性 |

如果没有 ColorChecker，至少要在报告中保留灰色 ROI 或低饱和 ROI 的分析，而不是只看全图均值。

### 3. Gray World 失败案例要显式列出

| 场景 | 为什么失败 | 改进方向 |
|---|---|---|
| 大面积草地/树叶 | 绿色主导全图均值 | 排除高饱和区域，使用灰点检测 |
| 大面积蓝天 | 蓝色主导均值 | 按亮度/饱和度筛灰点 |
| 室内混合光源 | 一个全局 gain 无法解释局部光源 | 分区 AWB 或时序/语义辅助 |
| 夜景彩灯 | 高亮彩色点污染统计 | 高光剔除和肤色保护 |

这样 Week3 才能从“AWB 后比例接近 1”推进到“知道 AWB 什么时候会失败”。

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
