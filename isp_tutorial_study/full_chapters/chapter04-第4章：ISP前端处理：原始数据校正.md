<!-- 来源：https://zsc.github.io/isp_tutorial/chapter4.html -->

# 第4章：ISP前端处理：原始数据校正



### 1. 本章先解决“RAW 的地基为什么要先校正”

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

### 2. 先建立 RAW 观测模型

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

### 3. Black Level Correction：黑电平不是亮度调节

#### 3.1 黑电平是什么

传感器没有有效光照时，RAW 输出通常不是 0，而是一个基线值。这个值可能来自 ADC 偏置、读出链路、sensor 设计保留空间或厂商编码策略。

```text
corrected_raw = raw - black_level
```

但真实系统很少只有一个全局常数。black level 可能按：

- 颜色通道不同：R/G/B 不同黑电平。
- 列或行不同：column/row offset。
- sensor mode 不同：不同分辨率、HDR、binning 下变化。
- gain/temperature/exposure 不同：部分偏移随工况漂移。

#### 3.2 黑电平做错会怎样

| 错误 | 图像现象 | 后续影响 |
|---|---|---|
| 减少了 | 暗部发灰，黑不下去 | AWB/CCM 基于错误基线，暗部偏色 |
| 减多了 | 暗部被压死，细节截断 | 阴影细节丢失，噪声统计错误 |
| 只用全局常数但实际有列偏移 | 竖条纹残留 | sharpen/tone 后条纹更明显 |
| HDR 不同曝光共用同一 black level | 合成边界异常 | HDR merge 亮度不连续 |

#### 3.3 用 masked pixels 估计黑电平

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

### 4. Dark Frame、Bias Frame、Flat Field：三类校准图不要混

原始数据校正常用三类校准图。初学者很容易混在一起。

| 校准图 | 怎么拍 | 主要观察什么 | 对应问题 |
|---|---|---|---|
| Bias frame | 极短曝光、无光 | 读出基线/电子偏置 | black/bias offset |
| Dark frame | 同曝光时间、无光 | 暗电流、热像素、暗 FPN | dark current、DSNU |
| Flat field | 均匀光照 | 响应不均、镜头暗角、PRNU | PRNU、LSC、flat correction |

#### 4.1 Dark frame subtraction 的边界

dark frame 可以估计固定暗信号模式，例如某些热像素和暗场 FPN。但它不能消除所有暗部噪声，因为暗电流本身也有 shot noise。

```text
可校正：平均暗信号、固定亮点、固定列纹
不可完全校正：随机读噪、暗电流 shot noise、帧间随机波动
```

这就是为什么暗场扣除后，图像不会变成完全干净。

#### 4.2 Flat field correction 的基本式

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

### 5. DSNU、PRNU、FPN：三个名字怎么分

#### 5.1 FPN 是大类

FPN，Fixed Pattern Noise，表示空间位置固定的噪声/不均匀性。它可以表现为点状、列状、行状或低频纹理。

#### 5.2 DSNU 是暗场 offset 不均

DSNU，Dark Signal Non-Uniformity，表示无光条件下不同像素/列/行暗信号不同。

```text
观察方法：拍 dark frame
校正方式：减 offset map / column offset / row offset
```

#### 5.3 PRNU 是受光响应 gain 不均

PRNU，Photo Response Non-Uniformity，表示同样光照下，不同像素响应斜率不同。

```text
观察方法：拍 flat field
校正方式：乘 gain map 或除 response map
```

#### 5.4 用一条线理解 DSNU 和 PRNU

假设一个像素响应近似线性：

```text
raw_i = offset_i + gain_i * light
```

那么：

- `offset_i` 不同，就是 DSNU / offset FPN。
- `gain_i` 不同，就是 PRNU / gain FPN。

这就是很多 FPN/NUC 校正论文中使用 offset correction + gain correction 的原因。

### 6. 暗电流补偿：温度和曝光时间是关键

暗电流不是固定常数。它通常随温度升高快速增加，也随曝光时间积累。

直觉模型：

```text
dark_signal ≈ dark_current_rate(temperature) * exposure_time
```

这意味着：

- 短曝光白天图像中，暗电流可能不明显。
- 长曝光夜景、天文、安防、车载高温场景中，暗电流会很重要。
- 如果 dark frame 的温度和曝光时间与实际拍摄不匹配，扣除效果会变差。

#### 热像素 Hot Pixel

某些像素暗电流特别高，即使没有光也会很亮。它们在长曝光和高温时更明显。处理方法通常包括：

- factory defect pixel map
- dark frame 检测
- dynamic bad pixel detection
- 时间/温度相关坏点表

### 7. 线性化：为什么 RAW 要尽量保持线性

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

### 8. 推荐的前端校正顺序

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

### 9. 硬件实现时要考虑什么

原始数据校正通常在 ISP 最前端，像素吞吐压力最大。因此硬件实现要简单、稳定、可流式。

#### 9.1 BLC 硬件

```text
corrected = max(raw - black_level[channel/column], 0)
```

关注：

- signed/unsigned 位宽
- underflow clipping
- 每通道 black level
- 每列/每行 offset table
- 参数更新与帧同步

#### 9.2 FPN/DSNU 校正

可能需要：

- per-pixel offset map：精度高，存储大。
- per-column offset：适合列纹，存储较小。
- per-row offset：适合行纹。
- block/grid offset：折中存储和效果。

#### 9.3 PRNU/flat 校正

gain map 可能是 per-pixel，也可能是网格插值。硬件常用：

- 定点 gain
- 双线性插值
- 分通道 gain table
- 限制最大 gain，避免边缘噪声过度放大

#### 9.4 LUT 线性化

LUT 要考虑：

- 输入 bit depth，例如 10/12/14 bit。
- 输出 bit depth 是否增加，避免精度损失。
- 是否按通道或 mode 使用不同 LUT。
- 是否需要分段线性近似来减少存储。

