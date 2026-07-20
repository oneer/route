# 第4章：ISP前端处理：原始数据校正


> 课程阶段：传统 ISP 与成像基础　|　难度：入门　|　优先级：核心
>
> 建议用时：2–3 小时阅读 + 1–2 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**在正确数据域完成 BLC、FPN、暗电流、线性化与 PRNU 校正。**

## 1. 本章先解决“RAW 的地基为什么要先校正”

第 2 章讲传感器为什么会产生黑电平、噪声、暗电流、FPN、PRNU 等非理想项。第 4 章讲 ISP 看到这些非理想 RAW 之后，第一批应该做什么。

可以把原始数据校正理解为：

```text
在做颜色、细节、风格之前，先把 RAW 的零点、线性、固定偏差和响应不均校准好
```

这一步像给后续 pipeline 打地基。地基歪了，后面每个模块都会在错误数据上工作：

- black level 错了，暗部基线错，AWB 和 CCM 会放大偏色。
- FPN 没处理，列纹/行纹会被 demosaic、sharpen、tone mapping 放大。
- dark current 没补偿，长曝光或高温暗部会出现热噪声和亮点。
- PRNU 没校正，均匀区域会有固定亮暗纹理。
- ADC/响应非线性没处理，后面的颜色矩阵、HDR 和曝光融合都不再满足线性假设。

所以本章不是“把图像调好看”，而是把传感器输出变成更稳定、更线性、更可建模的 RAW。

## 2. 先建立 RAW 观测模型

一个适合初学者的 RAW 模型可以写成：

```text
raw(x, y) =
  black_offset
  + analogue_gain * [
      true_light_signal(x, y)
      + dark_current(x, y, temperature) * exposure_time
    ]
  + fixed_pattern_offset(x, y)
  + response_gain_error(x, y) * true_light_signal(x, y)
  + read_noise
  + quantization_error
```

这个式子不要求你一开始严格推导，但它能帮你分清每个校正项的作用。

| 项 | 直觉解释 | 是否随光照变化 | 是否随位置固定 | 对应校正 |
|---|---|---|---|---|
| black_offset | 没有光也有的数字基线 | 否 | 可全局/通道/列相关 | BLC |
| dark_current | 热产生的“假光子” | 与曝光/温度相关 | 部分固定，部分随机 | 暗电流补偿 |
| fixed_pattern_offset | 每个像素/列/行固定偏移 | 否 | 是 | DSNU/FPN correction |
| response_gain_error | 每个像素响应斜率不同 | 是 | 是 | PRNU/flat-field correction |
| read_noise | 读出电路随机噪声 | 不一定 | 否 | 降噪/硬件设计 |
| quantization_error | ADC 离散化误差 | 与码值相关 | 否 | ADC/位宽/抖动策略 |

原始数据校正最重要的是区分：

```text
offset 类问题：减法解决为主
gain 类问题：乘法/除法解决为主
random noise：不能靠一张校正表完全去掉
```

## 3. Black Level Correction：黑电平不是亮度调节

### 3.1 黑电平是什么

传感器没有有效光照时，RAW 输出通常不是 0，而是一个基线值。这个值可能来自 ADC 偏置、读出链路、sensor 设计保留空间或厂商编码策略。

```text
corrected_raw = raw - black_level
```

但真实系统很少只有一个全局常数。black level 可能按：

- 颜色通道不同：R/G/B 不同黑电平。
- 列或行不同：column/row offset。
- sensor mode 不同：不同分辨率、HDR、binning 下变化。
- gain/temperature/exposure 不同：部分偏移随工况漂移。

### 3.2 黑电平做错会怎样

| 错误 | 图像现象 | 后续影响 |
|---|---|---|
| 减少了 | 暗部发灰，黑不下去 | AWB/CCM 基于错误基线，暗部偏色 |
| 减多了 | 暗部被压死，细节截断 | 阴影细节丢失，噪声统计错误 |
| 只用全局常数但实际有列偏移 | 竖条纹残留 | sharpen/tone 后条纹更明显 |
| HDR 不同曝光共用同一 black level | 合成边界异常 | HDR merge 亮度不连续 |

### 3.3 用 masked pixels 估计黑电平

很多传感器边缘有 optical black / masked pixels，它们被遮光，不接收有效光。ISP 可以用这些像素估计每帧或每行/列的黑电平。

直觉：

```text
遮光像素测到的不是场景光，而是传感器基线和暗信号
```

使用 masked pixels 时要注意：

