# 第21章：主流车载ISP方案分析


> 课程阶段：产业平台与应用场景（选修）　|　难度：中级/选修　|　优先级：选修/按方向
>
> 建议用时：2–3 小时阅读 + 1–2 小时证据分析　|　内容整理：2026-07-19

> **证据提醒**：本章涉及厂商、产品或趋势。正文中的参数必须结合资料日期阅读；公开事实、厂商宣传、第三方分析和合理推断不能混为一类。

本章学习结果：**依据任务、接口、生态、安全和证据质量完成车载平台初步选型。**

## 1. 本章先解决什么问题

上一章讲的是车载 ISP 的共性需求：功能安全、实时性、多摄同步、HDR/LFM、温度和环视。本章进一步问：如果真的要做一个车载视觉系统，应该选择哪类平台？TI、Mobileye、NVIDIA、Qualcomm、Ambarella、Renesas、AMD/Xilinx 这些方案差异在哪里？

初学者容易犯的错误是把“方案分析”做成参数排名。车载平台不能只按 TOPS、相机路数、最高分辨率排序，因为真实选型还要考虑：

```text
目标功能：AEB、LKA、APA、环视、DMS、L2/L2+/L3/L4
相机规格：路数、分辨率、帧率、HDR/LFM、GMSL/FPD-Link/MIPI
实时性：端到端延迟、最坏情况、同步精度
安全：ASIL 目标、诊断覆盖、safety island、锁步核
生态：SDK、工具链、标定工具、量产经验、Tier1 支持
功耗：散热空间、长期运行、车规温度
算法开放度：自研算法空间 vs turnkey 感知栈
成本：芯片、外设、PCB、开发人力、认证成本
```

读完本章，至少要能回答：

- 为什么 TI、Mobileye、NVIDIA 不是同一种路线。
- 为什么“可编程灵活”与“低功耗确定性”经常互相拉扯。
- 为什么平台选型要按目标车型和 ADAS 等级来定。
- 为什么工具链和量产生态会影响真实开发速度。
- 为什么车载 ISP 方案不能只看宣传参数。

## 2. 先把主流路线分成几类

主流车载 ISP/视觉平台大致可以按架构理念分成几类：

| 路线 | 代表 | 核心优势 | 典型代价 |
|---|---|---|---|
| 专用视觉预处理 SoC | TI Jacinto/TDA4 VPAC | 确定性、低功耗、车规友好、模块清晰 | 灵活性低于 GPU/FPGA |
| 垂直整合 ADAS 芯片 | Mobileye EyeQ | 感知栈成熟、量产经验强、功耗效率高 | 算法和 pipeline 开放度有限 |
| 高算力异构平台 | NVIDIA DRIVE | GPU/DLA/PVA/ISP 生态强，适合复杂 AI | 功耗、成本、系统复杂度高 |
| 移动 SoC 迁移到汽车 | Qualcomm Snapdragon Ride | ISP/NPU/移动影像经验、开放可扩展 | 车载安全和长期生态需平台化验证 |
| 低功耗 AI 视觉 SoC | Ambarella CV 系列 | 视频/ISP/AI 融合、功耗效率好 | 生态和通用开发资源不同于 NVIDIA |
| 车规 ADAS SoC | Renesas R-Car | 车载接口、安全、Tier1 生态 | AI/软件生态需结合具体平台 |
| 可重构 FPGA/Adaptive SoC | AMD/Xilinx | 接口灵活、低延迟、可定制、传感器适配强 | 开发门槛高、成本和验证复杂 |

这张表不是排名，而是告诉你：不同平台是不同工具箱。

## 3. 平台选型的第一步：定义任务

不要先问“哪个芯片强”，先问“我要做什么系统”。

例 1：低成本前视 ADAS。

```text
功能：AEB、FCW、LKA、TSR
相机：1 路或 2 路前视，2MP/8MP
重点：低功耗、低成本、ASIL、量产稳定
适合路线：Mobileye EyeQ Lite 类、TI/Renesas/Qualcomm entry ADAS 类
```

例 2：泊车环视和 APA。

```text
功能：360 环视、自动泊车、低速障碍物
相机：4 路鱼眼
重点：LDC、拼接、几何标定、低延迟显示
适合路线：TI VPAC/LDC、Renesas R-Car、Qualcomm/Ride、FPGA companion
```

