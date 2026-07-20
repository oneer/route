# 第3章：图像传感器与ISP协同设计


> 课程阶段：传统 ISP 与成像基础　|　难度：入门　|　优先级：核心
>
> 建议用时：2–3 小时阅读 + 1–2 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**根据 CFA、sensor mode、metadata 和接口约束定义 ISP 输入契约。**

## 1. 本章先解决“传感器和 ISP 为什么必须一起设计”

第 2 章讲的是 CMOS 传感器本身如何把光变成 RAW 数字值。第 3 章要再往系统层走一步：传感器不是孤立地吐出一张图片，ISP 也不是孤立地处理一个数组。它们之间是一套协同协议：

```text
传感器决定：测什么、怎么采样、什么时候曝光、怎样读出、输出什么格式
ISP 决定：如何解释这些数据、如何校正、如何重建颜色、如何反馈曝光/增益/白平衡控制
```

如果传感器输出方式变了，ISP 的假设也必须跟着变。例如：

- CFA 从 RGGB 变成 BGGR，demosaic 和 AWB 的颜色解释就要变。
- sensor mode 从全分辨率变成 binning，噪声、分辨率、视场、标定表都可能变。
- HDR mode 从单曝光变成 staggered multi-exposure，ISP 就要知道哪些行/帧属于长曝光，哪些属于短曝光。
- rolling shutter 读出时间变了，多摄同步和运动伪影也会变。
- 曝光/增益控制有 1-2 帧延迟，3A 算法就不能假设参数马上生效。

所以“传感器与 ISP 协同设计”的本质不是多加几个接口，而是让 ISP 正确理解传感器数据的来源、格式、时序和控制反馈。

## 2. 先把协同链路画出来

一个真实相机系统里，传感器和 ISP 之间至少有三条链路：

```text
1. 像素数据链路：
   Sensor RAW pixels -> MIPI CSI-2 / parallel / SerDes -> ISP input

2. 控制链路：
   ISP/3A decision -> I2C/SPI register write -> sensor exposure/gain/mode

3. 元数据链路：
   sensor mode / exposure / gain / frame id / timestamp / embedded data -> ISP metadata
```

初学者最容易只看到第 1 条：像素来了，ISP 处理。但真正工程里，第 2 条和第 3 条同样重要。如果 ISP 不知道当前帧使用的曝光时间、模拟增益、sensor mode、CFA pattern 和 timestamp，它就无法正确做黑电平、降噪、LSC、AWB、HDR 合成和多摄同步。

## 3. CFA Pattern：颜色采样方式决定 demosaic 怎么做

CFA 是 Color Filter Array，即像素上方的颜色滤光片排列。最经典的是 Bayer：

```text
R G
G B
```

但“Bayer”不是只有一种。常见 2x2 排列有：

```text
RGGB    BGGR    GRBG    GBRG
R G     B G     G R     G B
G B     G R     B G     R G
```

这些排列对人眼看起来只是旋转或平移，但对 ISP 是完全不同的解释方式。如果把 RGGB 当成 BGGR：

- 红蓝通道会互换或严重错位。
- AWB 会基于错误颜色统计做增益。
- CCM 再怎么调也很难完全救回来。
- 最终图像可能整体偏紫、偏绿或肤色异常。

### 初学者要特别注意

CFA pattern 不是“图像内容”，而是传感器采样规则。它必须来自 sensor datasheet、DNG metadata、驱动配置或相机栈 metadata，不能靠肉眼猜。

### 变种 CFA 为什么麻烦

除了普通 Bayer，还有 RGBW、RYYB、Quad Bayer/TetraCell/NonaCell 等设计。它们往往为了低照、HDR 或高像素营销牺牲了传统 demosaic 的简单性。