### 10. 参数为什么要随场景和 sensor mode 变化

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

### 11. 典型错误现象速查表

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

### 12. 最小可验证实验

#### 实验 1：黑电平三档实验

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

#### 实验 2：暗场 FPN 观察

拍或使用一张 dark frame：

- 计算整图均值和标准差。
- 计算每列均值，画 column profile。
- 计算每行均值，画 row profile。
- 找出异常亮点。

目标：区分随机噪声、列 FPN、行 FPN、hot pixel。

#### 实验 3：Flat field / PRNU 观察

拍一张均匀光照图：

- 先减 dark/black。
- 计算每个位置相对均值。
- 可视化 response map。

目标：观察 PRNU、镜头暗角和通道 shading。

#### 实验 4：错误顺序实验

比较两种流程：

```text
流程 A：corrected = (raw - black) * gain
流程 B：corrected = raw * gain - black
```

在有较大 gain 的边缘区域观察暗部差异。目标：理解为什么 offset correction 通常要先于 gain correction。

### 13. 自测题

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

### 14. 常见误区

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

### 15. 读完本章应该达到的标准

读完本章后，应该能做到：

- 画出 RAW 前端校正顺序，并解释每一步为什么在这个位置。
- 区分 BLC、dark current compensation、FPN/DSNU、PRNU、linearization。
- 用 dark frame 和 flat field 解释 offset correction 与 gain correction。
- 说出 black level 错误、FPN 残留、PRNU 未校正的图像现象。
- 设计一个最小实验验证 BLC 参数是否合理。
- 解释为什么前端 RAW 校正错误会影响 AWB、CCM、demosaic、HDR 和 denoise。

### 16. 推荐资料与论文

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



## 章节概述


原始传感器数据（RAW）是整条ISP流水线中最接近物理成像过程的表示形式。它既保留了最多的信息，也携带了最多的器件非理想性：黑电平偏移、列/行固定模式噪声、温度相关暗电流、ADC非线性、像素响应不一致，以及不同增益档位下的响应漂移。如果这些问题在前端没有被妥善校正，后续的Lens Shading、坏点修复、去马赛克、降噪和色彩处理都会建立在错误的信号基准之上，导致误检、色偏、动态范围损失甚至系统级不稳定。


在自动驾驶和具身智能系统中，RAW校正的要求比消费摄影更严格。系统不仅关心“画面好不好看”，更关心同一物体在不同温度、曝光、模拟增益和时间点下，是否仍然产生一致、可预测的数字响应。换言之，前端原始数据校正的目标不是简单“美化图像”，而是把传感器输出尽量还原为一个稳定、线性、可标定、可建模的信号域。


本章将系统介绍RAW前端校正链路的核心内容，包括Black Level Correction、固定模式噪声消除、暗电流补偿、线性化、PRNU校正，以及传感器增益与偏移标定。我们将同时讨论数学模型、标定方法、RTL/硬件实现结构，以及在车载与机器人场景中的工程权衡。


### 学习目标


- 理解RAW数据中的主要非理想项及其物理来源
- 掌握黑电平、暗电流、FPN、PRNU的区别与联系
- 理解线性化LUT和增益/偏移标定在ISP前端中的作用
- 能够设计一条硬件可落地的原始数据校正流水线
- 理解温度、曝光时间、ISO、增益档位对校正参数的耦合关系
- 能够为自动驾驶和具身智能场景制定更稳健的校正策略


## 4.1 原始数据校正链路总览


### 4.1.1 RAW观测模型


从系统设计角度，单个像素在ADC输出前后的信号可以抽象为：


\[D_{raw}(x,y) = Q\left(g_a \cdot \left[S(x,y) + I_{dark}(x,y,T)\cdot t_{exp} + O_{pix}(x,y) + O_{col}(y) + O_{row}(x)\right] + O_{adc}\right) + n_q\]


其中：


- $S(x,y)$ 是由光子产生的有效信号
- $I_{dark}(x,y,T)$ 是温度相关暗电流
- $t_{exp}$ 是曝光时间
- $O_{pix}, O_{col}, O_{row}$ 分别表示像素、列、行的固定偏移
- $g_a$ 是模拟增益
- $O_{adc}$ 是ADC基线偏移
- $Q(\cdot)$ 表示ADC量化与可能的压缩编码
- $n_q$ 是量化误差与残余噪声


这个模型说明：RAW数据并不等于“真实光照”，它是光信号、器件偏移、温漂和读出链路误差的叠加结果。ISP前端校正的本质，就是尽可能把这些非理想项从观测值中剥离出去。


### 4.1.2 典型处理顺序


工程上常见的RAW前端处理链路如下：


```
Sensor ADC Output
      |
      v
[Optical Black Statistics / Black Level]
      |
      v
[Dark Current Compensation]
      |
      v
[Row/Column FPN Correction]
      |
      v
[Linearization / Decompanding]
      |
      v
[PRNU / Flat-Field Correction]
      |
      v
[Gain & Offset Normalization]
      |
      v
To Lens Shading / Defect Pixel / Demosaic
```


这个顺序并非唯一，但有强烈的工程逻辑：


1. **先减偏移，再做乘法校正**。黑电平、暗电流和大部分FPN是加性误差，若在乘性校正之后再减，会被不必要地放大。
2. **先线性化，再做依赖“相对响应”的校正**。PRNU本质上是像素响应不一致，在线性域中更容易建模和补偿。
3. **增益与偏移归一化要感知模式切换**。不同ISO、DCG模式和HDR通路可能共享算法，却不共享标定参数。


### 4.1.3 前端校正失败的系统后果


如果RAW校正不准，后续模块通常会出现连锁反应：


- 黑电平偏高：暗部发灰，动态范围被压缩，AE/AWB统计偏移
- 黑电平偏低：暗部剪切，阴影细节不可恢复
- 列FPN残留：去噪器把条纹误判为纹理，难以清除
- 暗电流建模错误：长曝光和高温场景下出现块状亮斑
- 线性化错误：3A统计、降噪强度和HDR融合权重全部失真
- PRNU校正不足：均匀平面出现固定纹理，目标检测背景不稳定