例 3：L2+/L3 多传感器融合。

```text
功能：高速 NOA、城市辅助、BEV 感知
相机：多路 8MP + radar/lidar
重点：AI 算力、同步、fusion、软件栈、功能安全
适合路线：NVIDIA DRIVE、Qualcomm Ride、Mobileye EyeQ6H、Ambarella CV3、Renesas R-Car V4H
```

例 4：特殊传感器或定制相机。

```text
功能：LWIR 夜视、特殊工业相机、非标准接口
重点：接口适配、低延迟、自定义 pipeline
适合路线：AMD/Xilinx FPGA/Adaptive SoC、companion ISP
```

## 4. TI VPAC：清晰的车载视觉预处理路线

TI Jacinto/TDA4 的 VPAC 可以看作“车载视觉前处理加速器”。官方资料中，VPAC/VISS/LDC/MSC 等模块用于 camera capture、ISP、lens distortion correction、多尺度缩放等任务。它的学习价值在于：它把车载前处理拆得很清楚。

典型链路：

```text
RAW camera
-> VISS：BLC、DPC、LSC、demosaic、color、statistics
-> LDC：鱼眼/畸变校正、remap
-> MSC：多尺度输出给显示或 AI
-> perception / display / recorder
```

TI 路线的优势：

- 模块边界清楚，适合理解车载 ISP 工程。
- LDC/MSC 很适合环视、鱼眼和 AI 多尺度输入。
- 功耗和实时性更容易控制。
- 车规接口、文档、SDK、EVM、tuning 资料相对完整。

风险或限制：

- 如果需要大量自定义 AI 图像增强，灵活性不如 GPU/NPU 大平台。
- 性能上限要结合具体 TDA4 型号和相机路数计算。
- 开发者需要理解 TI 的 OpenVX、TIOVX、Vision Apps 等工具链。

适合把 TI 当作“车载 ISP 模块化教材”来学：VISS 负责 ISP，LDC 负责几何，MSC 负责多尺度，DMA/Graph 负责调度。

## 5. Mobileye EyeQ：感知优先和垂直整合

Mobileye 的 EyeQ 系列不是单纯卖 ISP，而是卖长期积累的 ADAS/感知系统能力。Mobileye 官方 EyeQ6 资料提到 EyeQ6H 内置 dedicated ISP、GPU 和 video encoder；EyeQ6 Lite 面向核心 ADAS，强调效率和大规模升级。

Mobileye 路线可以概括为：

```text
camera sensor
-> EyeQ ISP / pre-processing
-> Mobileye perception stack
-> ADAS functions / SuperVision / Surround ADAS
```

优势：

- 长期量产经验强，ADAS 算法和安全功能成熟。
- 垂直整合让 ISP 输出可以直接服务自家感知模型。
- 功耗效率和成本适合大规模前装。
- 对 AEB、LKA、TSR 等功能有成熟产品化路径。

代价：

- 开放度通常不如通用 GPU/SoC 平台。
- OEM 自定义底层 ISP/感知 pipeline 的空间有限。
- 学术或自研团队想深改算法时，约束较多。

学习 Mobileye 时要抓住“感知优先”：它不是为了输出最好看的图，而是为了让自家视觉算法稳定工作。

## 6. NVIDIA DRIVE：高算力异构和可编程生态

NVIDIA DRIVE 的特点是强异构计算：ISP、GPU、DLA、PVA、CPU、DriveWorks、CUDA、TensorRT、仿真和训练生态。NVIDIA DriveWorks 文档明确提到 DRIVE 平台上 ISP 是硬件组件，底层通过 NvMedia/IP Pipeline 使用；PVA 文档说明 PVA 可以与 CPU、GPU 和其他加速器异步并发，作为异构计算 pipeline 的一部分。

简化理解：

```text
camera
-> hardware ISP / NvMedia / SIPL
-> PVA 做 remap/resize/preprocess
-> GPU/DLA 做 perception inference
-> DriveWorks / DRIVE AV 做融合、规划、验证
```

优势：

- GPU/DLA 算力强，适合复杂多传感器 AI。
- CUDA/TensorRT/DriveWorks/仿真生态完整。
- 适合 L2+/L3/L4、robotaxi、研发平台和高端域控。
- PVA 可用于视觉预处理，减轻 GPU 压力。

代价：

