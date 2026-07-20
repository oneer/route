# 第11章：ISP硬件架构基础


> 课程阶段：硬件架构、HDR、计算摄影与 3A　|　难度：入门 → 中级　|　优先级：核心
>
> 建议用时：3–4 小时阅读 + 2–4 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**用像素率、带宽、位宽、缓存和流控约束描述硬件 ISP。**

## 1. 本章先解决什么问题

前面章节一直在讲 ISP 算法：BLC、LSC、BPC、demosaic、denoise、AWB、CCM 等。第 11 章开始换一个视角：这些算法如果要在真实相机里实时运行，硬件到底要怎么组织。

软件里处理一张图，常常可以把整张图读进内存，然后一行一行、一块一块慢慢算。硬件 ISP 更像一条传送带：传感器不断送来像素，模块必须按时接住、按时处理、按时送给下一级。它不能随便暂停很久，也不能每个像素都去外部 DDR 随机读一大堆邻域数据。

本章最小链路是：

```text
输入：来自传感器或上一级模块的像素流、行/帧同步、配置寄存器参数
处理：流水线模块、line buffer/window、定点乘加、流控、统计、DMA/寄存器配置
输出：满足吞吐、延迟、位宽和协议要求的像素流与统计结果
```

读完本章，至少要能回答：

- 为什么硬件 ISP 更偏向 streaming pipeline。
- 为什么 3x3/5x5 算法需要 line buffer。
- 如何估算像素率、带宽、最低时钟和并行度。
- 为什么定点位宽会影响画质、面积和功耗。
- ready/valid、寄存器配置、影子寄存器解决什么工程问题。

## 2. 软件算法和硬件 ISP 的思维差异

很多初学者第一次看 ISP 硬件会卡住，因为他们脑子里还是软件模型。

软件模型常常是：

```text
读入整张图 -> for y -> for x -> 访问任意邻域 -> 写回整张图
```

硬件流式模型更像：

```text
每个时钟来 1 个或多个像素 -> 模块边接收边计算 -> 固定延迟后输出 -> 下一级继续处理
```

这两种模型的差异很大：

| 维度 | 软件 frame-based | 硬件 streaming |
|---|---|---|
| 数据访问 | 可随机访问整帧 | 主要按像素流顺序访问 |
| 存储 | 外部内存相对充足 | 片上 SRAM/寄存器昂贵 |
| 时间 | 可变耗时较常见 | 必须满足实时吞吐 |
| 数据类型 | 浮点容易使用 | 定点更常见 |
| 控制 | 分支和循环灵活 | 控制逻辑要可综合、可时序收敛 |
| 调试 | 可断点、可打印 | 需要波形、断言、golden model |

硬件设计不是把 C/Python 算法逐行翻译成 RTL，而是重新组织数据流和计算结构。算法能不能流式化、需要几行缓存、每像素多少乘加、是否有帧级依赖，都会直接决定架构。

## 3. 先会算像素率

硬件 ISP 的第一件事是算吞吐。像素率大致是：

```text
pixel_rate = width * height * fps
```

例子 1：1080p30

```text
1920 * 1080 * 30 = 62,208,000 pixel/s
约 62.2 Mpixel/s
```

例子 2：4K30

```text
3840 * 2160 * 30 = 248,832,000 pixel/s
约 248.8 Mpixel/s
```

例子 3：4K60

```text
3840 * 2160 * 60 = 497,664,000 pixel/s
约 497.7 Mpixel/s
```

如果一个硬件模块每个时钟处理 1 个像素，那么 4K60 至少需要接近 500 MHz 的像素处理吞吐，这对很多 FPGA/ASIC 模块都很紧张。工程上可能会用：

```text
提高时钟频率
每时钟处理多个像素 PPC, pixels per clock
多 pipeline 并行
降低分辨率或帧率
把复杂算法改成 tile/offline/AI 加速器处理
```

例如 4K60，如果使用 2 pixels/clock：

```text
required_clock ≈ 497.7 / 2 = 248.9 MHz
```

如果使用 4 pixels/clock：

```text
required_clock ≈ 124.4 MHz
```

所以硬件架构讨论里，频率、并行度和像素率永远要一起看。

## 4. 再会算带宽

像素率只告诉你每秒多少像素，带宽还要乘以每个像素多少 bit、读写几次。

