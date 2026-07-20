# 第1章：ISP概述与发展历程


> 课程阶段：传统 ISP 与成像基础　|　难度：入门　|　优先级：核心
>
> 建议用时：2–3 小时阅读 + 1–2 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**画出从光子到 RAW、RGB/YUV 的完整链路，并解释每个核心模块为什么存在。**

## 1. 本章真正要解决的问题

第 1 章不是某个算法模块的说明书，而是整套 ISP 学习的地图。初学者最容易犯的错误，是把 ISP 理解成“相机里的美颜/滤镜/图像增强”，或者把它理解成一堆彼此独立的图像处理算法。更准确的理解是：

```text
ISP = 把传感器测量值变成可显示、可编码、可分析图像的实时工程系统
```

传感器输出的 RAW 数据还不是照片。它更接近一次物理测量：每个像素记录了某个颜色滤光片下的光强响应，同时混入黑电平、暗电流、读出噪声、坏点、镜头暗角、颜色响应偏差、ADC 量化误差等非理想因素。ISP 的第一任务不是“让图好看”，而是先把这些测量值变得稳定、线性、可解释；然后才进入颜色、动态范围、锐度、风格和显示编码。

所以本章要建立三个总论级认知：

- ISP 是传感器、光学、算法、硬件、调参和验证共同组成的系统。
- 传统 ISP pipeline 的顺序不是随便排的，每一步都在为后续步骤建立假设。
- AI-ISP 和端到端神经 ISP 是重要发展方向，但它们仍然绕不开 RAW、噪声、颜色、动态范围和验证这些基础问题。

## 2. 从光子到图像：先建立完整链路

数字相机成像可以先看成下面这条链：

```text
真实世界光线
  -> 镜头/光学系统
  -> CMOS/CCD 图像传感器
  -> 模拟增益与读出电路
  -> ADC 数字化
  -> RAW Bayer / RAW mosaic
  -> ISP 前端校正
  -> 去马赛克、降噪、白平衡、颜色校正
  -> Gamma / Tone Mapping / 色彩空间转换
  -> RGB / YUV / JPEG / 视频流 / 机器视觉输入
```

这条链路里，越靠前越接近物理测量，越靠后越接近视觉表达或应用需求。初学者读任何 ISP 模块时，都应该先问这 5 个问题：

- 当前数据还是 RAW Bayer 吗，还是已经变成 RGB/YUV？
- 当前数据是线性的吗，还是已经经过 gamma/tone curve？
- 当前像素值的 bit depth 是多少，例如 10-bit、12-bit、14-bit、16-bit？
- 这个模块依赖前面哪个校正已经完成？
- 这个模块做错后，错误会不会在后面被放大？

这 5 个问题比背模块名字更重要。比如黑电平校正如果做错，白平衡会把错误基线放大；坏点如果在去马赛克前不修，后面会扩散成彩色伪影；颜色矩阵如果在线性域假设下设计，却拿 gamma 后图像去套，颜色就会失真。

## 3. RAW 为什么不是照片

RAW 常被误解成“未压缩照片”。更准确地说，RAW 是传感器读出的原始测量数据。它至少有四个特点：

1. **颜色不完整**  
   大多数单传感器相机使用 Bayer CFA。每个像素只测 R/G/B 中的一种颜色，另外两个颜色需要去马赛克估计出来。

2. **黑色不等于 0**  
   传感器没有光照时，读出的数字值通常仍然有偏移，这就是 black level。没有减掉黑电平，后续所有亮度、颜色和噪声判断都会偏。

3. **噪声和物理条件有关**  
   photon shot noise、read noise、dark current、temperature、exposure time、analog gain 都会影响 RAW 的统计特性。EMVA 1288 这类标准的意义，就是把这些物理特性变成可测指标。

4. **还没有标准显示含义**  
   RAW 中的数值不是 sRGB，不应该直接显示。它通常需要白平衡、颜色矩阵、tone mapping 和 gamma/OETF 才能变成常见显示图像。

可以把 RAW 理解成“测量记录”，而不是“最终照片”。ISP 的前半段负责让测量记录更可信，后半段负责把可信测量转成符合人眼、显示、编码或机器视觉需求的图像。