| CFA 类型 | 直觉目的 | 对 ISP 的新要求 |
|---|---|---|
| Bayer RGGB | 标准彩色采样 | 常规 demosaic、AWB、CCM |
| RGBW | 提高进光量 | 从 W 像素中估计颜色，颜色重建更难 |
| RYYB | 增强亮度/低照 | 黄色通道到 RGB 的转换和色彩标定更难 |
| Quad Bayer | 同色 2x2 聚合，兼顾高像素/低照 | remosaic、binning、HDR、特殊 demosaic |
| NonaCell | 3x3 同色聚合 | 高像素模式和低照模式差异更大 |

这也是为什么新传感器接入时，ISP 不能默认“都是 Bayer，套一个通用算法就行”。

## 4. Sensor Mode：同一颗传感器可以像多台相机

传感器通常有很多 mode，例如：

```text
全分辨率拍照模式
4K 视频模式
1080p 高帧率模式
binning 低照模式
crop 局部读取模式
HDR staggered exposure 模式
```

每个 mode 都可能改变：

- 分辨率
- 帧率
- 视场 FOV
- rolling shutter readout time
- pixel binning / skipping 策略
- black level
- noise profile
- lens shading table
- CFA pattern 或有效采样方式
- MIPI data type / bit depth
- embedded metadata 格式

所以 sensor mode 不是单纯的“图像大小”。它会改变 ISP 的输入统计和校正参数。

### Binning 和 Skipping 的区别

| 方式 | 直觉解释 | 优点 | 风险 |
|---|---|---|---|
| Binning | 多个相邻像素合并 | 提高 SNR、低照更好、降分辨率 | 颜色采样变复杂，细节下降 |
| Skipping | 跳过部分像素读取 | 提高帧率、减少带宽 | aliasing、细节损失、噪声不一定改善 |
| Crop | 只读中间或局部区域 | 高帧率、低带宽 | 视场变窄，标定中心可能变化 |
| Scaling | 传感器或 ISP 缩放 | 输出尺寸灵活 | 插值和锐度变化 |

初学者经常把 binning 和 resize 混为一谈。它们不一样。binning 发生在传感器采样/读出阶段，会改变信噪比和 CFA 结构；resize 通常是后处理几何缩放。

## 5. MIPI CSI-2：不只是“传图像的线”

在嵌入式相机里，MIPI CSI-2 是最常见的传感器到处理器接口之一。初学者不需要一开始学习完整协议，但要知道它承载的不只是像素数组。

MIPI CSI-2 可以传：

- RAW8 / RAW10 / RAW12 / RAW14 等不同 bit depth 像素数据
- 不同 data type 的包
- embedded data
- frame start / frame end / line start / line end
- virtual channel
- 多曝光或多流数据

这对 ISP 协同很重要。比如 HDR 传感器可能通过不同 virtual channel 或 embedded metadata 标识不同曝光；多摄系统可能要依赖 frame id、timestamp 和 channel 区分数据来源。

### 初学者需要掌握的 MIPI 相关问题

- 当前 RAW 是几 bit？打包格式是什么？
- 每行 stride 和有效像素宽度是否一致？
- 是否有 embedded metadata 行？
- 是否有多个 virtual channel？
- 帧开始、帧结束是否稳定？
- 带宽是否足够支持目标分辨率和帧率？

## 6. Metadata：ISP 必须知道当前帧的身份

一帧图像不只是像素，还应该有身份信息。典型 metadata 包括：

```text
frame_id
timestamp
sensor_mode
exposure_time
analogue_gain
digital_gain
black_level
white_level
CFA pattern
frame_duration
line_length
temperature
HDR exposure index
embedded statistics
```

没有 metadata，会出现很多难查问题：

- 用错曝光时间做 HDR 合成。
- 用错 gain 做降噪强度估计。
- 用错 sensor mode 的 LSC 表。
- 用错 CFA pattern 做 demosaic。
- 多摄图像时间戳错位，融合失败。

