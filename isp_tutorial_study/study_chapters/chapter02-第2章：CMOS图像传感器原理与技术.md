# 第2章：CMOS图像传感器原理与技术


> 课程阶段：传统 ISP 与成像基础　|　难度：入门　|　优先级：核心
>
> 建议用时：2–3 小时阅读 + 1–2 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**解释 CMOS 像素、噪声、动态范围、增益和曝光之间的关系。**

## 1. 本章先解决“传感器到底测到了什么”

初学 ISP 时，很多人会把 RAW 当成“相机还没处理的照片”。这会导致后面所有理解都偏掉。更准确的说法是：

```text
CMOS 图像传感器输出的 RAW = 每个像素对光照的带噪声、带偏移、带颜色采样限制的数字测量值
```

也就是说，RAW 首先是测量，不是图像表达。传感器并不知道“天空”“人脸”“白墙”，它只是在某段曝光时间内，把落到像素上的光子转换成电荷，再把电荷读出来并量化成数字。这个过程中会发生很多不完美：

- 没有光也会有暗电流和黑电平。
- 光子到达本身是随机的，所以亮度也有 photon shot noise。
- 每个像素和每一列读出电路不可能完全一致，所以会有固定模式噪声。
- 像素能存的电子数有上限，所以高光会饱和。
- 读出不是所有行同时完成时，运动物体会发生 rolling shutter 形变。

这一章的核心目的，就是让你知道 ISP 前端为什么要做黑电平校正、坏点修复、固定模式噪声校正、暗电流补偿、线性化和增益/曝光相关调参。它们不是“画质玄学”，而是传感器物理测量带来的必然后果。

## 2. 用“水桶模型”理解像素

可以把每个像素想成一个很小的水桶：

```text
光子 = 雨滴
光电二极管 = 接雨水的桶
曝光时间 = 接雨水的时间
电子数 = 桶里收集到的水量
满阱容量 = 桶最多能装多少水
读出噪声 = 读刻度时手抖
暗电流 = 没下雨也漏进桶里的水
ADC = 把水量读成数字刻度
```

这个比喻能帮你理解几个关键点：

- 曝光时间越长，桶接到的光子越多，但暗电流也会积累更多。
- 桶满了以后再来光也装不下，这就是饱和。
- 小桶更容易满，高光动态范围可能更差；但小像素可以做更高分辨率。
- 读刻度本身有误差，所以暗部信号很容易被读噪淹没。
- 即使两个桶接到同样的光，也可能因为制造差异读出不同值，这就是不均匀性。

这个模型很朴素，但足够支撑你理解 EMVA 1288、Photon Transfer Curve、SNR、dynamic range 和 full well capacity。

## 3. CMOS 像素从光到数字的完整流程

一个简化的 CMOS 像素读出流程可以写成：

```text
入射光子
  -> 硅中产生电子-空穴对
  -> 光电二极管收集电子
  -> 曝光时间内电荷积分
  -> 电荷转移到浮动扩散节点
  -> 源跟随器/列电路读出电压
  -> 模拟增益/PGA
  -> ADC 量化
  -> 输出 RAW code value
```

这里每一步都可能引入 ISP 后面要处理的问题。

| 流程位置 | 发生什么 | 可能带来的问题 | 后续 ISP/标定如何应对 |
|---|---|---|---|
| 光子入射 | 光子数量随机到达 | photon shot noise | 降噪、多帧融合、曝光控制 |
| 光电转换 | 光子转成电子 | 量子效率差异、波长响应差异 | 色彩校正、传感器选型 |
| 积分曝光 | 电荷累积 | 暗电流、饱和、溢出 | 暗场标定、HDR、AE |
| 像素读出 | 电荷转电压 | reset noise、source follower noise | CDS、读噪建模 |
| 列读出 | 列电路放大 | column FPN、banding | 列校正、FPN correction |
| ADC | 电压量化 | 量化噪声、非线性、黑电平偏移 | linearization、BLC |
| 数字输出 | RAW code | bit depth、black/white level | RAW metadata、前端校正 |

初学者要记住：RAW 里的数字值不是纯粹的“亮度”。它是光信号、噪声、偏移、增益和量化共同作用的结果。

## 4. 关键术语逐个拆开

### 4.1 光电二极管 Photodiode