- 功耗和散热要求高。
- 成本和系统复杂度高。
- 软件栈强大但学习曲线陡。
- 车规安全、实时性和资源隔离需要系统级设计。

NVIDIA 路线的关键词是“灵活和高算力”，但车载量产时不能只看峰值 AI 性能，还要看安全分区、延迟、功耗和验证链路。

## 7. Qualcomm Snapdragon Ride：开放可扩展和移动经验迁移

Qualcomm 的优势来自移动 SoC：ISP、NPU/DSP、GPU、视频、低功耗和生态经验。Snapdragon Ride Vision System 官方资料强调 open and scalable，从 NCAP 前视相机到更高等级自动驾驶的前视/环视方案，并提到 functional safety/SOTIF support。Snapdragon Ride SDK 资料也提到 Automotive Imaging Systems Camera SDK 支持 ISP processing functions such as image scaling and color conversion。

路线特点：

```text
Snapdragon Ride SoC
-> camera / ISP / imaging SDK
-> AI Engine / CV algorithms
-> scalable ADAS / automated driving stack
```

优势：

- 移动影像和低功耗 SoC 经验强。
- 可扩展，从入门 ADAS 到高阶平台。
- 开放度相对 Mobileye 更高，适合 OEM/Tier1 定制。
- 与座舱、连接、数字底盘生态有协同潜力。

风险：

- 车载量产需要长期安全、工具链和 Tier1 支持。
- 同一平台的最终效果依赖 OEM 和供应商集成能力。
- 如果座舱和 ADAS 融合，安全隔离和实时性要设计清楚。

学习 Qualcomm 时，可以和 Apple/手机 ISP 对比：它把移动端 ISP/NPU 经验扩展到汽车，但汽车对安全和长期运行提出了新约束。

## 8. Ambarella：低功耗视频/AI/ISP 融合路线

Ambarella 长期强项是低功耗视频处理和计算机视觉 SoC。官方 automotive 页面提到其平台面向电子后视镜、多通道记录、ADAS、自动泊车等；CV3-AD 资料强调 AI domain controller SoC 支持 multi-sensor perception、fusion 和 path planning，并提到 on-chip ISP 增强。

路线特点：

```text
多路 camera / radar
-> on-chip ISP + video encode
-> CVflow / AI engine
-> perception / fusion / planning
```

优势：

- 视频编码、低功耗图像处理和 AI 结合紧密。
- 适合多通道记录、电子后视镜、ADAS camera、低功耗域控。
- 人眼显示和机器感知都在产品定位中。

风险：

- 开发者生态和通用深度学习工具链与 NVIDIA 路线不同。
- 自研算法团队需要评估 SDK、模型部署和调试工具。
- 方案竞争力要结合具体车厂/Tier1 支持和量产项目。

Ambarella 的学习重点是“低功耗视觉 SoC 如何把 ISP、视频编码和 AI 结合起来”。

## 9. Renesas R-Car：车载接口、安全和单芯片 ADAS

Renesas R-Car 系列在汽车电子中有深厚生态。R-Car V4H 官方资料写明它面向 L2+/L3 自动驾驶，支持 up to 34 TOPS，并集成 Image Signal Processor，支持 machine vision and human vision parallel processing；还支持 LiDAR、radar、thermal camera 等。

路线特点：

```text
车载多接口
-> ISP 并行支持 machine vision / human vision
-> AI/CV IP
-> 安全 MCU / lockstep cores / automotive interfaces
```

优势：

- 汽车供应链、接口和功能安全生态强。
- 强调机器视觉和人眼显示并行处理。
- 适合 L2+/L3、泊车、环视、NCAP 等量产系统。

风险：

- AI 软件生态和开发体验要结合具体 SDK 与合作伙伴。
- 不同 R-Car 型号能力差异大，选型需精确匹配需求。

Renesas 适合从“传统汽车电子平台如何向 AI/ISP 融合演进”的角度学习。

## 10. AMD/Xilinx：可重构和特殊相机接口路线

AMD/Xilinx 的 FPGA / Adaptive SoC 路线与固定 SoC 不同。Vitis Vision Library 官方资料说明它提供面向 FPGA 和 AI Engine 优化的 computer vision / image processing 函数，并包含 ISP Stats、ISP all_in_one_adas pipeline 等内容。AMD automotive night vision camera brief 还强调 XA FPGA 支持 LWIR night vision camera、MIPI/LVDS、ISO 26262 ASIL-B 等。