假设 4K60、RAW 12-bit、单路输入：

```text
497.7 Mpixel/s * 12 bit ≈ 5.97 Gbit/s ≈ 746 MB/s
```

如果转成 RGB 12-bit，每像素 3 通道：

```text
497.7 Mpixel/s * 36 bit ≈ 17.9 Gbit/s ≈ 2.24 GB/s
```

如果某个算法每帧要从 DDR 读一遍 RGB，再写一遍 RGB：

```text
读 2.24 GB/s + 写 2.24 GB/s ≈ 4.48 GB/s
```

如果还要多次读邻域、历史帧、临时 buffer，带宽会更高。片上流式 pipeline 的价值就在这里：如果模块之间直接传流，很多中间结果不必落 DDR，可以显著减少外部带宽和功耗。

## 5. 流水线架构：最典型的 ISP 形态

流水线架构把 ISP 拆成一串模块：

```text
Sensor -> BLC -> BPC -> LSC -> Denoise -> Demosaic -> AWB/CCM -> Gamma -> YUV/Output
```

每个模块只做自己的事，输入像素流，输出像素流。理想情况下，流水线填满之后，每个时钟都能输出一个或多个像素。

流水线的关键指标：

- 吞吐 throughput：单位时间能处理多少像素。
- 延迟 latency：一个像素从输入到输出要经过多少周期/多少行/多少帧。
- 启动填充时间：line buffer 和 pipeline 第一次填满前不能输出完整结果。
- 最慢级：整个 pipeline 的吞吐受最慢模块限制。
- 气泡 bubble：某级停顿会让有效数据不连续，影响后级。

一个小例子：

```text
BLC 延迟 2 cycle
BPC 延迟 20 cycle，因为需要窗口和判断
Demosaic 延迟 40 cycle
CCM 延迟 5 cycle

总像素级 pipeline 延迟约 67 cycle
但只要每级都能 1 pixel/cycle，吞吐仍然可以是 1 pixel/cycle
```

这就是硬件里“延迟”和“吞吐”要分开理解的原因。一个模块可以延迟很深，但只要流水线排满，每周期仍能持续输出。

## 6. Line Buffer：邻域算法的基本工具

许多 ISP 算法需要邻域窗口，例如：

- BPC：看 3x3、5x5 或 7x7 邻域。
- Demosaic：看周围同色采样。
- Denoise：看局部窗口。
- Sharpen/edge：看梯度窗口。

流式输入时，当前像素到来时，下一行像素还没来，上一行像素已经过去了。要形成 3x3 窗口，就必须缓存前面的行。

对窗口大小 `K x K`，通常至少需要：

```text
line_buffer 行数 = K - 1
```

例子：

```text
3x3 窗口 -> 需要缓存 2 行
5x5 窗口 -> 需要缓存 4 行
7x7 窗口 -> 需要缓存 6 行
```

如果图像宽度 3840、RAW 12-bit、5x5 窗口：

```text
line buffer bits = 4 * 3840 * 12 = 184,320 bit
约 22.5 KB
```

如果是 RGB 12-bit、5x5：

```text
4 * 3840 * 36 = 552,960 bit
约 67.5 KB
```

这只是一个模块的 line buffer。多个模块各自缓存，片上 SRAM 会迅速增加。所以硬件架构要尽量复用缓存、合并模块或谨慎选择窗口大小。

## 7. Tile/块处理：适合复杂算法，但边界麻烦

有些算法很难纯流式处理，例如复杂降噪、HDR 合成、局部 tone mapping、多帧融合、AI 模块。它们可能需要较大邻域、随机访问、历史帧或多次迭代。这时会把图像切成 tile：

```text
整帧图像 -> 切成 64x64 或 128x128 tile -> 每个 tile 放入片上 SRAM -> 局部处理 -> 拼回整帧
```

tile 的好处：

- 局部数据放片上，减少 DDR 往返。
- 复杂算法可以在 tile 内多次访问。
- 多个 tile 可以并行处理。

tile 的问题：

- 边界 artifact：滤波窗口跨 tile 边缘时信息不完整。
- overlap 开销：需要多读一些重叠区域。
- 控制复杂：地址生成、tile 顺序、DMA、同步都更复杂。
- 延迟增加：要等 tile 数据准备好才能处理。

