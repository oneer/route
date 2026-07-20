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

Demosaic 和 AWB 都会改变颜色外观，但职责不同：

| 模块 | 它解决什么 | 为什么需要 | 做错后的典型现象 | 应该怎样验证 |
|---|---|---|---|---|
| Demosaic | 从 Bayer 的稀疏颜色采样估计完整线性 RGB | 每个传感器像素只测到一种颜色，不能直接形成 RGB | Bayer pattern 错导致整图串色；插值不佳导致 zipper、false color、moire 和细节模糊 | 先测 shape、常量图和真实采样值保留，再固定斜边/文字/纹理 crop；不要用最终颜色判断插值正确性 |
| AWB estimation | 根据场景统计估计 R/G/B gain | 光源光谱和传感器响应会让中性物体通道不相等 | 大面积草地、蓝天、彩灯或混合光会使 Gray World 误判 | 排除过暗/饱和像素，检查中性 ROI、gain 合理范围和失败场景，不只看全图均值是否相等 |
| WB gain application | 把已经得到的 gain 应用到 RAW 或线性 RGB | 估计结果只有正确作用在对应通道和线性数据域才有效 | 通道映射错会偏色；gain 后 clip 会丢高光颜色；Gamma 后应用会破坏线性关系 | identity gain、单通道小数组、clip 比例和 RAW 域/RGB 域对照 |

因此，“Demosaic 后偏绿”不自动说明插值错，“AWB 后 R/G、B/G 接近 1”也不自动说明白平衡正确。前者要看结构伪影，后者要在已知中性区域和失败场景中验证。

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
Tone Mapping：压缩高光和整体动态范围
Gamma/OETF：把线性光信号编码到显示域
```

## 关键词与参数验收表

| 关键词/参数 | 定义 | 参数方向/失败现象 | 验证方式 |
|---|---|---|---|
| Demosaic | 从单通道 CFA 估计每像素 RGB | 插值跨越强边缘会产生 zipper、false color 或 moiré | 检查采样值保持、斜边和细纹理 crop |
| bilinear baseline | 对同色已知采样做线性插值 | 简单稳定但不感知边缘方向 | 与 OpenCV baseline 用相同 crop 比较 |
| Gray World | 假设全图平均反射近似中性 | 单色主导场景会把真实颜色拉向灰色 | 看中性 ROI，而不只看全图 R/G、B/G |
| `low/high_percentile=5/95` | AWB 统计时排除极暗/极亮像素的百分位 | 过滤过强会丢样本，过弱会受 clipping/黑位影响 | sweep 后比较 gain、DeltaE proxy 和 clipping |
| `max_gain=8` | AWB 通道增益上限 | 太高放大噪声和高光 clip；太低可能校不回色温 | 检查暗部噪声、每通道高光和 gain 饱和 |
| neutral ROI | 人工或规则选取的近中性区域 | ROI 不真正中性时会产生系统偏色 | 保存 ROI 坐标、预览和选择理由 |

## 从输入到结论：可复现教程

### 数据契约、公式符号和算法流程

| 边界 | Demosaic 输入/输出 | AWB 输入/输出 |
|---|---|---|
| shape | `(H,W)` Bayer → `(H,W,3)` RGB | `(H,W,3)` → `(H,W,3)` |
| dtype/range | `uint16/float32` RAW code → `float32` RAW-code RGB | `float32` 线性 RGB，gain 后按有效上限处理 |
| 颜色域 | Sensor CFA / camera primaries | Linear Camera RGB；还不是标准 sRGB |
| 必要 metadata | Bayer pattern、有效 white level | 有效像素筛选范围、gain 上限；中性 ROI 如有 |

对颜色 `C∈{R,G,B}`，`M_C(p)` 表示位置 `p` 是否真实采到该颜色，`K` 是归一化邻域核：

```text
C_hat(p) = ((X * M_C) convolve K)(p) / ((M_C convolve K)(p) + eps)
```

分母只计算有效同色样本的权重；`eps` 仅防止边界处分母为零。真实采样点应恢复为 `X(p)`，不能被插值值覆盖。Bilinear 假设局部颜色变化平滑，因此在跨边缘与周期纹理处最容易失败。

Gray World 在过滤后的像素集合 `S` 上计算 `mu_C=(1/|S|)sum_{p∈S}C(p)`，再用 `g_R=mu_G/mu_R`、`g_G=1`、`g_B=mu_G/mu_B`。假设是 `S` 中平均反射率近中性且光源近似全局一致；这两个条件不成立时，即使均值被拉平也可能更偏色。

```text
BLC/DPC/LSC Bayer
  -> 建立 R/G/B sample masks
  -> 对缺失颜色卷积插值并保留真实采样
  -> 过滤过暗/近饱和像素
  -> 估计并限制 AWB gains
  -> 在线性 RGB 应用 gains，统计 clipping
  -> 仅为显示生成 preview