对自动驾驶系统而言，更严重的问题是同一场景在不同环境条件下产生不一致特征，进而影响感知网络的域稳定性。


## 4.2 Black Level Correction原理与校准方法


### 4.2.1 什么是黑电平


理想情况下，在无光照、零信号输入时，传感器输出应为0。但真实系统不会这样工作，原因包括：


- 像素复位电路带来的基线偏移
- 列放大器和ADC输入失配
- 相关双采样（CDS）后的残余偏置
- 为避免负数截断而故意引入的数字抬升


因此，RAW中的“0码值”通常不是物理意义上的黑，而是一个预留的数字基线。Black Level Correction（BLC）的目标，就是减去这个基线，使无光输入尽可能回到真实零点附近。


对Bayer传感器，黑电平通常按颜色平面独立建模：


\[B = \{B_R, B_{Gr}, B_{Gb}, B_B\}\]


校正公式为：


\[P_{blc}(x,y,c) = \max\left(P_{raw}(x,y,c) - B_c,\ 0\right)\]


这里的 $c \in {R, Gr, Gb, B}$，之所以区分两个绿色，是因为上下文中它们可能处于不同列/微透镜/读出路径，偏置并不完全相同。


### 4.2.2 Optical Black像素与实时估计


许多传感器在有效成像区域边缘预留遮光像素（Optical Black, OB），这些像素理论上不受光照，只反映读出链路偏移和暗电流。ISP可以利用它们实时估计黑电平：


\[\hat{B}_c = \frac{1}{N_c} \sum_{(x,y)\in \Omega_{OB,c}} P_{raw}(x,y,c)\]


其中 $\Omega_{OB,c}$ 是颜色平面 $c$ 对应的OB区域。


典型做法包括：


1. **帧级平均**：对整帧OB取均值，适合稳定场景
2. **行级更新**：每行或每若干行更新一次，适合存在行漂移的读出链路
3. **鲁棒估计**：使用trimmed mean或中值，避免OB区域被偶发串扰污染


实时估计的优点是能跟踪温漂和电源漂移；缺点是若OB区域质量差，或强干扰耦合到OB像素，估计会不稳定。


### 4.2.3 静态标定与动态跟踪


工业产品中，黑电平通常不是“只靠实时估计”或“只靠工厂常数”，而是两者结合：


\[B_c(T,g_a,m) = B_{c,ref}(m) + \Delta B_{temp}(T,m) + \Delta B_{gain}(g_a,m)\]


其中：


- $T$ 是温度
- $g_a$ 是模拟增益
- $m$ 是工作模式，如普通模式、DCG高增益模式、HDR短曝光通路等


静态标定给出各模式下的参考黑电平，动态部分则依靠OB统计、温度表或时域跟踪更新。


时域平滑常用：


\[B_c^{(t)} = \alpha \cdot B_c^{(t-1)} + (1-\alpha)\cdot \hat{B}_c^{(t)}\]


其中 $\alpha$ 一般取0.8到0.98。数值越大，噪声越小，但对快速漂移响应越慢。


### 4.2.4 定点实现与位宽设计


黑电平减法虽然简单，却直接决定后续模块的信号基准，位宽设计不能随意。


若输入为12bit RAW，黑电平可能在64到256码值之间。常见实现策略：


- 输入扩展到13到14bit内部位宽，防止后续补偿产生中间负值
- 减法后执行下限裁剪，但保留足够小数位供后续模块使用
- 若后续还有乘法校正，建议先进入更高精度内部域，如 `12bit -> 16bit`


RTL结构通常很简单：


```
RAW In --> [Channel Select] --> [Subtract Bc] --> [Clamp] --> RAW_BLC
```


真正难点不在减法器，而在参数切换一致性：如果帧中途切换寄存器，可能出现前半帧用旧黑电平、后半帧用新黑电平的灾难性不连续，因此一般要使用影子寄存器和frame-sync生效机制。


### 4.2.5 自动驾驶场景的额外要求


车载系统常见以下特殊约束：


- 温度范围大，黑电平不能只在室温标定
- 多摄像头系统要求跨传感器黑场一致，便于拼接与融合
- 功能安全场景要求OB异常可检测，例如OB均值突变、方差过大、饱和像素比例异常


因此，BLC模块往往要输出统计信息给系统监控模块，而不仅仅输出校正后的像素。


## 4.3 固定模式噪声（FPN）消除


### 4.3.1 FPN的类型


固定模式噪声（Fixed Pattern Noise, FPN）是指在相同输入条件下、空间上稳定重复出现的噪声结构。它不同于随机噪声，后者会在时间上波动；FPN在多帧平均后反而更加明显。


常见FPN可分为：


1. **偏移型FPN（Offset FPN）** 无光照时仍存在
2. 主要表现为列纹、行纹、局部偏置块
3. **增益型FPN（Gain FPN）** 随照度增强而放大
4. 本质上与PRNU相关，但更强调读出链路增益失配
5. **列FPN / 行FPN** 由列放大器、列ADC、行选择器不匹配造成
6. 是最常见、最显眼的条纹来源
7. **模式切换FPN** 某些增益档位、HDR通路或binning模式下单独出现


在工程实现里，Offset FPN通常在黑电平/暗电流附近处理，Gain FPN与PRNU有一定重叠，但标定手段和更新节奏不同。


### 4.3.2 列FPN的建模与校正


假设某列存在稳定偏移 $\delta_{col}(y)$，则：


\[P(x,y) = S(x,y) + \delta_{col}(y) + n(x,y)\]


校正公式为：


\[P_{cfpn}(x,y) = P(x,y) - \hat{\delta}_{col}(y)\]


列偏移的估计方式主要有两类：


**方法A：暗场标定**