## 4. 传统 ISP Pipeline：每一步为什么存在

一个典型的传统 ISP pipeline 可以这样理解：

```text
RAW 输入
  -> Black Level Correction
  -> Bad Pixel Correction
  -> Lens Shading Correction
  -> RAW Denoise
  -> Demosaic
  -> RGB Denoise / Sharpen
  -> Auto White Balance
  -> Color Correction Matrix
  -> Gamma / Tone Mapping
  -> Color Space Conversion
  -> RGB / YUV 输出
```

这不是唯一顺序，不同厂商和场景会有变化，但它体现了一个核心原则：先修正测量基准，再补全颜色，再做颜色和视觉表达。

| 阶段 | 直觉解释 | 工程关注点 | 做错后的典型现象 |
|---|---|---|---|
| BLC | 找准黑色零点 | black level、暗场、bit depth | 暗部偏灰、色偏、截断 |
| DPC/BPC | 修坏点 | 同色邻域、坏点表、动态阈值 | 彩点、短线、局部伪影 |
| LSC | 修镜头暗角和色偏 | gain map、通道补偿、边缘噪声 | 四角过亮/过暗、边缘噪声放大 |
| Denoise | 分清噪声和细节 | RAW/RGB/YUV 域、空域/时域 | 塑料感、纹理丢失、鬼影 |
| Demosaic | 从 Bayer 补 RGB | 插值、边缘方向、伪色抑制 | 彩色锯齿、伪色、细节糊 |
| AWB | 抵消光源色偏 | 统计区域、灰点检测、gain | 整体偏黄/偏蓝/偏绿 |
| CCM | 转换颜色响应 | 3x3 矩阵、色卡、目标色域 | 肤色不准、饱和色偏移 |
| Gamma/Tone | 适配显示和观感 | 线性/非线性、动态范围压缩 | 对比度异常、亮部/暗部丢失 |
| CSC/YUV | 适配显示/编码 | RGB/YUV、色度采样、范围 | 视频颜色异常、编码前失真 |

初学者学传统 ISP 时，不要一开始就追“最先进算法”。更好的方式是：每个模块先回答输入是什么、输出是什么、模块假设是什么、错误现象是什么。

## 5. ISP 的发展脉络：从确定性 pipeline 到 AI-ISP

从专业书籍和工程资料看，ISP 的演进大致可以分成四个阶段。

### 阶段一：传统数字相机 ISP

早期数字相机 ISP 主要服务于“把 RAW 变成好看的照片”。核心任务是传感器校正、去马赛克、降噪、白平衡、颜色校正、gamma 和 JPEG 输出。Junichi Nakamura 主编的 *Image Sensors and Signal Processing for Digital Still Cameras* 是理解这个阶段的经典系统性资料，它把传感器、光学、色彩、算法、架构和图像质量评价放在同一个成像系统里讨论。

### 阶段二：移动 ISP 与计算摄影

智能手机把 ISP 推向多摄、多帧、HDR、夜景、人像、视频防抖和实时预览。此时 ISP 不再只是单帧 pipeline，而是和 CPU/GPU/DSP/NPU、相机驱动、调参系统和应用体验深度耦合。Raspberry Pi Camera Guide 和 libcamera 这类资料很适合初学者理解真实相机栈：ISP 不仅有图像算法，还有 AGC/AE、AWB、ALSC、CCM、denoise、sharpening 和 tuning files。

### 阶段三：车载、安防和机器视觉 ISP

当 ISP 输出不只是给人看，而是给检测、识别、测距和自动驾驶系统用，目标就变了。车载 ISP 更关心低延迟、多摄同步、HDR、LED flicker mitigation、功能安全和最坏场景稳定性。论文 “Overview and Empirical Analysis of ISP Parameter Tuning for Visual Perception in Autonomous Driving” 也强调，ISP 参数会影响下游视觉感知任务，不能只按主观画质调。

### 阶段四：AI-ISP 与学习型 RAW-to-RGB