如果滤波半径是 `r`，tile 通常需要至少 `r` 像素重叠：

```text
有效 tile：64x64
滤波半径：3
实际读取：70x70
```

tile 架构不是比流水线高级，而是适合不同类型算法。传统前端像素级处理多用流水线；复杂局部/多帧/AI 算法更可能用 tile 或外部加速器。

## 8. 定点位宽：画质和硬件成本的折中

硬件 ISP 很少全程用浮点。常见做法是定点数：

```text
Qm.n：m 位整数，n 位小数
```

定点化要解决三个问题：

1. 范围够不够：会不会溢出。
2. 精度够不够：小数位会不会太少。
3. 成本能不能接受：位宽越大，寄存器、SRAM、乘法器、功耗越高。

例子：12-bit RAW 做 LSC，边缘增益可能到 2.5 倍：

```text
输入最大值：4095
乘以 2.5：10237.5
至少需要 14 bit 才能表示到 16383
```

如果中间仍用 12-bit，边缘亮部会 clipping，画面可能出现高光断层或颜色异常。

CCM 也类似。3x3 矩阵可能有负系数，乘加中间结果可能超出输入范围。所以中间位宽要扩展，最后再根据输出格式做 rounding、clamp、saturation。

一个基本原则：

```text
内部位宽通常大于输入/输出位宽。
每次乘法、累加、增益、矩阵都要重新估算最大范围。
最后输出前才做受控裁剪和舍入。
```

## 9. Saturation、Clipping 和 Rounding 不能随便

定点 ISP 中常见三类处理：

- truncation：直接丢低位。
- rounding：四舍五入或带偏置舍入。
- saturation/clipping：超出范围时压到最大/最小。

直接截断会引入系统性偏差，暗部和渐变容易出现量化纹理。矩阵后不做合理 saturation，可能出现负值绕回或溢出。不同模块如果各自随意裁剪，会让高光、饱和色和肤色都变得不可控。

例子：

```text
12-bit 输出范围：0..4095
某矩阵结果：-50 -> 应 clamp 到 0，而不是无符号绕回成大值
某矩阵结果：4600 -> 应 clamp 到 4095，或在 tone/压缩前保留更高位宽
```

硬件验证时，必须让 RTL 与软件 golden model 的 rounding、clipping、saturation 完全一致，否则逐像素对比会出现大量 1 LSB 或边界差异。

## 10. Ready/Valid 流控：模块之间怎么握手

很多 FPGA/SoC 视频流接口使用 ready/valid 类握手，例如 AXI4-Stream。基本含义是：

```text
valid：发送方说“我这拍有有效数据”
ready：接收方说“我这拍能接收数据”
当 valid && ready 同时为 1，数据传输发生
```

视频流还常带：

- data：像素数据。
- tuser/sof：帧开始。
- tlast/eol：行结束。
- keep/strb：字节有效信息。

这个机制解决的问题是：下游暂时忙时，可以通过 ready 拉低让上游停住。但在高速 ISP pipeline 中，频繁 backpressure 会带来时序和缓存压力。AMD AXI4-Stream Video IP 设计资料也强调，视频处理核遇到行/帧边界、padding 或 pipeline 清空时可能会影响 READY/VALID 行为。

初学者要注意：

- valid 不能在没有数据时乱拉高。
- ready 拉低时，发送方必须保持数据稳定。
- 行结束、帧开始标记必须和像素对齐。
- pipeline register、FIFO、skid buffer 常用于改善时序和吸收短暂停顿。
- 流控错误会造成丢像素、重复像素、行错位、帧撕裂。

## 11. 统计模块：3A 不是普通图像输出

ISP 不只输出图像，还要输出统计信息给 AE、AWB、AF 等控制算法。

常见统计包括：

- AE：亮度直方图、分区平均亮度、过曝/欠曝统计。
- AWB：R/G/B 均值、灰点候选、色温相关统计。
- AF：高频能量、对比度、边缘强度。
- Flicker：亮度随时间的周期性变化。

统计模块有两个特点：

1. 它们通常在像素流经过时同步累加，不能等整帧结束再慢慢扫。
2. 它们的结果通常在帧结束后给控制算法，用于下一帧或后续几帧参数。

这带来一个闭环延迟：

```text
第 N 帧统计 -> CPU/控制器计算参数 -> 第 N+1 或 N+2 帧生效
```