在暗场下拍摄多帧，计算每列均值：


\[\hat{\delta}_{col}(y) = \frac{1}{M \cdot H} \sum_{k=1}^{M}\sum_{x=1}^{H} P_k(x,y) - \bar{P}\]


其中 $H$ 为图像高度，$\bar{P}$ 为全局均值，用于去除公共偏移。


**方法B：在线高通估计**


对于纹理不强的区域，可用列均值减全局均值近似列偏移，但需要屏蔽强边缘和高对比目标，否则真实内容会泄漏进校正量。


### 4.3.3 行/列联合FPN与低秩观点


当行FPN和列FPN同时存在时，可以写成：


\[P(x,y) = S(x,y) + a_x + b_y + \epsilon(x,y)\]


其中 $a_x$ 是行偏移，$b_y$ 是列偏移。这个模型本质上是一个低秩加性结构。标定时可用交替估计：


\[a_x = \frac{1}{W}\sum_{y} (P(x,y)-b_y), \qquad b_y = \frac{1}{H}\sum_{x}(P(x,y)-a_x)\]


迭代2到3轮通常即可收敛。


对硬件来说，列FPN更容易实时处理，因为只需要一条“列参数表”；行FPN若用整行统计实时更新，容易引入额外行缓存压力，因此很多系统采用“工厂标定 + 慢更新”策略。


### 4.3.4 FPN校正与真实纹理的冲突


FPN去除看似简单，实际容易伤害真实图像结构。最常见错误是把大面积水平/垂直纹理当成行列偏置减掉。


例如在自动驾驶场景中：


- 栅栏、车道线、建筑百叶窗会产生强方向性结构
- 室内机器人场景里地板纹理和货架条纹也可能与列FPN形态相似


因此，在线FPN估计通常需要：


- 使用低纹理区域掩码
- 多帧时域平均
- 与历史参数比较，只允许缓慢漂移
- 设置最大校正幅度，避免瞬时过补偿


### 4.3.5 硬件实现示意


```
RAW_BLC
   |
   v
[Address by Column/Row]
   |
   +--> [Column Offset LUT]
   |
   +--> [Row Offset LUT]
   |
   v
[Subtract / Combine]
   |
   v
RAW_FPN_Corrected
```


典型资源权衡：


- 列表法：存储开销随分辨率列数线性增长，最稳定
- 稀疏分段法：若相邻列偏移相似，可分段压缩
- 在线估计法：节省标定表，但控制逻辑更复杂，误校正风险更高


## 4.4 暗电流补偿与温度依赖性


### 4.4.1 暗电流的来源


暗电流是指在无光条件下，由热激发产生的电子流。其主要来源包括：


- 耗尽区的热激发
- 界面缺陷与陷阱态释放
- 边缘泄漏与工艺应力
- 长曝光下的积累效应


暗电流具有两个关键特征：


1. **与曝光时间近似成正比**
2. **对温度极其敏感**


因此它与黑电平不同。黑电平更多是读出基线偏移，而暗电流是“会随时间积分增长”的电荷项。


### 4.4.2 基本模型


最常用的一阶模型为：


\[D_{dark}(x,y,T,t_{exp}) = I_{dark}(x,y,T)\cdot t_{exp}\]


若用参考温度 $T_0$ 表示，可近似写为：


\[I_{dark}(x,y,T) = I_{dark}(x,y,T_0)\cdot 2^{\frac{T-T_0}{\Delta T}}\]


其中 $\Delta T$ 常取7到8°C，即温度每升高约7到8°C，暗电流翻倍。


完整补偿公式：


\[P_{dc}(x,y) = P_{in}(x,y) - \hat{I}_{dark}(x,y,T)\cdot t_{exp}\]


如果仅用全局平均值替代逐像素模型，则：


\[P_{dc}(x,y) = P_{in}(x,y) - \hat{\mu}_{dark}(T,g_a,m)\cdot t_{exp}\]


这会显著降低实现成本，但无法处理空间不均匀的热像素和暗电流热点。


### 4.4.3 暗帧法与温度查表法


暗电流补偿常见有两套工程路径。


**路径A：暗帧模板**


在工厂或系统维护阶段，采集不同温度、曝光、增益组合下的暗帧模板：


\[\mathcal{D}(x,y; T_i, t_j, g_k)\]


运行时根据当前状态插值：


\[\hat{D}_{dark} = \text{Interp}\left(\mathcal{D}; T, t_{exp}, g_a\right)\]


优点：


- 精度高，可覆盖空间非均匀性
- 对热像素和热点有效


缺点：


- 存储量大
- 状态维度一多，插值复杂


**路径B：温度-曝光分离模型**


把暗电流分解为模板和比例项：


\[\hat{D}_{dark}(x,y) = D_{ref}(x,y) \cdot f_T(T) \cdot f_t(t_{exp}) \cdot f_g(g_a)\]


优点是压缩参数量；缺点是当不同模式下空间分布形态都变了时，单一模板不足以覆盖。


### 4.4.4 长曝光与车载高温场景


暗电流补偿在以下场景尤其关键：


- 夜间长曝光监控
- 车规传感器高结温环境
- 低照机器人导航
- HDR长曝光通路


例如参考温度25°C时暗电流为10 e-/s，85°C时若每8°C翻倍，则：


\[I_{85} = 10 \cdot 2^{\frac{85-25}{8}} = 10 \cdot 2^{7.5} \approx 1810 \text{ e-/s}\]


若曝光时间为20ms，则每像素平均暗信号约为：


\[Q_{dark} \approx 1810 \times 0.02 = 36.2 \text{ e-}\]


这已经足以显著抬升暗部，并改变后续降噪和检测模块的噪声基线。


### 4.4.5 暗电流与热像素的边界


暗电流补偿和坏点修复不是同一件事，但二者高度相关。


- 大多数像素的暗电流随温度平滑变化，适合模板补偿
- 少数像素暗电流极高，表现为热像素，更适合在第6章的坏点处理中单独修复