DeepISP 这类论文尝试用神经网络学习从 RAW low-light mosaic 到最终图像的映射，把去噪、去马赛克、颜色校正和图像调整联合起来。Ignatov 等人的 “Replacing Mobile Camera ISP with a Single Deep Learning Model” 则进一步展示了用单个深度模型学习手机 RAW 到 DSLR 风格图像的可能性。

但初学者要注意：这些论文展示的是方向，不代表传统 ISP 基础可以跳过。学习型 ISP 仍然要面对真实 RAW 数据、噪声模型、颜色准确性、训练数据、泛化、延迟、功耗和可验证性问题。AI-ISP 更像是在传统成像问题上引入新的函数逼近和优化工具，而不是让物理和工程约束消失。

## 6. ISP 是算法，也是硬件系统

如果只从图像处理角度看 ISP，会漏掉它最重要的工程约束：实时。

相机每秒可能输入几十到上百帧，每帧数百万像素。ISP 不能像离线 Photoshop 一样慢慢处理。硬件 ISP 往往采用 streaming pipeline：像素不断流入，模块逐级处理，line buffer 保存有限邻域，参数由寄存器或 tuning table 控制。这里的核心问题包括：

- 每秒需要处理多少像素？
- 每个模块是否能做到一个或多个 pixel per clock？
- 需要多少 line buffer 或 SRAM？
- 是否需要整帧缓存？
- 中间数据 bit depth 是否会溢出？
- 功耗、面积、延迟是否满足目标平台？

这就是为什么 Vitis Vision、NVIDIA VPI、TI VPAC/VISS、Infinite-ISP 这类工程资料和开源项目很重要。它们能提醒初学者：ISP 不是纸面算法集合，而是受带宽、缓存、时钟、功耗和接口约束的系统。

## 7. 初学者推荐学习路线

建议按 4 轮学习，而不是一次性把所有章节看完。

### 第一轮：建立总图

目标：知道 RAW 为什么不是照片，能画出传统 ISP pipeline。

必会问题：

- 传感器输出和最终 RGB 图像有什么差别？
- 为什么 BLC、DPC、LSC 通常在前端？
- 为什么 demosaic 是 RAW 到 RGB 的关键边界？
- 为什么 AWB、CCM、Gamma 不能混为一谈？

### 第二轮：逐模块建立输入输出

目标：每个模块都能说清：

```text
输入数据 -> 核心处理 -> 输出数据 -> 错误现象
```

例如：

```text
Bayer RAW + black level
  -> 减去黑电平并裁剪
校正后的线性 Bayer RAW
  -> 给坏点、LSC、denoise、demosaic 使用
```

### 第三轮：加入工程约束

目标：理解为什么同一个算法在论文、Python、C++、GPU、RTL 中会有完全不同的实现形态。

要开始关注：

- bit depth
- line buffer
- tile
- DDR bandwidth
- latency
- power
- fixed-point approximation

### 第四轮：看现代方向

目标：理解计算摄影、车载 ISP、视频 ISP、AI-ISP 都是在传统基础上的扩展。

要能判断：

- 哪些模块适合学习型增强？
- 哪些模块需要保持确定性和可解释？
- 怎样验证 AI 输出没有破坏颜色、细节和极端场景稳定性？

## 8. 最小可验证练习

本章不要求写复杂代码，但需要完成三个最小练习。

### 练习 1：画 pipeline

画出一条你理解的最小 ISP pipeline：

```text
RAW -> BLC -> DPC -> LSC -> Denoise -> Demosaic -> AWB -> CCM -> Gamma/Tone -> RGB/YUV
```

要求：

- 每个节点写一句“为什么需要它”。
- 标出哪个节点之前数据还是 Bayer RAW。
- 标出哪个节点之后数据变成 RGB。
- 标出哪个节点适合用图像 crop 观察效果。

### 练习 2：解释 RAW 和 JPEG 的差别

用自己的话写一段 200 字解释：

- RAW 为什么不能直接显示？
- JPEG 为什么已经不是原始测量？
- 为什么 ISP 后的图像更好看，但也更难反推真实光照？

### 练习 3：读一篇 AI-ISP 论文摘要