libcamera 文档中专门有 sensor control delay 的概念：曝光、增益、blanking 等控制写入传感器后，可能隔几帧才反映到输出图像。这个细节对 3A 很关键。控制第 N 帧时写入的曝光，不一定作用在第 N 帧，可能是 N+1 或 N+2。

## 7. 3A 是传感器与 ISP 的闭环，不是单独算法

3A 指：

```text
AE / AEC：自动曝光
AWB：自动白平衡
AF：自动对焦
```

它们依赖 ISP 统计，也反过来控制传感器和镜头。

### AE / AEC 闭环

```text
当前帧 RAW/RGB
  -> ISP 统计亮度直方图/分块亮度
  -> AE 算法计算目标曝光
  -> 写 sensor exposure_time / analogue_gain
  -> 若干帧后生效
  -> 新帧再统计
```

AE 的难点不是“让平均亮度等于某个值”，而是要处理：

- 高光不能全爆。
- 暗部不能全黑。
- 人脸/ROI 可能比背景更重要。
- 频闪灯下曝光时间要避开 banding。
- 增益提高会带来噪声。
- 曝光控制有帧延迟，不能来回震荡。

### AWB 闭环

AWB 需要判断“场景里哪些区域应该是中性灰/白”。它依赖传感器颜色响应、CFA、LSC、CCM 和统计区域。用错 sensor mode 或 shading 表，会让 AWB 统计偏掉。

### AF 闭环

AF 不只看 ISP 图像清晰度，还要控制镜头马达或相位对焦像素。不同传感器可能有 PDAF pixel，这会给 ISP/3A 提供额外对焦信息。

## 8. 曝光、增益、帧率之间的约束关系

曝光时间不是想设多长就多长。它受 frame duration 限制：

```text
exposure_time <= frame_duration - readout_margin
```

如果目标是 30 fps：

```text
frame_duration ≈ 33.3 ms
```

曝光时间通常不能超过一帧周期太多，否则帧率会下降或需要特殊长曝光模式。

增益也不是免费的：

- analog gain 通常在 ADC 前放大信号，可能改善暗部可见性，但会更快接近饱和。
- digital gain 是数字域乘法，会把噪声一起放大。
- 高 gain 下 ISP 降噪、锐化、色彩和 tone mapping 都可能需要换参数。

### 一个简单例子

低照场景下 AE 想把图像变亮，有三种选择：

| 方法 | 好处 | 代价 |
|---|---|---|
| 延长曝光 | 收集更多真实光子，SNR 可能更好 | 运动模糊、帧率下降 |
| 提高模拟增益 | 暗部更亮，读出链路更有利 | 高光更易饱和、噪声也明显 |
| 提高数字增益 | 实现简单 | 真实信息不增加，只放大噪声 |

所以 AE 不只是调亮，而是在亮度、噪声、运动模糊、帧率和动态范围之间折中。

## 9. HDR Sensor Mode：多曝光不只是后期合成

HDR 可以在传感器侧就开始协同设计。常见方式包括：

- staggered HDR：同一场景输出长/中/短曝光帧或行。
- interleaved exposure：不同行或像素使用不同曝光。
- dual conversion gain：同一像素用不同转换增益扩大动态范围。
- split pixel / specialized HDR pixel：通过特殊像素结构扩展动态范围。

ISP 必须知道：

- 哪些数据属于长曝光，哪些属于短曝光。
- 不同曝光的时间差是多少。
- 如何对齐运动物体。
- 饱和区域应该从哪一路曝光补。
- 噪声模型如何随曝光和 gain 变化。

如果 metadata 或时序错了，HDR 会出现鬼影、边缘错位、亮度跳变或颜色异常。

## 10. 多摄同步：不仅是同时拍

多摄系统常见于手机多摄、环视、双目、车载和机器人。同步不是简单“差不多同时拍”，而是要知道每帧准确的曝光时间窗口。

多摄同步至少包括：