工程上可采用分层策略：


1. 先做全局/局部暗电流补偿
2. 再对残留异常亮点做热像素检测与修复


这样可以避免把大量正常暗漂移都交给坏点模块处理，导致误检率上升。


### 4.4.6 硬件实现与表项组织


常见硬件组织方式：


```
Temperature Sensor + Exposure Register + Gain Mode
                    |
                    v
             [Dark Model Selector]
                    |
                    v
          [Global / Tile / Pixel Template]
                    |
                    v
              [Scale by t_exp]
                    |
                    v
                 [Subtract]
```


实现层级通常有三种：


- **全局补偿**：仅一个标量，成本最低
- **Tile补偿**：例如16×12热图，兼顾空间变化与存储量
- **像素级补偿**：效果最好，适合高端系统或离线模板加载


## 4.5 线性化处理与查找表设计


### 4.5.1 为什么要线性化


许多传感器并不是把光子数线性映射到数字码值。非线性可能来自：


- 像素转换增益随电荷量变化
- 列ADC本身的积分非线性（INL）
- 片上传感器压缩（companding）
- HDR模式下不同通路拼接的分段响应


而ISP后续很多模块默认“输入近似线性”：


- 降噪强度估计依赖噪声与信号的关系
- HDR融合需要比较不同曝光的相对亮度
- 色彩矩阵和白平衡最好在线性域工作


因此，线性化的目标是求出一个逆映射，使输出尽可能与入射光能量成正比。


### 4.5.2 标定响应曲线


设传感器理想响应为 $L$，实际测得数字输出为 $D = f(L)$，则线性化需要近似求逆：


\[L \approx f^{-1}(D)\]


标定时一般在多组均匀照度下采样，得到一系列点 $(L_i, D_i)$，然后构建LUT或分段模型。


常见误差指标包括：


\[\epsilon_{lin} = \max_i \left| \frac{\hat{L}_i - L_i}{L_{FS}} \right|\]


其中 $L_{FS}$ 表示满量程信号。对高质量RAW链路，线性化残差通常希望低于0.5%到1% FS。


### 4.5.3 LUT设计方法


最常见的是1D LUT：


\[P_{lin} = LUT(P_{in})\]


若输入是12bit，则全精度LUT有4096项。为了节省面积，常用以下办法：


1. **稀疏采样 + 线性插值** 例如256项或512项
2. 高码值区可更稀疏，低码值区更密集
3. **分段线性模型** \(P_{lin} = a_k \cdot P_{in} + b_k,\quad P_{in}\in [T_k,T_{k+1})\)
4. **对数/指数域压缩表** 适合传感器使用了companding的情况
5. **模式相关LUT** 普通模式、DCG模式、HDR短中长曝光路径分别使用不同LUT


### 4.5.4 LUT插值精度与单调性


线性化LUT有两个容易被低估的工程问题。


**问题1：插值误差**


若相邻节点跨度过大，低码值区会出现响应误差，导致暗部统计不稳定。


**问题2：单调性破坏**


LUT若非严格单调，可能出现输入增大而输出不增的现象，严重影响排序、直方图和3A统计。


因此，LUT生成通常应满足：


\[LUT[i+1] \ge LUT[i]\]


必要时可对标定数据做单调回归（monotonic regression）或后处理修正。


### 4.5.5 线性化在HDR和DCG中的作用


对于双转换增益（DCG）或多曝光HDR，线性化不仅是“修正非线性”，还承担“统一信号域”的任务。


例如高增益路径和低增益路径输出分别为：


\[D_H = f_H(L), \qquad D_L = f_L(L)\]


经过线性化后：


\[L_H = f_H^{-1}(D_H), \qquad L_L = f_L^{-1}(D_L)\]


只有在统一到相同线性域后，两条路径才能无偏融合。


这也是为什么某些系统把黑电平、线性化和模式归一化视为一个联合模块，而不是三个孤立模块。


### 4.5.6 硬件实现与吞吐量


线性化LUT通常位于高吞吐路径中，因此要特别注意：


- LUT读端口数是否支持每周期多个像素并行
- 插值运算是否会引入额外流水级
- 模式切换时LUT是否支持双缓冲
- 是否允许同一帧内跨tile切换参数，通常不建议


典型结构：


```
RAW_FPN
   |
   v
[LUT Address Generator] --> [LUT SRAM]
   |                           |
   +--------> [Interpolator] <-+
               |
               v
            RAW_Linear
```


## 4.6 PRNU（光响应非均匀性）校正


### 4.6.1 PRNU的定义


PRNU（Photo Response Non-Uniformity）描述的是在同一均匀光照下，不同像素输出响应存在稳定差异。它属于乘性误差，更准确地说：


\[P(x,y) = \alpha(x,y) \cdot S(x,y) + \beta(x,y) + n(x,y)\]


其中：


- $\alpha(x,y)$ 表示像素响应增益差异，对应PRNU
- $\beta(x,y)$ 表示偏移项，对应DSNU/黑偏置类误差


只有在充分去除偏移类误差后，PRNU才容易被准确测量和校正。


PRNU常以百分比表示：


\[PRNU = \frac{\sigma_{flat}}{\mu_{flat}} \times 100\%\]


这里 $\mu_{flat}$ 和 $\sigma_{flat}$ 是均匀照明下像素响应的均值和标准差。


### 4.6.2 平场标定与增益图生成


PRNU标定通常使用均匀光源（积分球或高均匀背光）拍摄平场图像。去除黑电平和暗电流后，可为每个像素或每个网格生成校正增益：


\[G_{prnu}(x,y,c) = \frac{\mu_c}{P_{flat}(x,y,c)}\]


校正时：


\[P_{prnu}(x,y,c) = P_{lin}(x,y,c) \cdot G_{prnu}(x,y,c)\]


为了避免单帧噪声污染，通常会对多帧平场图做平均：