- 要剔除坏点和异常值。
- 估计值可能有噪声，需要平滑。
- 不同通道/列可能要分别估计。
- 长曝光和高温时，masked 区域也会受暗电流影响。

## 4. Dark Frame、Bias Frame、Flat Field：三类校准图不要混

原始数据校正常用三类校准图。初学者很容易混在一起。

| 校准图 | 怎么拍 | 主要观察什么 | 对应问题 |
|---|---|---|---|
| Bias frame | 极短曝光、无光 | 读出基线/电子偏置 | black/bias offset |
| Dark frame | 同曝光时间、无光 | 暗电流、热像素、暗 FPN | dark current、DSNU |
| Flat field | 均匀光照 | 响应不均、镜头暗角、PRNU | PRNU、LSC、flat correction |

### 4.1 Dark frame subtraction 的边界

dark frame 可以估计固定暗信号模式，例如某些热像素和暗场 FPN。但它不能消除所有暗部噪声，因为暗电流本身也有 shot noise。

```text
可校正：平均暗信号、固定亮点、固定列纹
不可完全校正：随机读噪、暗电流 shot noise、帧间随机波动
```

这就是为什么暗场扣除后，图像不会变成完全干净。

### 4.2 Flat field correction 的基本式

一个常见平场校正形式是：

```text
corrected = (raw - dark) / (flat - dark) * mean(flat - dark)
```

直觉：

- `raw - dark`：先去掉黑/暗偏移。
- `flat - dark`：得到每个位置对均匀光的相对响应。
- 除以响应图：把响应低的位置拉高，把响应高的位置压低。
- 乘平均值：保持整体亮度尺度。

如果没先做 dark/bias 校正就直接用 flat，很容易把 offset 当成 gain，导致补偿错误。

## 5. DSNU、PRNU、FPN：三个名字怎么分

### 5.1 FPN 是大类

FPN，Fixed Pattern Noise，表示空间位置固定的噪声/不均匀性。它可以表现为点状、列状、行状或低频纹理。

### 5.2 DSNU 是暗场 offset 不均

DSNU，Dark Signal Non-Uniformity，表示无光条件下不同像素/列/行暗信号不同。

```text
观察方法：拍 dark frame
校正方式：减 offset map / column offset / row offset
```

### 5.3 PRNU 是受光响应 gain 不均

PRNU，Photo Response Non-Uniformity，表示同样光照下，不同像素响应斜率不同。

```text
观察方法：拍 flat field
校正方式：乘 gain map 或除 response map
```

### 5.4 用一条线理解 DSNU 和 PRNU

假设一个像素响应近似线性：

```text
raw_i = offset_i + gain_i * light
```

那么：

- `offset_i` 不同，就是 DSNU / offset FPN。
- `gain_i` 不同，就是 PRNU / gain FPN。

这就是很多 FPN/NUC 校正论文中使用 offset correction + gain correction 的原因。

## 6. 暗电流补偿：温度和曝光时间是关键

暗电流不是固定常数。它通常随温度升高快速增加，也随曝光时间积累。

直觉模型：

```text
dark_signal ≈ dark_current_rate(temperature) * exposure_time
```

这意味着：

- 短曝光白天图像中，暗电流可能不明显。
- 长曝光夜景、天文、安防、车载高温场景中，暗电流会很重要。
- 如果 dark frame 的温度和曝光时间与实际拍摄不匹配，扣除效果会变差。

### 热像素 Hot Pixel

某些像素暗电流特别高，即使没有光也会很亮。它们在长曝光和高温时更明显。处理方法通常包括：

- factory defect pixel map
- dark frame 检测
- dynamic bad pixel detection
- 时间/温度相关坏点表

## 7. 线性化：为什么 RAW 要尽量保持线性

很多 ISP 前端假设 RAW 与入射光强近似线性。比如：

- 曝光融合需要比较不同曝光的线性亮度。
- CCM 通常建立在线性 RGB 上。
- 噪声模型常用信号强度估计 shot noise。
- flat field / PRNU 校正假设响应可用 gain 调整。

如果传感器或 ADC 输出有非线性，就需要 linearization LUT：

```text
linear_raw = LUT[raw_code]
```

常见非线性来源：

- ADC 非线性
- 压缩 RAW 编码
- dual conversion gain 切换
- HDR mode 中不同曝光/增益段拼接
- sensor 内部 tone-like processing

线性化不是让图像“看起来线性”，而是让数字值和光照强度之间尽量满足后续算法假设。

## 8. 推荐的前端校正顺序

一个合理的 RAW 前端校正顺序可以是：