- 触发同步：是否同一时刻开始曝光。
- 时间戳同步：每帧 timestamp 是否来自统一时钟。
- 曝光同步：不同相机曝光时间是否一致或可解释。
- 帧率同步：是否有掉帧或不同步。
- ISP 延迟同步：不同 pipeline 输出是否对齐。

对于双目和环视，几毫秒偏差就可能让运动物体位置不一致。对于 HDR 多摄，每路相机的曝光和 tone mapping 不一致也会导致融合边界明显。

## 11. 标定表为什么要按 sensor mode 管理

ISP tuning 里常见标定表包括：

- black level
- lens shading table / ALSC table
- defective pixel table
- noise profile
- AWB statistics prior
- CCM
- gamma/tone curve
- HDR merge parameters

这些表不一定对所有 sensor mode 通用。

例如：

- 全分辨率模式下的 LSC 表，不一定适合 crop 模式。
- binning 模式下噪声模型会变。
- HDR mode 下 black level 和 saturation 行为可能不同。
- IR-cut / NoIR 模式会改变 AWB 和 CCM。

所以协同设计里非常重要的一点是：

```text
sensor mode -> 对应 metadata -> 对应 tuning profile -> 对应 ISP 参数
```

## 12. 新传感器 Bring-up 检查表

接入一颗新传感器时，可以按下面顺序排查。

### 12.1 基础通信

- I2C/SPI 是否能读写 sensor 寄存器？
- sensor ID 是否正确？
- reset、power rail、clock 是否正确？
- MIPI lane 数、速率、极性是否匹配？

### 12.2 像素格式

- RAW bit depth 是 RAW8/10/12/14？
- MIPI packing 是否正确解包？
- width、height、stride 是否正确？
- 是否有 embedded data line？
- black level / white level 是否已知？

### 12.3 CFA 和图像方向

- CFA pattern 是 RGGB/BGGR/GRBG/GBRG 还是特殊 CFA？
- 是否有 mirror/flip？
- mirror/flip 后 CFA 是否也要变？
- demosaic 后颜色是否正常？

### 12.4 时序与控制

- exposure control 单位是 line 还是 microsecond？
- analogue gain register 如何换算成倍率？
- exposure/gain 生效延迟是多少帧？
- frame duration、line length、vblank/hblank 如何影响帧率？

### 12.5 标定与 tuning

- 暗场是否稳定？
- 平场是否有明显 shading？
- 坏点表是否需要生成？
- 不同 mode 是否需要不同 LSC/noise profile/CCM？
- 3A 是否稳定收敛？

## 13. 最小可验证实验

### 实验 1：CFA 错配实验

拿一张 Bayer RAW，分别按 RGGB、BGGR、GRBG、GBRG 做 demosaic。观察：

- 哪个颜色最自然？
- 哪些结果红蓝互换？
- 哪些结果整体偏绿或偏紫？
- AWB 能不能完全救回错误 CFA？

结论：CFA 是 ISP 正确解释 RAW 的第一前提。

### 实验 2：sensor mode 对比表

找一个真实传感器 datasheet 或相机日志，列出至少两个 mode：

| mode | 分辨率 | 帧率 | bit depth | binning/crop | 预期用途 | 可能需要变化的 ISP 参数 |
|---|---|---|---|---|---|---|

重点不是填全，而是理解“mode 改变不只是尺寸改变”。

### 实验 3：曝光/增益延迟思考实验

假设 AE 在第 N 帧发现图像太暗，写入更长曝光，但传感器控制延迟是 2 帧。回答：

- 第 N+1 帧是否已经变亮？
- 如果 AE 不知道延迟，会不会连续过度调节？
- 怎样避免曝光震荡？

### 实验 4：HDR metadata 检查

设计一个 HDR 帧 metadata 表：

| frame_id | exposure_type | exposure_time | analogue_gain | timestamp |
|---|---|---|---|---|