\[P_{flat}(x,y,c) = \frac{1}{M}\sum_{k=1}^{M} P_k(x,y,c)\]


### 4.6.3 像素级、网格级与混合式PRNU


**像素级PRNU**


- 精度最高
- 对高分辨率传感器存储压力大
- 对坏点和局部异常最敏感


**网格级PRNU**


- 将图像划分为粗网格，存储每个格点增益
- 运行时双线性插值
- 存储量大幅下降


**混合式PRNU**


把低频不均匀性交给网格，高频残差交给小幅修正表，是高分辨率系统常见策略。


要注意：PRNU与第5章的Lens Shading在表面上都像“乘一个增益图”，但它们来源不同。


- PRNU：传感器像素/读出链路响应差异
- Lens Shading：镜头照度衰减与光学系统引起的空间不均匀


若标定流程控制不好，这两者很容易相互污染。


### 4.6.4 PRNU与Lens Shading的解耦


设观测平场为：


\[P_{flat}(x,y) = S_0 \cdot L(x,y) \cdot R(x,y)\]


其中：


- $L(x,y)$ 是镜头渐晕/光学 shading
- $R(x,y)$ 是像素响应差异


如果直接把 $1/P_{flat}(x,y)$ 当作PRNU表，则实际上把镜头和传感器效应混在一起了。工业流程里常见三种解耦方法：


1. **系统级接受混合校正** 让第4章和第5章的边界弱化
2. 对固定模组产品可行
3. **更换传感器裸片或近轴光学条件单独标定传感器响应** 成本高，但可获得更纯净PRNU
4. **用低阶光学模型拟合低频部分，剩余高频当作PRNU** 工程上最常见


也就是说，PRNU和Lens Shading的划分不仅是物理问题，更是产品校准分工问题。


### 4.6.5 乘法校正的噪声放大问题


PRNU校正本质是乘法，会放大噪声，尤其在低响应区域更明显。


若某处响应很低，增益接近 $G_{max}$，则：


\[\sigma_{out}^2 \approx G_{prnu}^2 \cdot \sigma_{in}^2\]


因此需要限制最大增益：


\[G_{prnu}(x,y,c) \le G_{clip}\]


典型做法：


- 对增益表做上限裁剪
- 在极低亮区降低PRNU校正强度
- 将高频PRNU残差限制在较小幅度内


### 4.6.6 硬件实现


```
RAW_Linear
   |
   v
[Grid / Pixel Gain Fetch]
   |
   v
[Interpolation]
   |
   v
[Multiplier + Rounding]
   |
   v
RAW_PRNU_Corrected
```


关键设计点：


- 乘法后位宽至少增加若干保护位
- 对不同颜色平面使用独立表项
- 表项更新需与模式切换绑定
- 避免和Lens Shading重复校正


## 4.7 传感器增益与偏移校准


### 4.7.1 为什么需要统一增益与偏移


除了前面提到的黑电平、FPN、PRNU，传感器还存在更宏观的模式差异：


- 不同模拟增益档位的实际放大倍数不等于名义值
- 不同颜色通道的基础响应不一致
- DCG高低转换增益路径有独立偏移和斜率
- 多摄像头系统中不同模组存在全局响应偏差


因此，需要把不同工作模式统一映射到一个共同的工程域，方便后续算法和跨相机系统使用。


### 4.7.2 斜率-截距模型


最简单的归一化形式是仿射变换：


\[P_{norm} = a(m,c)\cdot P_{in} + b(m,c)\]


其中：


- $a(m,c)$ 是模式 $m$、颜色平面 $c$ 对应的归一化增益
- $b(m,c)$ 是残余偏移修正


若系统已经完成BLC和线性化，则 $b$ 通常较小；但在多路径融合场景下，保留这个自由度有助于做精细对齐。


### 4.7.3 多增益档位校准


假设名义ISO从100切到400，理论上数字响应应放大4倍，但实际可能由于模拟链路误差变成3.82倍或4.11倍。若不修正：


- 噪声模型会失准
- 3A跨档位切换会出现亮度跳变
- 多帧融合难以对齐


标定时可在一组均匀照度下拟合每档位斜率：


\[a_k = \frac{\sum_i L_i \cdot D_{k,i}}{\sum_i D_{k,i}^2}\]


然后把档位 $k$ 归一化到参考档位。


### 4.7.4 双转换增益（DCG）路径对齐


对于DCG，常见情况是低亮度使用高转换增益路径，高亮度使用低转换增益路径。为了避免拼接或切换时台阶，需满足在重叠线性区：


\[a_H \cdot D_H + b_H \approx a_L \cdot D_L + b_L\]


可在重叠曝光区做最小二乘拟合：


\[\min_{a_H,b_H,a_L,b_L} \sum_i \left[(a_H D_{H,i}+b_H) - (a_L D_{L,i}+b_L)\right]^2\]


对HDR融合而言，这一步是后续权重计算可靠性的基础。


### 4.7.5 多摄像头系统的一致性


在环视、双目、三目和具身智能多相机系统中，增益与偏移校准还承担“跨相机一致性”任务。


若相机A和B看同一灰卡，但输出不同，则：


- 拼接边界明显
- 立体匹配代价不稳定
- 视觉里程计和SLAM的光度一致性假设被破坏


因此常用一层跨相机归一化：