如果参数更新不同步，会出现曝光跳变、白平衡闪烁、帧内参数不一致等问题。

## 12. 配置寄存器和影子寄存器

ISP 有大量可配置参数：黑电平、LSC gain map、BPC 阈值、denoise 强度、AWB gain、CCM、gamma LUT、crop、格式、输出尺寸等。

如果 CPU 在一帧中间直接改正在使用的寄存器，可能出现：

```text
上半帧用旧 CCM，下半帧用新 CCM
一行中间 AWB gain 改变
LSC 表更新到一半被模块读取
```

所以硬件常用影子寄存器机制：

```text
CPU 写 shadow registers
帧边界或安全时刻 copy 到 active registers
active registers 供像素 pipeline 使用
```

这样可以保证一整帧使用一致参数。对于大表，例如 LSC grid、gamma LUT、坏点表，可能还需要双 buffer 和版本号，避免读写冲突。

## 13. 最小可验证实验

实验 1：像素率和时钟估算。

1. 计算 1080p30、4K30、4K60 的 pixel/s。
2. 假设模块每时钟 1 pixel、2 pixel、4 pixel，分别估算最低 clock。
3. 加入 20% blanking/协议开销余量，再看时钟是否合理。

实验 2：line buffer 估算。

1. 选择 3x3、5x5、7x7 三个窗口。
2. 假设图像宽度 1920 和 3840，输入位宽 12-bit RAW。
3. 计算每个窗口需要多少行缓存和多少 bit。
4. 再把 RAW 改成 RGB 12-bit，比较缓存增长。

实验 3：定点位宽估算。

1. 假设 12-bit RAW 输入。
2. LSC 最大增益设为 2.5。
3. 计算中间结果至少需要多少整数位。
4. 再考虑小数位，例如 gain 用 Q2.10，估计乘法输出位宽。

实验 4：ready/valid 时序。

1. 画一个上游模块和下游模块。
2. 设计 5 个 cycle 的 valid、ready、data 波形。
3. 模拟 ready 拉低时 data 是否保持。
4. 标出哪些周期真正发生传输。

实验 5：影子寄存器。

1. 假设一帧 4 行，每行 8 像素。
2. 在第 2 行中间写入新的 AWB gain。
3. 对比“立即生效”和“下一帧生效”两种策略。
4. 观察帧内颜色不一致如何产生。

## 14. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 行错位或花屏 | ready/valid、tlast、sof 对齐错误 | 看波形，检查每行像素计数 |
| 帧撕裂 | 帧同步或寄存器更新时机错误 | 检查 shadow register 和帧边界 |
| 图像边缘异常 | line buffer 边界处理不对 | 检查 padding、mirror、replicate 策略 |
| 高光断层 | 中间位宽不足或过早 clipping | 做位宽范围分析 |
| 暗部有条纹 | truncation 偏差、定点精度不足 | 改 rounding，增加小数位 |
| pipeline 偶发停顿 | backpressure 没被吸收 | 加 FIFO/skid buffer，检查最慢级 |
| tile 边界明显 | overlap 不够或融合不平滑 | 增大重叠，改边界混合 |
| 统计不稳定 | 统计窗口、饱和排除、帧延迟处理错误 | 检查 3A 统计时序 |
| 软件和 RTL 差 1 LSB 很多 | rounding/clipping 不一致 | 对齐 golden model 量化规则 |

## 15. 常见误区

- 误区 1：算法能跑通软件，就一定能实时硬件化。吞吐、带宽、缓存、位宽可能完全不允许。
- 误区 2：频率越高越好。高频会增加时序收敛和功耗压力，PPC 并行有时更合适。
- 误区 3：内部位宽等于输入位宽就够。增益、矩阵、累加都会扩大范围。
- 误区 4：line buffer 是小事。高分辨率、多通道、大窗口下片上 SRAM 会成为主要成本。
- 误区 5：ready/valid 只是连线。流控错误会直接造成丢像素和帧同步错误。
- 误区 6：寄存器写了马上生效最简单。帧中更新会导致一帧内部参数不一致。
- 误区 7：tile 没有副作用。边界、overlap、DMA 和延迟都要认真处理。

## 16. 学习优先级

必须掌握：