路线特点：

```text
custom sensor interface
-> FPGA fabric ISP / remap / filter / scaler
-> AI Engine / programmable logic
-> ADAS / industrial / night vision
```

优势：

- 接口灵活，适合非标准 sensor、LWIR、特殊同步和专用 pipeline。
- 延迟确定性强，可以做硬件级定制。
- Vitis Vision / HLS 降低部分开发门槛。
- 可用于量产前原型验证或特殊场景产品。

代价：

- FPGA/HLS 开发难度高。
- 功耗、成本、资源利用需要硬件团队深度优化。
- 功能安全和验证证据需要额外投入。
- 不适合只想快速使用成熟 turn-key 感知栈的团队。

一句话：FPGA 路线适合“标准芯片不够灵活”的场景，但需要更强工程能力。

## 11. 方案对比的关键 tradeoff

常见取舍：

| 取舍 | 偏左适合 | 偏右适合 |
|---|---|---|
| 固定功能 vs 可编程 | 低功耗、确定性、量产 | 快速迭代、自研算法、复杂 AI |
| Turn-key 感知栈 vs 开放平台 | 快速量产、成熟 ADAS | 差异化算法、自主可控 |
| 单芯片集成 vs 多芯片组合 | 成本、功耗、体积 | 扩展性、特殊功能、高算力 |
| 人眼显示优先 vs 机器视觉优先 | 电子后视镜、环视显示 | AEB、BEV、目标检测 |
| 高算力 vs 低功耗 | L3/L4、高端域控 | 入门 ADAS、DMS、记录仪 |
| 标准接口 vs 特殊接口 | 主流 camera module | LWIR、特殊传感器、实验平台 |

没有绝对最优平台，只有最适合需求、团队和量产约束的平台。

## 12. 如何做一张厂商架构卡片

每个平台都用同一模板整理：

```text
平台名称：
目标应用：前视 ADAS / 环视 / L2+ / L3 / robotaxi / DMS
相机输入：路数、分辨率、帧率、HDR/LFM、接口
ISP 能力：RAW pipeline、LDC、multi-scaler、statistics、multi-output
AI/CV：NPU/GPU/DLA/PVA/APU、TOPS、模型工具链
安全：ASIL 目标、锁步核、ECC、BIST、诊断
实时性：端到端延迟、最坏情况、调度方式
生态：SDK、参考设计、EVM、Tier1/OEM 项目
优点：
限制：
适合场景：
不适合场景：
证据来源：
```

这个模板比“谁 TOPS 高”更接近工程判断。

## 13. 最小可验证实验

实验 1：6 路 8MP ADAS 选型。

1. 假设需求：6 路 8MP@30fps，HDR/LFM，ASIL-B，低功耗，L2+。
2. 分别评估 TI、NVIDIA、Qualcomm、Ambarella、Renesas、FPGA 路线。
3. 写出每条路线的优点、风险和需要进一步确认的问题。
4. 不允许只用 TOPS 做结论。

实验 2：环视系统选型。

1. 假设 4 路鱼眼 2MP@30fps，要求低延迟鸟瞰图。
2. 比较 TI VPAC/LDC、Renesas R-Car、Qualcomm、FPGA companion。
3. 重点看 LDC、标定、拼接、display latency 和 SDK。
4. 写出最小验证 demo 需要哪些输入和输出。

实验 3：平台开放度比较。

1. 选 Mobileye、NVIDIA、Qualcomm 三个平台。
2. 查公开资料：能否自研 perception？能否访问 ISP 参数？是否提供 SDK？
3. 评估“快速量产”和“算法差异化”的取舍。
4. 写出适合哪类车厂或 Tier1。

实验 4：给人看和给机器看的双输出。

1. 假设电子后视镜和目标检测共用同一路相机。
2. 设计 display pipeline 和 perception pipeline。
3. 判断哪些模块共享，哪些模块分开。
4. 比较 Renesas/Arm Mali-C720AE/TI/NVIDIA 这类双路径思想。

实验 5：特殊传感器方案。

1. 假设要接 LWIR 夜视相机或非标准高速相机。
2. 分析固定 SoC、companion ISP、FPGA 的接口和延迟风险。
3. 判断为什么 AMD/Xilinx 路线在特殊接口上有吸引力。
4. 列出验证项：接口、温度、ASIL、延迟、图像质量。