光电二极管是像素里负责收集光生电子的区域。光子进入硅材料后，如果能量足够，就可能产生电子-空穴对。电子被收集起来，形成和光照相关的信号。

初学者理解即可：

- 光越强，产生的电子越多。
- 曝光时间越长，累积电子越多。
- 不同波长的光在硅中吸收深度不同，所以传感器结构会影响不同颜色响应。

### 4.2 Pinned Photodiode，PPD

现代 CMOS 图像传感器常用 PPD。它的重要意义是降低暗电流、改善电荷转移，并支持更低噪声读出。你不需要第一遍就会画器件能带图，但要知道：

- PPD 是现代低噪声 CMOS 像素的重要基础。
- 它和 4T 像素结构、相关双采样 CDS 一起，显著改善了图像传感器噪声表现。

### 4.3 满阱容量 Full Well Capacity

满阱容量是一个像素最多能容纳多少电子。它决定高光什么时候饱和。

```text
full well capacity 越大
  -> 高光越不容易饱和
  -> 最大 SNR 可能更高
  -> 动态范围上限更好
```

但更大的满阱通常需要更大的像素或更复杂结构，这会和分辨率、成本、读出速度产生冲突。

### 4.4 Black Level

Black level 是“没有有效光照时传感器输出的数字基线”。它不是错误，而是传感器读出链路的一部分。ISP 必须先知道黑电平在哪里，才能正确解释暗部。

如果 black level 处理错：

- 减少了：暗部发灰，颜色偏。
- 减多了：暗部被截断，细节没了。

### 4.5 White Level

White level 是 RAW 数值接近饱和的上限。它通常不是简单的 `2^bit_depth - 1`，因为传感器和相机厂商会保留黑电平、头部空间或采用压缩编码。

初学者要养成习惯：不要假设 12-bit RAW 的白点一定是 4095，应该看 metadata 或标定资料。

### 4.6 Quantum Efficiency，QE

量子效率表示入射光子中有多少比例最终转成可收集电子。它受像素结构、微透镜、背照式结构、波长和工艺影响。

直觉上：

```text
QE 高 -> 同样光照下收集到更多电子 -> 信号更强 -> 暗部更有利
```

### 4.7 Conversion Gain

conversion gain 描述电子数到电压或数字码值的转换比例。高 conversion gain 有利于读出小信号，但可能牺牲满阱或高光范围。很多现代传感器会用 dual conversion gain 在暗部和亮部之间折中。

### 4.8 Dynamic Range

动态范围可以直觉理解为：

```text
从刚能分辨暗部信号，到高光刚饱和之间，传感器能覆盖的亮度范围
```

常见近似：

```text
Dynamic Range ≈ full well capacity / noise floor
```

用 dB 表示时：

```text
DR(dB) = 20 * log10(max_signal / min_detectable_signal)
```

所以动态范围不是只由 bit depth 决定。14-bit ADC 不等于 14-bit 有效动态范围，如果噪声很大，低位可能只是噪声。

## 5. 噪声：初学者最容易混淆的部分

CMOS 传感器噪声可以先分成两大类：

```text
随机噪声：每一帧都随机变化
固定模式噪声：位置固定，看起来像固定纹理、条纹或坏点
```

### 5.1 Photon Shot Noise

光子到达像素是随机事件。即使场景亮度完全不变，每次曝光收集到的光子数也会波动。这种噪声满足近似泊松统计：

```text
如果平均收集 N 个电子
shot noise 的标准差约为 sqrt(N)
SNR 约为 N / sqrt(N) = sqrt(N)
```

这带来一个重要结论：

```text
光越多，绝对噪声越大，但相对噪声越小
```

所以亮部看起来更干净，暗部更脏。

### 5.2 Read Noise

读噪来自像素和读出电路，比如 reset noise、source follower noise、列放大器和 ADC。它和光照强弱不一定成比例，因此在暗部尤其明显。

暗部为什么难？因为真实信号很小，read noise 可能和信号同量级，甚至比信号还大。

### 5.3 Dark Current 和 Dark Current Shot Noise

暗电流是没有光时，由热激发等原因产生的电子。它随温度和曝光时间增加而变明显。

要区分两件事：

- 暗电流的平均模式可以通过 dark frame 估计和扣除。
- 暗电流本身也有 shot noise，这部分扣不掉，只能降低温度、缩短曝光或降噪。

