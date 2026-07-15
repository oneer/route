# Week 3 面试题：Demosaic、AWB 与线性 RGB

本周面试目标是区分空间重建与颜色校正：Demosaic 负责补齐缺失颜色，AWB 负责估计和应用通道增益，两者都不能用“最后好不好看”作为唯一验证标准。

## 1. Demosaic 的输入、输出和本质任务是什么？

### 核心回答

输入是二维 Bayer RAW `(H, W)`，每个位置只采到一种颜色；输出是三维线性 RGB `(H, W, 3)`，每个位置都有 R/G/B。Demosaic 的本质是根据空间邻域估计缺失通道，不是白平衡、颜色空间转换或显示编码。

可以写成：

```text
RAW = M_R * R + M_G * G + M_B * B
目标：从稀疏采样估计 R_hat、G_hat、B_hat
```

### 为什么它是关键数据域转换点

Demosaic 前可以按 Bayer 位置处理传感器问题；之后像素已经混合邻域信息，进入线性 RGB 域。前端坏点、黑位和 LSC 错误会在这里扩散，后续 AWB/CCM 也无法把空间插值错误真正恢复。

### 验证

检查 shape、dtype、范围；用常量 Bayer 验证常量输出；确认真实采样位置被保留；最后看斜边、文字和高频纹理 crop，而不是先评价整体颜色。

## 2. Bilinear Demosaic 的基本原理是什么？

### 核心回答

对每个颜色通道建立采样 mask，在已采样位置保留原值，在缺失位置用附近同色样本加权平均：

```text
C_hat = conv(RAW * M_C, K) / max(conv(M_C, K), eps)
```

分母是有效权重之和，避免图像边界或 mask 稀疏导致亮度变化。R、G、B 分别插值后再 stack 成 RGB。

### 为什么真实采样值应保留

传感器已经测到的值是观测，不应被邻域平均无条件覆盖。若连真实采样位置也改写，算法会额外模糊图像，并使单元测试难以区分“补值”和“改值”。

### 局限

Bilinear 不判断边缘方向，容易造成 zipper、false color、moire 和细节模糊。它适合作为可解释 baseline，不代表产品级 Demosaic。

## 3. Bayer pattern 错误时为什么会整图串色？怎样定位？

### 核心回答

pattern 决定每个坐标是真实 R、G 还是 B。pattern 一旦错，算法会把真实红样本当蓝或绿，并用错误邻域补齐其他通道，因此影响是周期性、全局性的，而不是某个局部颜色偏一点。

### 典型现象

- R/B 对调或整体出现强烈紫、绿色偏。
- 细节结构仍然存在，但边缘带周期性色彩。
- AWB gain 可能变得极端，因为它试图补偿错误通道解释。

### 排查

1. 回到 `raw_pattern + color_desc`，不要从最终图猜 pattern。
2. 打印 4×4 位置标签和三色 mask。
3. 检查真实采样值保留测试。
4. 暂停 AWB/CCM，只看线性 Demosaic 的结构与通道位置。

## 4. Demosaic 应重点观察哪些伪影？为什么全图 PSNR 不够？

### 重点伪影

| 伪影 | 常见区域 | 原因 |
|---|---|---|
| zipper | 斜边、文字边缘 | 插值没有沿边缘方向处理 |
| false color | 黑白高对比边缘、细枝 | 缺失通道估计不一致 |
| moire | 规则网格、织物、屋顶 | 场景频率接近 CFA 采样极限 |
| blur | 细纹理、毛发 | 邻域平均抹平高频信息 |

这些问题通常只占少量像素，全图平均指标会被大面积平坦区域稀释。正确做法是固定语义 crop，保证不同算法使用同一坐标和方向，再结合 edge/texture 指标与主观观察。

### 证据边界

OpenCV edge-aware 是一个独立 baseline，不应直接称为 AHD；若没有实现或接入 Malvar/AHD，就只能讨论其理论差异，不能声称做过实测。