## 14. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 方案 demo 很好但量产困难 | 工具链、标定、功能安全证据不足 | 看 SDK、reference design、ASIL 文档、Tier1 支持 |
| GPU 平台延迟不稳定 | 资源竞争、调度和 DDR 带宽波动 | 分析 worst-case latency 和 queue |
| 低功耗平台 AI 功能不够 | 算力和模型工具链限制 | 看模型部署、量化、帧率和精度 |
| Mobileye 类方案难以差异化 | 垂直栈开放度有限 | 明确可调参数和 OEM 自研空间 |
| FPGA 原型效果好但成本高 | 资源、功耗、开发和验证成本 | 做 BOM、功耗、ASIL 和开发人力评估 |
| 环视拼接不稳 | LDC/标定/同步不足 | 检查 VPAC/LDC/IMR、timestamp、外参 |
| AI 输入和显示输出冲突 | 单一路径同时服务人眼和机器 | 拆 display/perception 双 pipeline |
| 车规认证周期失控 | 安全文档和流程准备不足 | 提前做 ISO 26262、ASPICE、ASIL gap analysis |
| 高 TOPS 未转化为效果 | ISP、memory、SDK 或模型瓶颈 | Profile 全链路，不只看 NPU |
| 平台切换成本巨大 | Camera HAL、标定、模型和工具链绑定 | 做迁移风险清单 |

## 15. 常见误区

- 误区 1：TOPS 最高的平台就是最适合。车载还要看 ISP、接口、延迟、功耗、安全和生态。
- 误区 2：Mobileye 不开放就不好。对很多量产 ADAS 来说，成熟闭环反而是优势。
- 误区 3：NVIDIA 灵活，所以一定适合所有车。高算力平台也带来成本、功耗和系统复杂度。
- 误区 4：FPGA 可重构，所以最保险。可重构意味着更高开发和验证负担。
- 误区 5：TI/Renesas 这类平台不够“AI”就不重要。大量车载任务首先需要稳定预处理、接口和低功耗。
- 误区 6：ISP 方案只影响图像质量。它还影响算法输入、延迟、安全诊断和整车架构。
- 误区 7：有 ASIL 认证就万事大吉。系统级安全目标仍要做分解、集成和验证。

## 16. 学习优先级

必须掌握：

- TI、Mobileye、NVIDIA、Qualcomm、Ambarella、Renesas、AMD/Xilinx 的路线差异。
- 固定功能、GPU、NPU/DLA/PVA、FPGA/Adaptive SoC 的优缺点。
- 平台选型必须从功能需求、相机规格、安全等级和量产约束出发。
- 工具链、SDK、Tier1 支持、标定和安全文档会影响真实落地速度。
- display pipeline 和 perception pipeline 可能需要分开。

了解即可：

- 各平台具体芯片型号和详细性能表。
- PVA、DLA、CVflow、R-Car ISP、VPAC 寄存器细节。
- OpenVX、CUDA、TensorRT、DriveWorks、Vitis HLS 的完整开发流程。
- 不同 Tier1 的参考方案和量产项目。

后面再回看：

- 域控制器集中化趋势。
- 软件定义汽车中 ISP 与 ADAS/座舱融合。
- 车载 perception model 对 ISP tuning 的反馈。
- ASIL-D 感知链路和 SOTIF 场景库验证。

## 17. 自测题

1. 为什么车载 ISP 平台不能只按 TOPS 排名？
2. TI VPAC/VISS/LDC 的学习价值是什么？
3. Mobileye EyeQ 的垂直整合有什么优势和限制？
4. NVIDIA DRIVE 为什么适合高算力自动驾驶研发和高阶平台？
5. Qualcomm Snapdragon Ride 的开放可扩展路线适合什么场景？
6. Ambarella 的低功耗视频/AI/ISP 融合路线有什么特点？
7. Renesas R-Car 为什么强调 machine vision 和 human vision 并行？
8. AMD/Xilinx FPGA 路线适合哪些特殊需求？
9. 如果一个平台支持 ASIL-B IP，为什么系统仍然要做安全分析？
10. 给 4 路环视系统选平台时，哪些指标比 AI TOPS 更重要？

## 18. 读完本章的验收标准

合格的学习结果应该是：