```

### 参数、耦合与失败方向

| 参数/选择 | 默认/单位 | 增大或切换后的影响 | 耦合 | 失败现象/选择理由 |
|---|---:|---|---|---|
| interpolation kernel | 3×3 bilinear | 更大核更平滑，也更可能跨边缘 | CFA、border policy | baseline 易手算；斜边 blur/zipper 时需 edge-aware 对照 |
| `low_percentile` | 5% | 排除更多暗部，减少黑位/噪声影响，也减少样本 | BLC、场景曝光 | 太高会让统计只剩中高亮区域 |
| `high_percentile` | 95% | 数值越高会纳入更多高光 | white level、clipping | 太高受彩色高光/饱和污染，太低丢失有效中性样本 |
| `max_gain` | 8× | 上限增大可校更极端色温，但放大噪声/clip | low/high 筛选、Sensor 响应 | gain 经常触顶表示估计或数据合同可能错误 |
| AWB domain | RGB-domain baseline | RAW 域应用可少一次通道图，但要精确映射 R/Gr/Gb/B | Demosaic、clip 顺序 | 两条路径比较时必须冻结 estimation 和归一化 |

### 代码导航、结果判读和 failure case

```text
scripts/08_apply_demosaic.py -> soft_isp/demosaic.py -> demosaic JSON/preview/compare
scripts/09_apply_awb.py      -> soft_isp/awb.py       -> gains/ratio JSON/compare
scripts/16_close_mastery_gaps.py -> OpenCV/White Patch/Gray ROI 对照
tests/test_dpc_demosaic.py + tests/test_iq_awb.py
```

| 现象 | 首查 | 用什么隔离 | 修复的 trade-off |
|---|---|---|---|
| 整图紫/绿且规则交错 | CFA pattern/offset | 关闭 AWB，检查真实采样点和 4×4 小图 | 先修数据合同；调 gain 只会掩盖问题 |
| 斜边拉链/文字彩边 | Demosaic crop | 固定 AWB/CCM，比较 bilinear 与 edge-aware | 边缘感知降低伪影，但复杂度和误判风险上升 |
| AWB 后中性物仍偏色 | ROI 是否真中性、gain 映射 | 保存筛选 mask 和 ROI 通道比 | 更严格灰点筛选提高纯度但降低覆盖率 |
| 夜景高光失去颜色 | gain 后 per-channel clipping | 暂停 Tone/CCM，查线性 RGB 高端比例 | 限 gain 保高光，但可能残留色偏 |
| 全图均值变中性但主体更差 | Gray World 假设 | 对大面积单色/混合光样张做失败对照 | 分区/语义 AWB 更稳，但系统复杂度提高 |

### 证据边界、跨周连接和学习验收

| 内容 | 证据等级 | 能证明 | 不能证明 |
|---|---|---|---|
| 公开 DNG 的 bilinear/Gray World 输出 | `verified_public` | 单帧学习链路与失败现象可复现 | 产品级 demosaic/AWB 或手机时序稳定性 |
| OpenCV edge-aware、White Patch、Gray ROI | `verified_public` baseline | 同一公开数据下不同假设的趋势 | AHD/Malvar 已实现；标准光源颜色准确度 |
| rawpy 对比 | `verified_proxy` | 更接近/远离所选成熟渲染参考 | 真实颜色 ground truth |
| ColorChecker、中性灰、多光源序列 | `not_run` | 当前无标准证据 | 不能宣称 AWB/颜色准确度达标 |

Week3 把 Week2 的线性 Bayer 转成线性 Camera RGB，并将结果交给 Week4 的 CCM/Tone/OETF。这里必须把“插值结构错误”和“白点/颜色错误”分开，否则 Week4 矩阵会错误地补偿上游问题。

- [ ] 能在 8×8 数组上证明真实采样值保持
- [ ] 能指出 bilinear 的平滑假设及一个失败 crop
- [ ] 能手算 Gray World gains，并解释过滤集合 `S`
- [ ] 能预测 `high_percentile`/`max_gain` 改变后的 clip 与噪声方向
- [ ] 能用 no-AWB/identity-gain 隔离 CFA、Demosaic 和 AWB 问题

## 本周面试闭环

完整参考答案见[Week 3：Demosaic/AWB 面试题](../interview/week3_demosaic_awb_questions.md)。

1. **概念题：** Demosaic 与 AWB 分别解决什么问题，为什么不能互相替代？
2. **原理题：** bilinear、edge-aware 和 AHD 的核心差异是什么，本项目实际验证了哪一种？
3. **参数题：** `low/high_percentile` 与 `max_gain` 怎样共同影响样本纯度、噪声和 clipping？
4. **调试题：** 如何区分 CFA pattern 错误、Demosaic 假彩和 AWB 偏色？
5. **系统题：** Gray World 在混合光视频中为什么不稳定，量产方案还需哪些空间/时序信息？