这就是为什么长曝光、热环境、低照场景特别容易出现噪声和热像素。

### 5.4 Fixed Pattern Noise，FPN

FPN 是空间位置固定的不均匀性。它可能来自像素偏移、列电路差异、行电路差异、暗电流差异或响应增益差异。

初学时可以分成：

| 类型 | 中文理解 | 常见观察方式 | 校正思路 |
|---|---|---|---|
| DSNU | 暗信号不均匀 | 拍 dark frame | offset / dark correction |
| PRNU | 光响应不均匀 | 拍均匀平场 | gain map / flat field correction |
| Column FPN | 列固定偏差 | 暗场或平场看竖条纹 | per-column offset/gain |
| Row FPN | 行固定偏差 | 看横条纹 | per-row correction |
| Defect pixel | 单点异常 | 亮点/暗点/闪点 | bad pixel map / dynamic detection |

注意：FPN 不等于所有噪声。FPN 的特点是位置固定，所以可以标定；随机噪声位置不固定，只能统计抑制。

### 5.5 Quantization Noise

ADC 把连续电压变成离散数字，会引入量化误差。如果 ADC bit depth 太低，细微亮度变化会被粗糙分档。实际系统中，量化噪声要和读噪、shot noise 一起看；如果传感器噪声已经大于 1 LSB，继续提高 ADC bit depth 未必明显改善画质。

## 6. Photon Transfer Curve：为什么它是理解传感器的钥匙

Photon Transfer Curve，PTC，是图像传感器表征中的重要工具。它通过不同曝光下的均值和方差关系，帮助估计 conversion gain、read noise、full well capacity、SNR 和动态范围。

直觉流程：

1. 对均匀光源拍多组不同曝光。
2. 每个曝光拍两张或多张。
3. 计算图像均值，代表平均信号。
4. 计算帧间差异或方差，代表噪声。
5. 观察方差随均值变化的曲线。

典型现象：

```text
暗部区域：读噪占主导
中间区域：shot noise 占主导，方差随信号近似线性增加
高光区域：接近 full well，开始饱和，曲线不再线性
```

EMVA 1288 标准把这些测量流程规范化，让不同传感器和相机可以更公平地比较。初学者不需要一开始完整实现 EMVA 1288，但要理解它的思想：传感器性能不是靠看一张照片猜，而是通过暗场、平场、曝光序列和统计量测出来。

## 7. SNR：为什么暗部更脏，亮部更干净

SNR 是信号和噪声的比例。一个简化模型可以写成：

```text
signal = N
noise ≈ sqrt(N + dark + read_noise^2)
SNR = signal / noise
```

如果只看 photon shot noise：

```text
N = 100 个电子 -> noise ≈ 10 -> SNR ≈ 10
N = 10000 个电子 -> noise ≈ 100 -> SNR ≈ 100
```

亮部的绝对噪声更大，但相对信号更小，所以看起来更干净。暗部信号小，read noise、dark current 和量化误差都更容易显出来。

这对 ISP 的启发是：

- 暗部降噪更重要，但也更容易抹掉细节。
- 提亮暗部会把噪声一起提上来。
- HDR 和多帧融合本质上是在扩大可用信号范围或改善暗部 SNR。

## 8. Bit Depth 不等于真实动态范围

初学者常误以为：

```text
12-bit RAW = 4096 档 = 动态范围很大
14-bit RAW = 一定比 12-bit RAW 好很多
```

这不一定对。bit depth 只是 ADC 或数据格式能表达多少级，真实可用信息还受噪声和饱和限制。

举例：

```text
如果低 3 bit 基本都是噪声
那么 14-bit 文件里并不是 14 bit 都是有效画面信息
```

所以评价传感器不能只看 bit depth，要同时看：

- full well capacity
- read noise
- dark current
- dynamic range
- SNR curve
- linearity
- black level stability

## 9. Rolling Shutter 与 Global Shutter

### Rolling Shutter

rolling shutter 是逐行曝光或逐行读出。不同图像行对应的时间不同。

优点：

- 结构相对简单。
- 噪声、成本、功耗和像素面积通常更有优势。
- 手机和消费相机常见。

缺点：