阅读 DeepISP 或 Replacing Mobile Camera ISP with a Single Deep Learning Model 的摘要，回答：

- 它的输入是什么？
- 它的输出是什么？
- 它试图替代或学习哪些传统 ISP 步骤？
- 它可能面临哪些工程问题，例如数据、延迟、泛化、可解释性？

## 9. 本章常见误区

- **误区 1：ISP 就是图像增强。**  
  更准确地说，ISP 先做测量校正，再做重建和增强。

- **误区 2：RAW 是未压缩照片。**  
  RAW 是带 CFA、噪声、黑电平和传感器响应特性的测量数据。

- **误区 3：传统 ISP 已经过时。**  
  AI-ISP 很重要，但训练数据、噪声模型、颜色、验证和硬件约束仍然依赖传统 ISP 基础。

- **误区 4：画质越好看越正确。**  
  消费摄影、专业相机、车载、安防、机器视觉的目标不同。好看不一定适合检测，准确也不一定讨喜。

- **误区 5：模块顺序可以随便换。**  
  很多模块依赖前序假设。例如黑电平、坏点、LSC 如果放错位置，会让后续模块处理错误数据。

## 10. 读完本章应该达到的标准

读完第 1 章后，不要求你掌握所有算法细节，但应该能做到：

- 用一段话解释 ISP 为什么存在。
- 画出 RAW 到 RGB/YUV 的基本 pipeline。
- 解释 RAW、线性 RGB、sRGB/YUV 的差别。
- 说出传统 ISP、计算摄影、AI-ISP 的关系。
- 知道后续章节大致分成传感器基础、传统模块、硬件架构、应用场景、AI-ISP、验证工程几类。
- 面对一个新 ISP 模块时，能主动问：输入是什么，输出是什么，在哪个域处理，依赖什么前置假设，失败现象是什么。

## 11. 推荐资料与论文

- Junichi Nakamura, *Image Sensors and Signal Processing for Digital Still Cameras*. 适合建立数字相机传感器、ISP、色彩、评价和架构的系统视角。
- EMVA 1288 标准：适合学习传感器噪声、动态范围、SNR、暗电流和测量方法。  
  <https://www.emva.org/standards-technology/emva-1288/>
- Raspberry Pi Camera Algorithm and Tuning Guide：适合从真实工程角度理解 AGC/AE、AWB、ALSC、CCM、denoise、sharpening 和 tuning。  
  <https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf>
- libcamera：适合理解开源相机栈、pipeline handler、IPA 和相机控制。  
  <https://libcamera.org/>
- Infinite-ISP：适合观察 RTL 级 ISP 模块如何划分和连接。  
  <https://github.com/10x-Engineers/Infinite-ISP>
- openISP：适合作为传统 ISP pipeline 学习实现参考。  
  <https://github.com/cruxopen/openISP>
- DeepISP: Toward Learning an End-to-End Image Processing Pipeline：适合理解端到端学习型 ISP 的早期代表工作。  
  <https://arxiv.org/abs/1801.06724>
- Replacing Mobile Camera ISP with a Single Deep Learning Model：适合理解移动 RAW-to-RGB 学习型 ISP 的数据和模型思路。  
  <https://arxiv.org/abs/2002.05509>
- Overview and Empirical Analysis of ISP Parameter Tuning for Visual Perception in Autonomous Driving：适合理解 ISP tuning 对下游机器视觉任务的影响。  
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC8321211/>
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
- 自测答案与评分：[本章答案要点](../answer_keys/chapter01-第1章：ISP概述与发展历程.md)
- 项目落点：
  - [Stage 1 起点](../../stage1_soft_isp/materials/stage1_start_here.md)
- [RAW 检查脚本](../../stage1_soft_isp/scripts/01_inspect_raw.py)
- [RAW 数据契约](../../stage1_soft_isp/soft_isp/raw_contract.py)
- 原始资料：[原教程正文归档](../source_archive/chapter01-第1章：ISP概述与发展历程.md)

导航：[课程首页](../README.md) · [下一章](./chapter02-第2章：CMOS图像传感器原理与技术.md) · [完整课程索引](../full_content_index.md)