- 能用同一张架构卡片模板比较不同车载 ISP/ADAS 平台。
- 能说明每类平台的核心优势、代价和适合场景。
- 能根据 1 路前视、4 路环视、6/8 路 L2+、特殊夜视相机等需求做初步选型。
- 能解释为什么工具链、标定、安全文档和生态比单项参数更重要。
- 能根据延迟不稳、量产困难、AI 效果不达标、环视错位等现象提出排查方向。

## 19. 推荐资料与进一步阅读

- [TI：Jacinto 7 Camera Capture and Imaging Subsystem](https://www.ti.com/lit/an/spracx9/spracx9.pdf)：理解 VPAC、VISS、LDC、MSC 等车载视觉预处理模块。
- [TI：TDA4VM VPAC ISP Tuning Overview](https://www.ti.com/lit/an/spracu7a/spracu7a.pdf)：了解 TI 车载 ISP tuning 和工具链。
- [Mobileye：Meet EyeQ6](https://ir.mobileye.com/news-releases/news-release-details/meet-eyeqr6-our-most-advanced-driver-assistance-chips-yet/)：官方说明 EyeQ6 Lite/High、dedicated ISP、GPU、video encoder 等方向。
- [Mobileye：EyeQ6 Lite Launch](https://ir.mobileye.com/news-releases/news-release-details/mobileye-eyeq6-lite-launches-speed-adas-upgrades-worldwide)：理解核心 ADAS 的效率和量产路线。
- [NVIDIA DriveWorks ISP Documentation](https://docs.nvidia.com/drive/driveworks-4.0/isp_mainsection.html)：了解 NVIDIA DRIVE 平台 ISP 接口和使用方式。
- [NVIDIA PVA Documentation](https://developer.nvidia.com/docs/drive/drive-os/6.0.7/public/drive-os-linux-sdk/common/topics/pva/ProgrammableVisionAccelerator20.html)：理解 PVA 在异构视觉 pipeline 中的作用。
- [Qualcomm Snapdragon Ride Vision System](https://www.qualcomm.com/news/releases/2022/01/qualcomm-introduces-snapdragon-ride-vision-system-open-and-scalable)：理解开放可扩展 ADAS/AD 视觉平台和 functional safety/SOTIF 支持。
- [Qualcomm Snapdragon Ride SDK](https://www.qualcomm.com/news/onq/2022/01/snapdragon-ride-sdk-premium-solution-developing-customizable-adas-and-autonomous)：了解 Camera SDK 和 ISP processing functions。
- [Ambarella Automotive](https://www.ambarella.com/products/automotive/)：理解低功耗 AI processor、multi-sensor perception、electronic mirror、ADAS 等定位。
- [Renesas R-Car V4H](https://www.renesas.com/products/r-car-v4h)：了解 R-Car V4H 的 ISP、machine/human vision parallel processing、34 TOPS 和 L2+/L3 应用。
- [AMD Vitis Vision Library](https://docs.amd.com/r/en-US/Vitis_Libraries/vision/index.html)：查看 FPGA/AI Engine 优化的 vision/ISP 函数和 ADAS pipeline。
- [Arm Mali-C720AE Automotive ISP](https://www.arm.com/products/silicon-ip-multimedia/image-signal-processor/mali-c720ae)：理解面向 ADAS 和座舱影像的双 pipeline ISP 思路。
## 可追溯资料入口

- [按章节映射的参考资料](../research_bibliography.md#按章节映射的一手入口)
- [来源、证据等级与时效规范](../SOURCE_POLICY.md)
- 本章涉及的产品参数必须记录型号、版本、发布日期/访问日期和证据等级。

## 本章学习闭环

- 配套实验：[lab08-产业资料证据审计.md](../labs/lab08-产业资料证据审计.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter21-第21章：主流车载ISP方案分析.md)
- 项目落点：
  - [相机系统综合项目](../../camera_system_capstone/README.md)
- [多摄评价](../../camera_system_capstone/scripts/03_run_multicamera_evaluation.py)
- [系统岗位证据矩阵](../../camera_system_capstone/outputs/job_evidence_matrix.csv)
- 原始资料：[原教程正文归档](../source_archive/chapter21-第21章：主流车载ISP方案分析.md)

导航：[上一章](./chapter20-第20章：车载ISP架构基础.md) · [下一章](./chapter22-第22章：车载ISP特殊场景优化.md) · [完整课程索引](../full_content_index.md)