```text
RAW input
  -> unpack / bit alignment
  -> black level / bias correction
  -> dark current / DSNU correction
  -> bad pixel correction
  -> linearization LUT
  -> PRNU / flat-field / lens shading gain correction
  -> RAW domain denoise
  -> demosaic
```

不同系统会调整顺序，但原则是：

```text
先处理 offset，再处理 gain；
先建立线性和零点，再做依赖线性的操作；
先在 Bayer 域修局部错误，再进入 RGB 域。
```

为什么 offset 要先于 gain？

假设：

```text
raw = offset + gain * signal
```

如果先乘 gain map，再减 offset，offset 也会被错误放大。正确思路通常是先减 offset，再做 gain correction。

## 9. 硬件实现时要考虑什么

原始数据校正通常在 ISP 最前端，像素吞吐压力最大。因此硬件实现要简单、稳定、可流式。

### 9.1 BLC 硬件

```text
corrected = max(raw - black_level[channel/column], 0)
```

关注：

- signed/unsigned 位宽
- underflow clipping
- 每通道 black level
- 每列/每行 offset table
- 参数更新与帧同步

### 9.2 FPN/DSNU 校正

可能需要：

- per-pixel offset map：精度高，存储大。
- per-column offset：适合列纹，存储较小。
- per-row offset：适合行纹。
- block/grid offset：折中存储和效果。

### 9.3 PRNU/flat 校正

gain map 可能是 per-pixel，也可能是网格插值。硬件常用：

- 定点 gain
- 双线性插值
- 分通道 gain table
- 限制最大 gain，避免边缘噪声过度放大

### 9.4 LUT 线性化

LUT 要考虑：

- 输入 bit depth，例如 10/12/14 bit。
- 输出 bit depth 是否增加，避免精度损失。
- 是否按通道或 mode 使用不同 LUT。
- 是否需要分段线性近似来减少存储。

## 10. 参数为什么要随场景和 sensor mode 变化

一套 RAW 校正参数很少能适配所有情况。

| 变化因素 | 影响 |
|---|---|
| 温度升高 | dark current、hot pixel、DSNU 增强 |
| 曝光时间变长 | 暗电流积累更多 |
| analog gain 变大 | 噪声和饱和行为变化 |
| sensor mode 改变 | black level、LSC、noise profile 可能变化 |
| HDR mode | 不同曝光/增益段需要不同黑电平和饱和点 |
| crop/binning | PRNU/LSC 表和 CFA 解释可能变化 |

所以前端校正需要 metadata：曝光、增益、温度、mode、frame id。没有这些信息，校正很容易“看起来能跑，但场景一变就坏”。

## 11. 典型错误现象速查表

| 图像现象 | 可能原因 | 优先检查 |
|---|---|---|
| 暗部整体发灰 | black level 减少了 | BLC 值、masked pixels |
| 暗部死黑、细节断层 | black level 减多了 | clipping、直方图左侧 |
| 竖条纹 | column FPN | 列均值、暗场图 |
| 横条纹 | row FPN / rolling readout | 行均值、时序 |
| 长曝光亮点 | hot pixel / dark current | dark frame、温度 |
| 均匀平场有纹理 | PRNU / LSC 不足 | flat field、gain map |
| HDR 合成边缘亮度跳 | 不同曝光 black level/linearization 不一致 | HDR metadata、LUT |
| AWB 怎么调都偏色 | 前端黑电平或 CFA 错 | BLC、CFA、通道统计 |

## 12. 最小可验证实验

### 实验 1：黑电平三档实验

对同一张 RAW 使用三种 black level：

```text
black_level - 64
black_level
black_level + 64
```

输出：

- RAW 直方图
- 暗部 crop
- demosaic 后 RGB

观察：

- 欠校正是否抬黑？
- 过校正是否截断暗部？
- AWB 后是否出现暗部偏色？

### 实验 2：暗场 FPN 观察

拍或使用一张 dark frame：

- 计算整图均值和标准差。
- 计算每列均值，画 column profile。
- 计算每行均值，画 row profile。
- 找出异常亮点。

目标：区分随机噪声、列 FPN、行 FPN、hot pixel。

### 实验 3：Flat field / PRNU 观察

拍一张均匀光照图：

- 先减 dark/black。
- 计算每个位置相对均值。
- 可视化 response map。

目标：观察 PRNU、镜头暗角和通道 shading。

### 实验 4：错误顺序实验

比较两种流程：

```text
流程 A：corrected = (raw - black) * gain
流程 B：corrected = raw * gain - black
```

在有较大 gain 的边缘区域观察暗部差异。目标：理解为什么 offset correction 通常要先于 gain correction。