## 5. AWB estimation 和 WB gain application 有什么区别？

### 核心回答

AWB estimation 回答“应该使用什么增益”；WB gain application 回答“怎样把已知增益正确乘到数据上”。前者是统计和场景理解问题，后者是数据域、通道映射、clamp 和硬件执行问题。

本项目用 Gray World 在线性 RGB 上估计并应用 R/G/B gain；OpenISP 对照更接近在 Bayer RAW 域应用外部给定的 R/Gr/Gb/B gain。

### 为什么要区分

如果最终偏色，可能是估计错，也可能是 gain 映射、应用位置或 clipping 错。把两者都叫 AWB 会让排查失去层次。

### 最小验证

- identity gain 必须保持输入。
- 单通道小数组验证 R/G/B 或 R/Gr/Gb/B 映射。
- 检查 gain 有限、为正且不超过合理上限。
- 统计应用 gain 后的 per-channel clipping。

## 6. Gray World 的假设、公式和失败场景是什么？

### 核心回答

Gray World 假设自然场景包含足够丰富的颜色，整体平均反射接近中性。以 G 为锚点：

```text
R_gain = G_mean / R_mean
G_gain = 1
B_gain = G_mean / B_mean
```

通常先排除过暗和饱和像素，避免噪声和截断值污染统计。

### 失败场景

- 大面积草地、森林或舞台彩灯：场景平均色本来就不应是灰色。
- 大面积蓝天、海洋：Gray World 可能错误压低蓝色。
- 混合光源：单组全局 gain 无法同时校正不同区域。
- 极暗或大量饱和：可靠统计样本不足。

### 验证

不能只看全图 R/G、B/G 是否变成 1，因为算法按定义就会推动均值接近。更强的证据是中性 ROI、肤色保护、gain 稳定性、失败场景对照和 Gray World/White Patch/Gray ROI 多 baseline 比较。

## 7. 为什么 AWB 应在线性数据上做？RAW 域和 RGB 域各有什么特点？

### 核心回答

通道 gain 表示对线性光响应的比例校正。若在 Gamma/OETF 后做乘法，码值已是非线性的，相同倍数不再对应光强倍数，颜色和亮度关系都会被扭曲。

RAW 域 gain 可以在 Demosaic 前按 Bayer 位置执行，更接近硬件流水线，也能分别控制 Gr/Gb；RGB 域实现更直观，便于教学和 Gray World 统计，但插值已经发生。

### 比较时要控制什么

必须使用相同的增益来源、白电平、clamp 规则和后续 Demosaic，否则输出差异不能只归因于“RAW 域还是 RGB 域”。

## 8. Demosaic 后偏绿，你会怎样判断是正常现象还是算法错误？

### 排查框架

1. 检查 CFA pattern 和三色 mask，排除通道位置错。
2. 检查真实采样值保留、常量图和边界行为。
3. 只看结构伪影：是否花屏、zipper、false color，而不是先看最终色彩。
4. 检查 RAW 四通道响应；Bayer 有两个绿色位置，且尚未 AWB/CCM，线性 camera RGB 偏绿可能正常。
5. 应用独立 AWB，再检查中性 ROI；若中性仍偏绿，再看 gain 估计与 CCM。

### 面试表达

我不会用 AWB 去掩盖 pattern 或插值错误。Demosaic、AWB、CCM 的职责必须分开验证，虽然工程实现可以融合流水线。

## Week 3 一分钟复述

Week 3 是从 Bayer RAW 到线性 RGB 的转换点。Bilinear Demosaic 用同色邻域补缺失通道，我用常量图、采样值保留和纹理 crop 验证；Gray World 用全局统计估计 gain，但必须用中性 ROI 和失败场景检验。偏色不自动等于 Demosaic 错，均值变灰也不自动等于 AWB 正确。