\[P_i' = \gamma_i \cdot P_i + \eta_i\]


其中 $i$ 表示不同相机，$\gamma_i,\eta_i$ 由整机标定得到。


### 4.7.6 寄存器组织与参数管理


增益与偏移校准最大的工程难点不是公式，而是参数爆炸。参数维度可能同时依赖：


- 传感器模式
- 分辨率与binning方式
- 模拟增益档位
- 曝光路径
- 温度区间
- 颜色通道


因此寄存器与NVM表项设计应遵循：


1. 参数按模式分组，避免运行时交叉污染
2. 支持影子加载和帧边界切换
3. 支持回退到安全默认值
4. 支持参数版本号和CRC校验


## 4.8 一条可落地的RAW校正流水线


综合本章内容，一个工程上稳健的RAW校正流程可写为：


\[\begin{aligned}
P_1 &amp;= \max(P_{raw} - B_c,\ 0) \\
P_2 &amp;= \max(P_1 - D_{dark}(T,t_{exp},g_a),\ 0) \\
P_3 &amp;= P_2 - O_{row}(x) - O_{col}(y) \\
P_4 &amp;= f_m^{-1}(P_3) \\
P_5 &amp;= P_4 \cdot G_{prnu}(x,y,c) \\
P_{out} &amp;= a(m,c)\cdot P_5 + b(m,c)
\end{aligned}\]


这里每一步都对应明确的物理含义：


- $P_1$：去掉静态基线
- $P_2$：去掉随时间和温度积分的暗信号
- $P_3$：去掉空间固定偏移
- $P_4$：恢复线性响应域
- $P_5$：补偿像素响应差异
- $P_{out}$：统一到系统参考增益域


对不同产品，步骤顺序和细节可以变化，但总体原则不变：先处理加性误差，再处理乘性误差，再做模式归一化。


## 本章小结


原始数据校正是ISP前端中最“底座化”的部分。它不直接创造“漂亮的画面”，但决定了后续所有图像与视觉算法是否建立在可信信号之上。


本章关键点如下：


1. **Black Level Correction** 用于去除读出基线偏移，是一切后续处理的零点参考。
2. **FPN消除** 针对稳定的空间结构噪声，尤其是列/行偏移条纹。
3. **暗电流补偿** 与温度、曝光时间强相关，在高温和长曝光场景中至关重要。
4. **线性化处理** 把传感器和ADC的非线性响应映射回统一线性域，是HDR、降噪和色彩处理的基础。
5. **PRNU校正** 处理像素响应不一致，但必须注意与Lens Shading的边界和噪声放大问题。
6. **增益与偏移校准** 用于对齐不同模式、不同通路和多相机系统的整体响应。


关键工程原则：


- 先减法，后乘法
- 先建立稳定零点，再建立统一斜率
- 参数必须感知模式、温度和增益状态
- 任何“在线自适应”都必须限制更新速度和最大修正幅度


## 练习题


### 基础题（帮助熟悉材料）


**练习4.1** 黑电平减法计算

某12bit传感器在RGGB四个平面的黑电平分别为：$B_R=64$，$B_{Gr}=60$，$B_{Gb}=62$，$B_B=68$。某个蓝色像素原始值为92。


1. 该像素做BLC后的输出是多少？
2. 若内部要求保留非负输出，是否需要裁剪？


*Hint: 直接按对应颜色平面减去黑电平。*


<details>
<summary>答案</summary>

该像素是蓝色平面，因此减去 $B_B=68$：

$P_{blc} = 92 - 68 = 24$

结果为24，大于0，因此不需要裁剪。
</details>


**练习4.2** 温度相关暗电流估算

已知25°C时暗电流为12 e-/s，温度每升高8°C翻倍。请计算73°C、曝光时间10ms时的平均暗电荷。


*Hint: 先算温度相对25°C升高了多少个8°C。*


<details>
<summary>答案</summary>

温升为 $73-25=48°C$，对应6个翻倍周期：

$I_{73} = 12 \cdot 2^6 = 768 \text{ e-/s}$

曝光时间10ms，即0.01s：

$Q_{dark} = 768 \times 0.01 = 7.68 \text{ e-}$

平均暗电荷约为7.68 e-。
</details>


**练习4.3** 列FPN校正

某暗场图像4列的列均值分别为[70, 74, 69, 75]，全局均值为72。请给出每列的偏移校正量。


*Hint: 列偏移可用列均值减全局均值。*


<details>
<summary>答案</summary>

列偏移估计为：

- 第1列：$70 - 72 = -2$
- 第2列：$74 - 72 = 2$
- 第3列：$69 - 72 = -3$
- 第4列：$75 - 72 = 3$

若做校正，通常从每列像素中减去该偏移量，即：

- 第1列减去-2，等价于加2
- 第2列减去2
- 第3列减去-3，等价于加3
- 第4列减去3
</details>


**练习4.4** PRNU增益计算

某绿色平面平场标定后，全局均值为1000，某像素响应为920。请计算该像素的PRNU校正增益，并说明这是“增亮”还是“减亮”。


*Hint: 增益等于均值除以该像素响应。*


<details>
<summary>答案</summary>

校正增益为：

$G_{prnu} = \frac{1000}{920} \approx 1.087$

因为增益大于1，所以这是一次“增亮”校正。
</details>


### 挑战题（深度思考）


**练习4.5** 线性化LUT压缩设计

输入RAW为12bit，理想全精度线性化LUT需要4096项。现在只允许存储256项LUT，请设计一种兼顾低码值精度和硬件成本的方案，并说明为什么低码值区应分配更多节点。


*Hint: 从噪声建模、暗部精度和插值误差三个角度思考。*


<details>
<summary>答案</summary>

可采用“非均匀分段 + 线性插值”方案：

1. 在低码值区密集布点，例如前25%的码值范围分配50%以上节点
2. 中高码值区逐渐稀疏
3. 运行时通过区间查找和线性插值得到输出

原因：

- 暗部码值小，任何少量误差都会带来较大的相对误差
- 黑电平、暗电流和噪声估计主要影响低码值区，低码值线性化误差会直接破坏后续统计
- 高频非线性往往也更集中在低码值附近
- 高码值区信噪比高、相对误差更容易容忍，可减少节点节省存储

硬件上只需一张256项LUT、一个地址生成器和一个线性插值器，代价远低于4096项全查表。
</details>


**练习4.6** PRNU与Lens Shading边界划分

你在均匀光场下得到一个明显中心亮、边缘暗的增益图。请分析其中哪些成分可能属于PRNU，哪些更可能属于Lens Shading，并给出一种工程上可行的拆分办法。


*Hint: 关注空间频率。*


<details>
<summary>答案</summary>

分析思路：

- 大尺度、缓慢变化、近似径向对称的部分，更可能来自Lens Shading
- 高频、局部细碎、与像素/列结构相关的部分，更可能来自PRNU或读出链路不一致

工程拆分办法：

1. 先对增益图做低通拟合，例如径向多项式或粗网格拟合
2. 拟合得到的低频部分划入Lens Shading模块
3. 原始增益图除以低频拟合结果，剩余高频残差划入PRNU模块
4. 对PRNU残差设置幅度上限，避免噪声放大

这种“低频归光学、高频归传感器”的方法不是纯物理分解，但工程上高效且稳定。
</details>


**练习4.7** 多增益档位对齐

某传感器在同一均匀照度下，ISO100档输出均值为800，ISO400档输出均值为3050。理论上ISO400应是ISO100的4倍。


1. 实际增益比是多少？
2. 若要把ISO400归一化到理想4倍，应乘以多少修正系数？


*Hint: 先求 $3050/800$，再与4比较。*


<details>
<summary>答案</summary>

1. 实际增益比：

$r = \frac{3050}{800} = 3.8125$

2. 为了把ISO400映射到理想4倍域，需要乘以：

$k = \frac{4}{3.8125} \approx 1.0492$

也就是说，ISO400路径还需要约4.9%的额外增益修正。
</details>


**练习4.8** 车载高温场景的校正策略

为一颗车规摄像头设计RAW前端校正策略，工作温度范围为-40°C到125°C，要求在隧道出口和夏季暴晒后都保持响应稳定。请说明：


1. 哪些参数必须随温度切换或插值
2. 哪些参数更适合工厂静态标定
3. 如何避免在线参数更新导致画面闪变


*Hint: 区分“快速漂移”和“稳定结构误差”。*


<details>
<summary>答案</summary>

建议策略：

1. 必须随温度切换或插值的参数：
   - 黑电平
   - 暗电流模板或暗电流比例因子
   - 某些模式下的残余偏移修正

2. 更适合工厂静态标定的参数：
   - 线性化LUT
   - 列/行FPN基础表
   - PRNU增益图
   - 多增益档位之间的基础对齐系数

3. 避免闪变的方法：
   - 参数使用影子寄存器，在帧边界统一生效
   - 对在线估计量做时域平滑
   - 设置参数变化上限，避免单帧跳变
   - 当温度传感器异常或OB统计失真时回退到安全参数集

核心思想是：稳定结构误差靠工厂标定，温漂型误差靠有限速的在线补偿。
</details>


## 常见陷阱与错误 (Gotchas)


### 1. 把黑电平和暗电流混为一谈


**问题**：认为两者都属于“暗场偏移”，只做一个统一常数减法。

**后果**：长曝光、高温场景下补偿严重不足。

**建议**：把“静态基线偏移”和“随曝光积分的暗信号”拆开建模。


### 2. 在乘法校正之后再减黑电平


**问题**：先做PRNU或其他增益校正，再做BLC。

**后果**：黑偏置被不必要放大，暗部误差显著。

**建议**：遵循“先减法、后乘法”的基本顺序。


### 3. 在线列FPN估计被真实场景污染


**问题**：直接把列均值变化视为列偏移。

**后果**：垂直纹理被误消除，图像出现反向条纹。

**建议**：加入低纹理掩码、多帧平滑和最大修正幅度限制。


### 4. 线性化LUT不保证单调


**问题**：直接拟合实验数据，未处理测量噪声。

**后果**：输出出现局部非单调，破坏直方图和3A统计。

**建议**：对LUT生成过程增加单调性约束。


### 5. PRNU与Lens Shading重复补偿


**问题**：第4章和第5章都对同一低频空间不均匀性做了乘法校正。

**后果**：边缘过度增益，噪声被放大。

**建议**：明确标定分工，或在工具链中对两张增益图做联合审查。


### 6. 忽视模式切换一致性


**问题**：普通模式、HDR模式、DCG模式共用一套参数。

**后果**：切换时亮度台阶、噪声模型失配、融合错误。

**建议**：参数必须按模式建表，并通过帧同步切换。


### 7. 只看平均误差，不看最坏情况


**问题**：标定报告只给均值RMSE。

**后果**：少量极端列、热点或模式边界问题被掩盖。

**建议**：同时检查最大误差、百分位误差和空间热图。


## 最佳实践检查清单


### 建模与标定


- 明确区分黑电平、暗电流、Offset FPN、Gain FPN、PRNU
- 在不同温度、曝光、模拟增益和模式下采集标定数据
- 对RGGB四个平面分别建模，而不是简单共享参数
- 评估PRNU与Lens Shading的耦合程度
- 为多摄像头系统准备跨相机一致性标定


### 硬件架构


- 前端流水线遵循“先减法、后乘法、再归一化”
- 所有关键参数支持影子寄存器和帧边界生效
- LUT、增益图和偏移表支持模式索引和CRC校验
- 乘法与插值后的内部位宽留有保护位
- 在线统计路径与主像素路径解耦，避免互相阻塞


### 参数管理


- 黑电平支持OB实时估计与工厂表项融合
- 暗电流参数至少感知温度和曝光时间
- FPN校正量设置变化上限和饱和保护
- 线性化LUT保证单调性
- PRNU增益图设置最大增益限制


### 验证与系统联调


- 验证暗场、平场、灰卡、强纹理场景下的校正效果
- 检查高温、低温、模式切换时是否出现亮度台阶
- 观察列/行条纹在多帧平均后是否仍然存在
- 量化线性化误差对AE/AWB/降噪/HDR的影响
- 检查多相机拼接和立体匹配的一致性
- 为功能安全场景输出OB异常、温度异常和参数失配告警