说明如果 exposure_type 标错，HDR merge 会发生什么。

## 14. 初学者常见误区

- **误区 1：ISP 只需要像素数据。**  
  错。ISP 还需要 sensor mode、曝光、增益、CFA、timestamp、black level、tuning profile 等 metadata。

- **误区 2：换分辨率就是 resize。**  
  错。sensor mode 可能涉及 binning、skipping、crop、读出时序和噪声模型变化。

- **误区 3：CFA 错了可以靠 AWB/CCM 修回来。**  
  通常不行。CFA 是采样解释错误，后续颜色模块只能有限补救。

- **误区 4：曝光和增益写寄存器后立刻生效。**  
  很多传感器有帧延迟。3A 必须知道这个延迟。

- **误区 5：多摄只要帧率一样就同步。**  
  不够。还要统一触发、时间戳、曝光窗口和 pipeline 延迟。

## 15. 读完本章应该达到的标准

读完本章后，应该能做到：

- 解释传感器和 ISP 为什么不是简单上下游，而是闭环协同系统。
- 说清 CFA、sensor mode、MIPI、metadata、3A、HDR、多摄同步各自影响 ISP 的哪个环节。
- 设计一个新 sensor bring-up 检查表。
- 判断 binning、skipping、crop、scaling 的区别。
- 解释曝光、增益、帧率和控制延迟之间的关系。
- 说明为什么不同 sensor mode 可能需要不同 tuning profile。

## 16. 推荐资料与论文

- MIPI CSI-2 官方介绍：适合了解嵌入式相机最常用传输接口、virtual channel、多数据类型和多曝光/多流支持。  
  <https://www.mipi.org/specifications/csi-2>
- libcamera Sensor Driver Requirements：适合学习 exposure、analogue gain、sensor control 和驱动需要提供哪些信息。  
  <https://libcamera.org/sensor_driver_requirements.html>
- libcamera SensorDelays：适合理解曝光、增益、blanking 等控制写入后可能隔几帧才生效。  
  <https://www.libcamera.org/internal-api-html/structlibcamera_1_1CameraSensorProperties_1_1SensorDelays.html>
- Raspberry Pi Camera Algorithm and Tuning Guide：适合学习真实相机栈中 AGC/AEC、AWB、ALSC、CCM、denoise 和 tuning profile 如何组织。  
  <https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf>
- Merging-ISP: Multi-Exposure High Dynamic Range Image Signal Processing：适合学习多曝光 RAW CFA HDR 合成为什么需要和 ISP pipeline 一起考虑。  
  <https://arxiv.org/abs/1911.04762>
- Beyond Joint Demosaicking and Denoising: An Image Processing Pipeline for a Pixel-bin Image Sensor：适合了解 pixel binning / 非标准 CFA 会如何改变 ISP pipeline。  
  <https://arxiv.org/abs/2104.09398>
## 补充自测题

1. 用一句话说明本章对象的输入、处理和输出。
2. 哪一个参数或前置假设最容易设置错误？错误图像现象是什么？
3. 设计一个最小实验，说明如何区分算法问题、输入契约问题和标定问题。
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
- 自测答案与评分：[本章答案要点](../answer_keys/chapter03-第3章：图像传感器与ISP协同设计.md)
- 项目落点：
  - [Stage 1 起点](../../stage1_soft_isp/materials/stage1_start_here.md)
- [RAW 检查脚本](../../stage1_soft_isp/scripts/01_inspect_raw.py)
- [RAW 数据契约](../../stage1_soft_isp/soft_isp/raw_contract.py)
- 原始资料：[原教程正文归档](../source_archive/chapter03-第3章：图像传感器与ISP协同设计.md)

导航：[上一章](./chapter02-第2章：CMOS图像传感器原理与技术.md) · [下一章](./chapter04-第4章：ISP前端处理：原始数据校正.md) · [完整课程索引](../full_content_index.md)
