# Week 2 面试题：BLC、DPC、LSC 与 RAW 前端校正

本周面试目标是讲清三个前端模块分别修正什么物理问题、为什么必须在 Bayer RAW 域尽早处理，以及如何证明没有把真实信号当缺陷修掉。

## 1. BLC 为什么通常放在 Pipeline 前面？

### 核心回答

BLC 修正的是传感器和读出链路的黑位偏置，为 RAW 信号建立正确零点。DPC 阈值、LSC gain、AWB 统计和后续归一化都默认输入已经接近真实光信号，因此 BLC 应尽量靠前。

### 错误传播

- 欠扣 black level：暗部发灰，DPC residual 和 AWB 均值都带偏。
- 过扣 black level：暗部大量 clip 到 0，细节不可恢复，通道间还可能产生暗部偏色。
- 只用一个 scalar：若四个 Bayer 位置黑位不同，暗部会留下通道相关偏置。

### 项目验证

在 `int32` 中做减法，按 `raw_pattern` 生成 per-position black map；验证 BLC 前后 histogram、p01/p50、0 附近比例和每个 Bayer 位置。black 为 0 时减法部分应是 identity，但仍需区分 white-level clamp 带来的变化。

## 2. 为什么不能直接在 `uint16` RAW 上减 black level？

### 核心回答

无符号整数不能表示负值。如果像素小于 black level，直接做 `uint16` 减法可能环绕到很大的正数，而不是得到负数再被 clip 到 0。

正确顺序是：

```text
uint RAW -> int32/float32 -> 减 black map -> clip -> 需要时再转回目标类型
```

### 错误表现

暗像素会突然变成接近 dtype 最大值的亮点或大片高亮，之后 DPC、Demosaic 和 Tone Mapping 会进一步放大错误。

### 最小测试

构造 `raw=10, black=20`。正确结果应为 0；若得到接近 65526，就说明发生了无符号下溢。测试还要覆盖四个 Bayer 位置使用不同 black level。

## 3. DPC 为什么要比较同色 Bayer 邻域？

### 核心回答

Bayer RAW 的相邻像素可能来自不同颜色滤色片，本来就有不同响应。若直接把中心 R 与上下左右 G 比较，颜色边缘和正常通道差异会被误判为坏点。

同色邻域是指在原始坐标中按 CFA 周期找到相同滤色片位置，或者先拆成 R、Gr、Gb、B 四个平面再检测。这样 residual 更接近“同类传感器采样之间的异常”。

### 为什么要在 Demosaic 前处理

一个 RAW hot pixel 在 Demosaic 后会参与多个缺失通道插值，扩散成彩色斑点。RGB 域再修复时，异常已经跨像素、跨通道传播，定位和恢复都更困难。

### 验证

在平坦 Bayer 小数组中注入已知 hot/dead pixel，检查 mask 是否命中；再在强边缘和高频纹理 crop 中检查 false positive。

## 4. `min_delta + MAD` 阈值解决什么问题？

### 核心回答

固定阈值简单，但无法适应不同 ISO、曝光和纹理；纯统计阈值在非常平坦或异常点较多时又可能过敏。学习版实现把固定最低差值和 robust 统计结合：

```text
residual = abs(pixel - local_median)
threshold = max(min_delta, median(residual) + mad_k * MAD(residual))
```

`min_delta` 防止在低噪声平坦区把微小差异当坏点；`mad_k` 根据 residual 离散程度调整阈值，对少量极端值比标准差更稳健。

### 参数方向

- `min_delta` 或 `mad_k` 增大：检测更保守，false positive 通常下降，但 recall 可能下降。
- 参数减小：更容易抓到弱异常，也更容易误伤纹理、边缘和噪声。

### 项目验证

不能只报检测点数量。要对注入坏点做参数网格，记录 precision、recall、额外检测数，并查看强边缘 crop。

## 5. 怎样设计 DPC 注入实验？为什么要同时看 precision 和 recall？