- 快速运动会倾斜、弯曲。
- 闪烁光源下可能出现横向亮暗条纹。
- 多摄同步和高速机器视觉场景更麻烦。

### Global Shutter

global shutter 是所有像素在同一时间窗口曝光，然后再读出。

优点：

- 运动形变小。
- 更适合工业、车载、机器人、高速视觉。

缺点：

- 像素结构更复杂。
- 可能牺牲噪声、满阱、面积或成本。

初学者要记住：rolling/global shutter 不是简单“谁更高级”。它们是不同应用下的 tradeoff。

## 10. CFA 与颜色：为什么传感器不是直接输出 RGB

大多数 CMOS 传感器每个像素前面有一个颜色滤光片，常见是 Bayer CFA：

```text
R G
G B
```

这样做的原因是单个像素本身通常只测光强，不能同时完整测 R/G/B 三个颜色。CFA 让不同像素分别测不同颜色，再由 ISP 通过 demosaic 重建完整 RGB。

这会带来几个后果：

- RAW 图像是 mosaic pattern，不是三通道 RGB。
- CFA pattern 识别错误会导致严重色偏。
- 去马赛克会引入伪色、锯齿和细节损失。
- 噪声、坏点和黑电平最好在 Bayer 域就处理好，否则会扩散到 RGB。

## 11. 传感器性能如何影响 ISP 设计

传感器不是 ISP 的上游黑盒，而是决定 ISP 策略的源头。

| 传感器特性 | 对 ISP 的影响 |
|---|---|
| 高 read noise | 暗部降噪压力更大，AE 可能要避免欠曝 |
| 高 dark current | 长曝光和高温场景需要暗场/温度补偿 |
| 明显 column FPN | 前端需要列校正，否则后面会出现条纹 |
| 低 full well | 高光容易饱和，需要 HDR 或保守曝光 |
| rolling shutter 慢 | 运动/闪烁场景需要时序补偿或更快读出 |
| PRNU 明显 | 需要平场校正或 lens shading/gain map |
| CFA 特殊 | demosaic、AWB、CCM 都要适配 |

所以学 ISP 不能绕过传感器。很多“图像问题”的根源，不在后处理，而在传感器测量、读出或标定。

## 12. 最小可验证实验

### 实验 1：读 metadata，建立 RAW 身份档案

找一张 RAW/DNG 文件，记录：

- width / height
- CFA pattern
- bit depth
- black level
- white level
- ISO / analog gain
- exposure time
- camera model

然后回答：

- 哪些字段会影响 BLC？
- 哪些字段会影响 demosaic？
- 哪些字段会影响噪声？
- 哪些字段会影响饱和和动态范围？

### 实验 2：暗场图理解 black level 和 FPN

如果能拍摄，盖上镜头拍一张 dark frame。观察：

- 直方图峰值在哪里？
- 是否有亮点、暗点？
- 是否有横纹或竖纹？
- 提高曝光时间或 ISO 后，暗部统计如何变化？

结论应能区分：

- black level：整体基线
- hot pixel：局部坏点
- column/row FPN：条纹结构
- random noise：每帧随机变化

### 实验 3：平场图理解 PRNU 和 shading

拍一张均匀白墙、积分球或尽量均匀光源。观察：

- 中心和四角亮度是否一致？
- R/G/B 通道是否有不同 shading？
- 同一亮度区域是否有固定纹理？

这能帮助理解 PRNU、lens shading 和后续 LSC 为什么需要标定。

### 实验 4：用两帧估计随机噪声

对同一静态均匀场景连续拍两张 RAW。用两张图相减：

```text
diff = frame1 - frame2
```

固定模式成分会被部分抵消，随机噪声会更明显。这个思想也是很多传感器噪声测量方法的基础。

## 13. 本章自测题

1. RAW 为什么不是照片？
2. black level 和 dark current 是一回事吗？
3. 为什么暗部比亮部更容易显得脏？
4. full well capacity 和 dynamic range 有什么关系？
5. 14-bit RAW 是否一定比 12-bit RAW 有更多有效信息？
6. FPN 和 random noise 的区别是什么？
7. DSNU 和 PRNU 分别应该用 dark frame 还是 flat field 观察？
8. rolling shutter 会造成哪些图像问题？
9. 为什么 CFA pattern 错了会导致颜色错？
10. 为什么传感器性能会影响 ISP 模块顺序和参数？