## 13. 自测题

1. BLC 和曝光补偿有什么区别？
2. black level 为什么可能按通道、列或 mode 变化？
3. DSNU 和 PRNU 分别应该用什么校准图观察？
4. dark frame subtraction 能否消除所有暗部噪声？为什么？
5. 为什么 flat field correction 前要先减 dark/bias？
6. 为什么 PRNU 是 gain 类问题，不是 offset 类问题？
7. 为什么线性化要尽量放在颜色矩阵和 HDR merge 之前？
8. per-pixel offset map 和 per-column offset map 的存储代价有什么区别？
9. 为什么边缘 LSC/PRNU 增益过大会放大噪声？
10. 如果 AWB 总是暗部偏色，为什么应该先检查 BLC？

## 14. 常见误区

- **误区 1：黑电平就是把图像调暗。**  
  错。BLC 是建立零点，不是风格调节。

- **误区 2：暗场扣除后就没有噪声。**  
  错。dark frame 可以扣固定模式，但随机读噪和暗电流 shot noise 仍然存在。

- **误区 3：FPN、DSNU、PRNU 是一回事。**  
  FPN 是大类；DSNU 是暗场 offset 不均；PRNU 是受光响应 gain 不均。

- **误区 4：先做 gain 再减 black 也差不多。**  
  很多情况下不差一点，而是会把 offset 错误放大。

- **误区 5：一套校正参数适合所有 mode。**  
  温度、曝光、gain、HDR、binning、crop 都可能让参数变化。

## 15. 读完本章应该达到的标准

读完本章后，应该能做到：

- 画出 RAW 前端校正顺序，并解释每一步为什么在这个位置。
- 区分 BLC、dark current compensation、FPN/DSNU、PRNU、linearization。
- 用 dark frame 和 flat field 解释 offset correction 与 gain correction。
- 说出 black level 错误、FPN 残留、PRNU 未校正的图像现象。
- 设计一个最小实验验证 BLC 参数是否合理。
- 解释为什么前端 RAW 校正错误会影响 AWB、CCM、demosaic、HDR 和 denoise。

## 16. 推荐资料与论文

- EMVA 1288：适合学习 DSNU、PRNU、dark current、SNR、saturation、linearity 等传感器表征指标。  
  <https://www.emva.org/standards-technology/emva-1288/>
- EMVA 1288 Release 4.0/4.1 文档：适合深入理解标准化测量定义和 photon transfer 思路。  
  <https://www.emva.org/wp-content/uploads/EMVA1288General_4.0Release.pdf>
- “High-level numerical simulations of noise in CCD and CMOS photosensors: review and tutorial”：适合学习 RAW 噪声模型，包括 PRNU、photon shot noise、dark current FPN、offset FPN、source follower noise、reset noise 和 quantization noise。  
  <https://arxiv.org/abs/1412.4031>
- “Uniformity Correction of CMOS Image Sensor Modules for Machine Vision Cameras”：适合学习 DSNU、PRNU、温度和模拟增益依赖，以及机器视觉相机的 uniformity correction。  
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC9783237/>
- “Fixed Pattern Noise Reduction and Linearity Improvement in Time-Mode CMOS Image Sensors”：适合学习 offset correction、gain correction 和线性化在 FPN 降低中的作用。  
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC7588900/>
- Allied Vision FPNC Application Note：适合从工业相机角度理解 FPN、DSNU、PRNU 和校正示例。  
  <https://www.alliedvision.com/assets/documents/products/cameras/Alvium_common/Alvium-Cameras_FPNC_AppNote.pdf>
## 学习优先级

- **必须掌握**：本章学习结果、输入输出、关键失败现象和最小验证方法。
- **了解即可**：历史背景、少见硬件变种和暂时无法从公开资料验证的细节。
- **后面再回看**：需要真实 RAW、标定数据或硬件经验才能完整理解的内容。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab02-raw前端校正.md](../labs/lab02-raw前端校正.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter04-第4章：ISP前端处理：原始数据校正.md)
- 项目落点：
  - [BLC 实现](../../stage1_soft_isp/soft_isp/blc.py)
- [BLC 实验脚本](../../stage1_soft_isp/scripts/06_apply_blc.py)
- 原始资料：[原教程正文归档](../source_archive/chapter04-第4章：ISP前端处理：原始数据校正.md)

导航：[上一章](./chapter03-第3章：图像传感器与ISP协同设计.md) · [下一章](./chapter05-第5章：ISP前端处理：光学缺陷校正.md) · [完整课程索引](../full_content_index.md)