### 实验设计

1. 选择平坦合成 Bayer 或真实 RAW 的受控区域。
2. 在已知同色坐标注入 hot、dead 或 stuck pixel。
3. 运行检测与修复，得到 mask。
4. 将 mask 与注入坐标集合比较。
5. 扫描阈值，并检查修复前后局部 crop。

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
```

recall 高只说明注入点大多被找到；若 precision 很低，算法可能把大量真实纹理也删掉。precision 高但 recall 低，则算法过于保守。ISP 中误伤真实细节往往比保留少量弱坏点更难接受，因此必须结合使用场景讨论取舍。

### 证据边界

合成注入证明检测逻辑在已知缺陷上有效，不证明它能覆盖真实传感器所有缺陷分布。产品级还需要 dark frame、温度/曝光条件和工厂 defect map。

## 6. LSC 修正的物理问题是什么？为什么通常按通道标定？

### 核心回答

LSC 修正镜头渐晕、微透镜和像素角度响应造成的中心—边缘亮度下降及颜色不均匀。不同波长、滤色片和入射角的响应不同，因此实际 gain map 通常按 R、Gr、Gb、B 独立标定，而不是全图只乘一张灰度径向图。

典型模型是：

```text
corrected(y,x,c) = raw(y,x,c) * gain(y,x,c)
```

中心 gain 通常接近 1，边缘 gain 较大，但实际 mesh 不一定是完美圆对称。

### 错误后果

- gain 太小：角落仍暗或偏色。
- gain 太大：角落过亮，并同步放大 shot/read noise。
- 用自然场景直接估计：可能把真实天空渐变或灯光分布误当镜头阴影。

### 验证

identity gain 必须保持输入；合成 flat-field 可验证 mesh 估计流程；真实产品结论则需要均匀光源、多帧平均、四通道残差和不同色温/焦距/光圈条件。

## 7. 为什么 synthetic flat-field 不能证明产品级 LSC？

### 核心回答

合成 flat-field 的生成模型和估计算法往往共享相似假设。算法恢复成功，只能证明坐标、插值、mesh 和除法流程自洽，不能证明真实镜头、传感器和光源条件下仍然正确。

真实标定还要处理：

- 光源本身的不均匀性；
- 读出噪声和坏点；
- 不同通道、色温、焦距和光圈；
- 多帧平均、归一化基准和边缘残差；
- gain 上限、插值精度和量化。

### 面试表达

我会把 synthetic flat-field 称为流程验证或单元实验，不称为真实 LSC 标定结果。这样既说明我做过闭环，也不会夸大证据。

## 8. 如果前端处理后出现暗部偏色、彩点和角落噪声，你怎样排查？

### 排查顺序

1. 检查 Bayer pattern、visible area 和 orientation，排除坐标解释错误。
2. 暂停 DPC/LSC，只运行 BLC，检查四通道黑位和低端 clipping。
3. 开启 DPC，查看 mask 是否集中在强边缘或高光，检查注入实验指标。
4. 开启 LSC，分别查看四通道 gain map、中心/边缘比例和 clip 数量。
5. 再进入 Demosaic，检查单点是否扩散、角落噪声是否被 gain 放大。

### 判断逻辑

暗部整体偏色更像 per-channel BLC 或 WB 问题；孤立彩点通常先查 DPC；从中心向角落逐渐变亮且噪声同步增强，通常先查 LSC gain。不能只凭最终图猜模块，必须逐阶段保存中间结果。

## Week 2 一分钟复述

Week 2 的 BLC、DPC、LSC 都在保护 Demosaic 的输入：BLC 建立正确零点，DPC 在异常扩散前修复稀疏坏点，LSC 补偿位置相关响应。我的验证不只看最终图片，而是用 per-position 测试、坏点注入、参数扫描、gain map 和局部 crop 检查收益与误伤，并明确学习模型和真实标定的边界。