## 14. 常见误区

- **误区 1：ISO 越高，传感器越“敏感”。**  
  ISO/增益通常放大读出信号，但不会凭空增加真实光子。它可能改善量化或读出链路表现，也可能更快推向饱和。

- **误区 2：暗场扣除能去掉所有暗部噪声。**  
  暗场可以估计固定模式，但暗电流 shot noise 和读噪仍然随机存在。

- **误区 3：bit depth 就是动态范围。**  
  bit depth 是表示精度，动态范围还取决于满阱容量和噪声底。

- **误区 4：FPN 就是坏点。**  
  坏点只是 FPN/缺陷的一种表现。FPN 还可能是列、行、PRNU、DSNU 等结构。

- **误区 5：rolling shutter 只是视频问题。**  
  静态照片里如果物体或相机运动很快，也会出现倾斜、弯曲、条纹或闪烁带。

## 15. 读完本章应该达到的标准

读完本章后，应该能做到：

- 用“水桶模型”解释像素曝光、饱和、读噪和暗电流。
- 说出 CMOS RAW 数值由哪些物理和电子因素组成。
- 区分 photon shot noise、read noise、dark current、FPN、PRNU、DSNU、quantization noise。
- 解释为什么动态范围不等于 ADC bit depth。
- 解释 rolling shutter 和 global shutter 的差异与应用取舍。
- 设计 dark frame、flat field、曝光序列这三类基础传感器观察实验。
- 说明传感器特性如何决定 ISP 前端校正策略。

## 16. 推荐资料与论文

- EMVA 1288：图像传感器和相机表征标准，适合学习 SNR、dynamic range、dark current、saturation capacity、photon transfer 等指标。  
  <https://www.emva.org/standards-technology/emva-1288/>
- EMVA 1288 Release 4.1 文档：适合深入了解标准化测量流程和参数定义。  
  <https://www.ksp.kit.edu/chapters/2556/files/501464d0-18f1-4188-b5f1-85c9422c6826.pdf>
- “High-level numerical simulations of noise in CCD and CMOS photosensors: review and tutorial”：适合学习 CCD/CMOS 噪声建模框架，包括 PRNU、photon shot noise、dark current、FPN、read noise、quantization noise。
- “Noise in a CMOS digital pixel sensor”：可用于理解低照时暗电流 shot noise、亮部 photon shot noise 等不同噪声主导区间。
- “CMOS image sensors: state-of-the-art” 和 “Review of CMOS image sensors”：适合了解 CMOS 传感器从 CCD 竞争到主流技术的演进，以及噪声、功耗、速度、动态范围等问题。
- Basler / Teledyne 关于 rolling shutter 与 global shutter 的工业资料：适合初学者理解两种快门的应用差异和图像伪影。  
  <https://www.baslerweb.com/en-us/learning/cmos-rolling-shutter-cameras/>  
  <https://www.teledynevisionsolutions.com/learn/learning-center/imaging-fundamentals/rolling-vs-global-shutter/>
- “Uniformity Correction of CMOS Image Sensor Modules for Machine Vision Cameras”：适合学习 uniformity correction、FPN、暗电流温度依赖和机器视觉相机标定。
## 学习优先级

- **必须掌握**：本章学习结果、输入输出、关键失败现象和最小验证方法。
- **了解即可**：历史背景、少见硬件变种和暂时无法从公开资料验证的细节。
- **后面再回看**：需要真实 RAW、标定数据或硬件经验才能完整理解的内容。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab01-raw与传感器身份契约.md](../labs/lab01-raw与传感器身份契约.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter02-第2章：CMOS图像传感器原理与技术.md)
- 项目落点：
  - [Stage 1 起点](../../stage1_soft_isp/materials/stage1_start_here.md)
- [RAW 检查脚本](../../stage1_soft_isp/scripts/01_inspect_raw.py)
- [RAW 数据契约](../../stage1_soft_isp/soft_isp/raw_contract.py)
- 原始资料：[原教程正文归档](../source_archive/chapter02-第2章：CMOS图像传感器原理与技术.md)

导航：[上一章](./chapter01-第1章：ISP概述与发展历程.md) · [下一章](./chapter03-第3章：图像传感器与ISP协同设计.md) · [完整课程索引](../full_content_index.md)