- streaming pipeline 与 frame/tile 处理的区别。
- pixel rate、带宽、clock、PPC 的估算。
- line buffer 与窗口大小的关系。
- 定点位宽、rounding、clipping、saturation。
- ready/valid 流控和行/帧同步。
- 配置寄存器、影子寄存器和帧边界更新。

了解即可：

- AXI4-Stream Video、AXI4-Lite、AXI DMA 的接口细节。
- 多级缓存、tile DMA、双 buffer。
- HLS pragma、RTL module boundary、FPGA BRAM/DSP/LUT 资源。
- 统计模块的具体 AE/AWB/AF 控制算法。

后面再回看：

- 可重构 ISP、multi-rate pipeline、CGRA/SIMD ISP 架构。
- 复杂时序收敛、clock domain crossing、low-power clock gating。
- AI ISP 加速器与传统 ISP pipeline 的数据交互。

## 17. 自测题

1. 4K60 的像素率是多少？若每时钟处理 2 个像素，最低时钟大约是多少？
2. 5x5 窗口在流式输入中至少需要缓存几行？
3. 为什么 pipeline 延迟增加不一定降低吞吐？
4. 12-bit 输入乘以 2.5 倍 LSC gain 后，中间至少需要多少 bit 表示整数范围？
5. ready 和 valid 同时为 1 表示什么？
6. ready 拉低时，上游 data 应该怎样？
7. 为什么 AWB/CCM 参数最好在帧边界更新？
8. tile 处理为什么需要 overlap？
9. 软件 golden model 和 RTL 对比时，为什么 rounding 规则必须一致？
10. 如果输出图每行少一个像素，你会优先检查哪些信号？

## 18. 读完本章的验收标准

合格的学习结果应该是：

- 口头解释：能讲清 ISP 硬件为什么偏向流式流水线。
- 计算能力：能估算分辨率、帧率、像素率、带宽、PPC 和 line buffer 大小。
- 位宽判断：能对增益、矩阵、累加做基本动态范围分析。
- 流控理解：能画出 valid/ready 传输发生的周期。
- 架构判断：能说明流水线、tile、混合架构各自适合什么算法。
- 验证意识：能说出 golden model、波形、帧同步、寄存器更新和统计结果如何检查。

## 19. 推荐资料与进一步阅读

- [AMD AXI4-Stream Video IP and System Design Guide](https://www.amd.com/content/dam/amd/en/documents/products/adaptive-socs-and-fpgas/technologies/axi4-stream-video-ip-and-system-design-guide.pdf)：理解视频流 ready/valid、行帧同步和 AXI4-Stream 视频系统。
- [AMD Vitis Vision Library ISP Pipeline](https://xilinx.github.io/Vitis_Libraries/vision/2022.1/overview.html)：参考 HLS/硬件视觉库中 ISP pipeline 和 stream/memory 接口组织方式。
- [Infinite-ISP 开源 RTL 项目](https://github.com/10x-Engineers/Infinite-ISP)：可观察真实 ISP RTL 模块划分、寄存器和 pipeline 组织。
- [Rigel: Flexible Multi-Rate Image Processing Hardware](https://graphics.stanford.edu/papers/rigel/)：理解 stencil/image pipeline 在硬件中如何做多速率和最小缓存。
- [ReconfigISP: Reconfigurable Camera Image Processing Pipeline](https://arxiv.org/abs/2109.04760)：了解可重构 ISP 架构和任务相关 pipeline 设计。
- [Raspberry Pi Camera Algorithm and Tuning Guide](https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf)：从相机算法和调参角度理解 ISP 模块、统计和参数配置。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab06-硬件数据流与定点.md](../labs/lab06-硬件数据流与定点.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter11-第11章：ISP硬件架构基础.md)
- 项目落点：
  - [Stage 3 C++ ISP](../../stage3_cpp_isp/README.md)
- [Pipeline benchmark](../../stage3_cpp_isp/benchmarks/bench_pipeline.cpp)
- [测试向量清单](../../stage3_cpp_isp/data/test_vectors_manifest.csv)
- 原始资料：[原教程正文归档](../source_archive/chapter11-第11章：ISP硬件架构基础.md)

导航：[上一章](./chapter10-第10章：色彩科学与ISP色彩处理.md) · [下一章](./chapter12-第12章：ISP存储架构与数据流.md) · [完整课程索引](../full_content_index.md)
