# 第12章：ISP存储架构与数据流


> 课程阶段：硬件架构、HDR、计算摄影与 3A　|　难度：入门 → 中级　|　优先级：核心
>
> 建议用时：3–4 小时阅读 + 2–4 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**计算 line buffer、tile overlap、SRAM bank 和 DDR 带宽。**

## 1. 本章先解决什么问题

第 11 章讲了 ISP 硬件架构的整体思维：流水线、tile、定点、流控、统计和寄存器。第 12 章继续往下钻一个最实际的问题：图像数据到底放在哪里、怎么搬、怎么复用，才能让 ISP 持续实时运行。

很多初学者以为 ISP 的瓶颈主要是“算不动”。真实系统里，瓶颈经常是“数据搬不动”。一张 4K 图有几百万个像素，RAW、RGB、YUV、统计、中间缓存、历史帧、AI 输入输出都可能占用带宽。如果每个模块都把整帧写回 DDR，再由下一个模块读出来，DDR 带宽、功耗和延迟会很快爆掉。

本章最小链路是：

```text
输入：像素流、帧缓存、tile 数据、DMA 描述符、格式/stride/地址参数
处理：line buffer、window buffer、tile buffer、SRAM bank、DDR burst、prefetch、format packing/unpacking
输出：可被下一级实时消费的数据流，或可被 DMA/CPU/AI/编码器读取的帧/块/统计数据
```

读完本章，至少要能回答：

- 为什么 line buffer 能省掉整帧缓存。
- 为什么 tile 处理需要 overlap。
- 为什么中间结果落 DDR 会放大带宽压力。
- 为什么 burst、stride、alignment、bank conflict 会影响吞吐。
- 多路相机、多尺度输出、历史帧会怎样放大存储压力。

## 2. 先算一帧图有多大

存储架构学习的第一步不是看复杂架构图，而是会算数据量。

一帧图像大小大致是：

```text
frame_size = width * height * bits_per_pixel
```

例子 1：4K RAW 12-bit

```text
3840 * 2160 * 12 bit = 99,532,800 bit
约 11.87 MB
```

例子 2：4K RGB 12-bit，每像素 3 通道

```text
3840 * 2160 * 36 bit = 298,598,400 bit
约 35.6 MB
```

例子 3：4K YUV420 8-bit

```text
Y 平面：3840 * 2160 * 8 bit
UV 合计：Y 的一半
总计：3840 * 2160 * 12 bit
约 11.87 MB
```

注意：RAW12 和 YUV420 8-bit 都可能是 12 bit/pixel 的量级，但含义完全不同。RAW12 是单通道传感器采样；YUV420 是显示/编码阶段的亮度加降采样色度。

## 3. 再算带宽：帧大小乘帧率还不够

单纯输入输出带宽：

```text
bandwidth = frame_size * fps
```

以 4K30 为例：

```text
RAW12 输入：11.87 MB * 30 ≈ 356 MB/s
RGB12 中间：35.6 MB * 30 ≈ 1.07 GB/s
YUV420 8-bit 输出：11.87 MB * 30 ≈ 356 MB/s
```

如果只看输入 RAW 和输出 YUV420：

```text
约 356 + 356 = 712 MB/s
```

但如果 pipeline 中间有 3 个模块都把 RGB12 写到 DDR，再由下个模块读回：

```text
一次 RGB12 中间读写：1.07 GB/s 写 + 1.07 GB/s 读 = 2.14 GB/s
三次中间读写：约 6.42 GB/s
总带宽：输入输出 0.71 GB/s + 中间 6.42 GB/s ≈ 7.13 GB/s
```

这说明一个关键事实：中间 buffer 的读写常常比最终输入输出更贵。流式 pipeline、on-chip buffer、tile reuse 的目标，就是尽量避免这种“每个模块都落 DDR”的模式。

## 4. Line Buffer：用几行缓存换掉整帧缓存

很多 ISP 算法只需要局部邻域，例如 3x3、5x5、7x7。流式输入时，line buffer 可以缓存最近几行，让当前像素和前几行组成窗口。

对 `K x K` 窗口：

```text
需要缓存行数 ≈ K - 1
line_buffer_size = (K - 1) * image_width * bits_per_pixel
```

例子：4K 宽度 3840，RAW12，5x5 窗口：

```text
(5 - 1) * 3840 * 12 bit = 184,320 bit ≈ 22.5 KB
```

如果不用 line buffer，而是把整帧 RAW12 放片上：

```text
3840 * 2160 * 12 bit ≈ 11.87 MB
```

22.5 KB 和 11.87 MB 的差距，就是 line buffer 的意义。SmartHLS、AMD/Vitis Vision、很多 FPGA 图像处理资料都会强调 line buffer 对 stencil/window 图像处理的重要性：它让流式图像处理不必把整帧都存在片上。

## 5. Window Buffer 和 Shift Register：line buffer 还不够

line buffer 解决“前几行在哪里”的问题，但 `3x3` 或 `5x5` 窗口还需要每行相邻的几个像素。通常会配合 shift register 形成滑动窗口。

一个简化 3x3 数据结构：

```text
line buffer 2 -> shift registers -> top row pixels
line buffer 1 -> shift registers -> middle row pixels
current input -> shift registers -> bottom row pixels
```

每来一个新像素：

1. 当前行 shift register 左移。
2. line buffer 输出对应列的历史像素。
3. 各行窗口同步更新。
4. 中心像素位置的 3x3 邻域送给算法。

初学者要注意：窗口输出会有启动延迟。图像最开始几行、每行最左几列，没有完整邻域，必须做边界策略，例如 replicate、mirror、zero padding 或直接不输出边缘有效像素。

## 6. Tile Processing：把整帧问题变成局部块问题

当算法需要较大邻域、多次访问或复杂处理时，只用 line buffer 可能不够。这时常把图像切成 tile。

基本思路：

```text
整帧 -> DMA 读一个 tile 到片上 SRAM -> tile 内处理 -> DMA 写回 -> 下一个 tile
```

tile 好处：

- 片上只放当前 tile，不放整帧。
- 数据局部性强，tile 内可重复访问。
- 适合复杂降噪、局部 tone mapping、AI 前处理、畸变校正等。
- 多个处理单元可以并行处理不同 tile。

tile 难点：

- 边界需要 overlap。
- DMA 地址生成更复杂。
- tile 太小，overlap 和调度开销大。
- tile 太大，片上 SRAM 不够。
- tile 拼接不当会出现块边界。

## 7. Overlap 怎么算

如果一个滤波器半径是 `r`，那么 tile 每边至少需要额外读 `r` 个像素，才能让 tile 内有效区域的边界像素有完整邻域。

例如 5x5 滤波：

```text
kernel size = 5
radius = (5 - 1) / 2 = 2
```

如果有效 tile 是 128x128，实际读取至少：

```text
(128 + 2*2) x (128 + 2*2) = 132 x 132
```

如果两个滤波级联，一个 5x5、一个 7x7，半径分别是 2 和 3，最保守估算总 overlap：

```text
2 + 3 = 5
实际读取：(128 + 10) x (128 + 10) = 138 x 138
```

真实系统可能通过重排算法、合并处理、共享中间结果来减少 overlap。但初学者先掌握原则：tile 的有效区域越小、算法半径越大，overlap 开销越明显。

## 8. Ping-Pong Buffer：让搬数据和算数据并行

tile 处理如果按顺序做：

```text
读 tile0 -> 算 tile0 -> 写 tile0 -> 读 tile1 -> 算 tile1 -> 写 tile1
```

DMA 和计算单元会互相等待。Ping-pong buffer 用两个 buffer 交替工作：

```text
buffer A 正在被计算单元处理
buffer B 正在被 DMA 读入下一块
下一轮交换 A/B
```

理想情况下：

```text
总时间 ≈ max(DMA 时间, 计算时间)
```

而不是：

```text
总时间 ≈ DMA 时间 + 计算时间
```

但 ping-pong buffer 会增加片上 SRAM 需求，也需要更复杂的状态机、地址管理和同步。若 DMA 和计算时间严重不平衡，仍会有一方等待。

## 9. SRAM Bank：并行访问和冲突

片上 SRAM 通常会分成多个 bank，以支持并行读写。问题是：如果同一周期多个访问落到同一个 bank，就会发生 bank conflict。

一个常见 bank 分配：

```text
bank_id = pixel_x mod num_banks
```

例如 4 bank：

```text
Bank0: x = 0,4,8,...
Bank1: x = 1,5,9,...
Bank2: x = 2,6,10,...
Bank3: x = 3,7,11,...
```

如果每时钟处理 4 个连续像素，这种分配可能很好；如果访问模式是跨行、跨列、随机 patch，冲突就可能变多。

SRAM bank 设计要考虑：

- 每周期需要几个读端口和写端口。
- 访问是连续、跨步 stride，还是随机。
- PPC 是 1、2、4、8 还是更高。
- 数据是否需要按通道分 bank。
- bank conflict 时是 stall、复制数据，还是改变布局。

## 10. DDR 访问：burst、stride、alignment

外部 DDR 带宽看起来很大，但不能只看理论峰值。实际吞吐受 burst 长度、地址连续性、读写切换、bank/page 命中、仲裁、QoS、cache 和对齐影响。

AXI burst 的基本思想是：不要每个像素发一次内存请求，而是把连续地址聚合成一段 burst。AMD Vitis HLS 文档中也明确把 burst 描述为提高 DDR load/store 吞吐、降低延迟的重要优化。

好的访问模式：

```text
连续地址
长 burst
对齐到总线宽度
读写分组
stride 简单
```

差的访问模式：

```text
每行很短 burst
大量小块随机读
读写频繁切换
地址未对齐
多路模块同时抢 DDR
```

stride 是每行起始地址之间的距离。它不一定等于 `width * bytes_per_pixel`，因为行可能为了对齐被 padding。格式转换、crop、tile、YUV planar/semi-planar 都会涉及 stride。

如果 stride 配错，典型现象是：

- 图像斜着错位。
- 每行开头或结尾花。
- 色度平面错位。
- 图像只在某些宽度下出错。

## 11. 数据格式、packing 和 alignment

ISP 中常见格式很多：

- RAW10/RAW12 packed。
- RAW16 unpacked。
- RGB888、RGB101010、RGB121212。
- YUV444、YUV422、YUV420。
- NV12、NV21、I420 等 planar/semi-planar 格式。

packed RAW 是常见坑。比如 RAW12 每个像素 12 bit，两个像素 24 bit，可以打包成 3 byte。这样节省带宽，但硬件需要 unpack：

```text
byte0 byte1 byte2 -> pixel0[11:0], pixel1[11:0]
```

如果 unpack 的 bit 顺序、大小端、对齐规则错了，图像会出现周期性条纹、亮度异常或像素值跳变。

YUV420 也常见坑：Y 平面全分辨率，UV 半分辨率；NV12 是 UV 交错，NV21 是 VU 交错。UV 顺序错会导致颜色怪异，stride 错会导致色度错位。

## 12. 多路相机和多尺度输出会放大所有问题

单路 4K30 已经需要认真算带宽，多路相机更麻烦。

假设 4 路 1080p60 RAW12：

```text
单路：1920*1080*60*12 bit ≈ 1.49 Gbit/s ≈ 186 MB/s
四路：约 744 MB/s 仅 RAW 输入
```

如果每路还要输出：

- 主预览 YUV。
- 编码 YUV。
- AI 小图 RGB/NV12。
- 统计数据。
- 历史帧给时域降噪。

带宽和调度压力会继续上升。多路系统还要考虑：

- DMA QoS：哪一路优先级更高。
- 帧同步：多摄时间对齐。
- 内存分区：避免互相抢同一 DDR bank/channel。
- 峰值带宽：多路帧开始或 tile DMA 同时发生时是否拥塞。
- 最坏情况：不能只看平均带宽。

## 13. 数据流设计的一条原则：少落 DDR，多做复用

好的 ISP 数据流通常会尽量做到：

```text
能流式就流式
能 line buffer 就不 frame buffer
能 tile 内复用就不反复读 DDR
能合并模块就减少中间写回
能 burst 连续读写就避免随机小访问
```

但这不是绝对。某些模块必须落 DDR：

- 帧级算法需要整帧。
- 多帧算法需要历史帧。
- AI 加速器需要特定 tensor layout。
- 编码器/显示器需要帧缓存。
- CPU/GPU 后处理需要访问图像。

因此，架构设计不是“完全不用 DDR”，而是清楚每一次 DDR 读写为什么存在，是否有复用机会，是否满足最坏情况带宽。

## 14. 最小可验证实验

实验 1：I/O 带宽和中间带宽。

1. 以 4K30 为例。
2. 输入 RAW12，输出 YUV420 8-bit。
3. 计算只含输入输出的带宽。
4. 再加入 1 次、3 次、5 次 RGB12 中间读写。
5. 对比带宽增长。

实验 2：line buffer 大小。

1. 选择 1920 和 3840 两种宽度。
2. 选择 RAW12 和 RGB12 两种格式。
3. 计算 3x3、5x5、7x7 窗口的 line buffer 大小。
4. 对比整帧缓存大小。

实验 3：tile overlap 开销。

1. 有效 tile 设为 64x64、128x128、256x256。
2. 滤波半径设为 2、4、8。
3. 计算实际读取 tile 大小。
4. 计算 overlap 带来的额外像素百分比。

实验 4：burst 和 stride。

1. 假设总线宽度 128-bit。
2. 对 RGB888、RAW12 packed、YUV420 分别设计行 stride。
3. 检查每行是否对齐 16 byte 或 64 byte。
4. 思考未对齐会怎样影响 burst。

实验 5：多路相机最坏情况。

1. 假设 4 路 1080p60 RAW12。
2. 每路输出一份 YUV420 8-bit。
3. 每路保留 2 帧历史 YUV 用于时域降噪。
4. 估算平均带宽和帧缓存容量。

## 15. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 图像周期性条纹 | RAW packing/unpacking bit 顺序错 | 检查 RAW10/12 打包格式和 endian |
| 每行错位或斜纹 | stride 配置错误 | 检查行 pitch、padding、crop 地址 |
| 色彩平面错位 | YUV UV 地址或 stride 错 | 检查 NV12/NV21/I420 布局 |
| tile 边界明显 | overlap 不足或边界融合错误 | 计算算法半径，检查 tile 有效区 |
| 随机掉帧 | DDR 峰值带宽不足或 QoS 不稳 | 看 DMA 时间线、仲裁和最坏情况 |
| pipeline 偶发停顿 | 下游 buffer 不够或 backpressure 传递 | 看 ready/valid 和 FIFO 深度 |
| 某些分辨率才出错 | 对齐、burst、stride 与宽度相关 | 测试奇数宽度、非 16/64 对齐宽度 |
| 多路相机互相影响 | DDR/NoC 争用 | 分析每路带宽、优先级、峰值时刻 |
| 功耗过高 | 中间帧反复落 DDR | 合并模块，增加片上复用 |

## 16. 常见误区

- 误区 1：DDR 标称带宽够就一定没问题。实际有效带宽受 burst、对齐、读写切换和仲裁影响。
- 误区 2：只算输入输出带宽就够。中间 buffer 读写经常才是大头。
- 误区 3：tile 越小越省。tile 小会让 overlap 和 DMA 调度开销变大。
- 误区 4：line buffer 可以无限加。片上 SRAM 面积和功耗都很贵，多模块重复 line buffer 会堆资源。
- 误区 5：packed 格式只是省空间。它会增加 unpack/pack 控制复杂度和对齐风险。
- 误区 6：平均带宽过了就安全。实时系统还要看峰值带宽和最坏情况延迟。
- 误区 7：格式转换只是矩阵。实际还涉及 planar/interleaved、stride、alignment、range 和 chroma subsampling。

## 17. 学习优先级

必须掌握：

- RAW/RGB/YUV 单帧大小和带宽计算。
- line buffer 公式和窗口大小关系。
- tile overlap 的原因和基本计算。
- DDR burst、stride、alignment 的直觉。
- packed/unpacked、planar/semi-planar 格式差异。
- 中间 buffer 读写对带宽的放大作用。

了解即可：

- SRAM bank 分配和 bank conflict。
- ping-pong buffer、prefetch、DMA descriptor。
- 多路相机 QoS、NoC/DDR 仲裁。
- HBM、multi-channel DDR、cache coherence。

后面再回看：

- 图像处理编译器如何自动生成 line buffer 和最小缓存。
- 复杂 AI-ISP 中 tensor layout 与 ISP image layout 的转换。
- 多摄、HDR、多帧降噪中的帧缓存生命周期管理。

## 18. 自测题

1. 4K30 RAW12 输入一秒大约多少 MB？
2. 4K30 RGB12 中间帧读写一次大约消耗多少 GB/s？
3. 5x5 窗口处理 3840 宽 RAW12，需要多少 line buffer？
4. 为什么 tile 处理需要 overlap？
5. tile 太小和太大分别有什么问题？
6. 为什么 burst 连续访问比零散小访问更适合 DDR？
7. RAW12 packed 为什么容易出周期性条纹？
8. NV12 和 NV21 弄错会出现什么现象？
9. 多路相机系统为什么不能只看平均带宽？
10. 如果某个图像宽度下正常，换一个宽度就错位，你会优先检查什么？

## 19. 读完本章的验收标准

合格的学习结果应该是：

- 口头解释：能讲清 ISP 存储架构是在解决数据复用、带宽和实时稳定性问题。
- 计算能力：能估算单帧大小、输入输出带宽、中间读写带宽、line buffer 大小和 tile overlap。
- 架构判断：能说明什么时候用 streaming、line buffer、tile、frame buffer、DDR。
- 格式意识：能区分 RAW packed、RGB、YUV420、NV12/NV21、stride 和 alignment。
- 排查能力：能根据条纹、错行、色度错位、掉帧、tile 边界提出合理原因。
- 工程判断：能说明为什么“少落 DDR、多做片上复用”是 ISP 数据流设计的重要原则。

## 20. 推荐资料与进一步阅读

- [High-Throughput Line Buffer Microarchitecture for Streaming Image Processing](https://pmc.ncbi.nlm.nih.gov/articles/PMC8320917/)：讲 line buffer 和 streaming stencil 图像处理的硬件组织。
- [AMD Vitis HLS: AXI Burst Transfers](https://docs.amd.com/r/2022.1-English/ug1399-vitis-hls/AXI-Burst-Transfers)：理解 AXI burst 为什么能提升 DDR 访问吞吐。
- [AMD AXI4-Stream Video IP: Line Buffer Placement](https://docs.amd.com/r/en-US/ug934_axi_videoIP/Line-Buffer-Placement)：理解视频流系统中 line buffer 放置和 backpressure 的工程影响。
- [SmartHLS Optimization Guide: Line Buffer](https://microchiptech.github.io/fpga-hls-docs/2021.1.2/optimizationguide.html)：用简单 stencil 示例解释 line buffer 如何减少整帧存储。
- [AMD Vitis Vision Library](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vitis/vitis-libraries/vitis-vision.html)：参考硬件视觉库中图像数据流、memory 和 streaming 接口组织。
- [ImaGen: Memory- and Power-Efficient Image Processing Accelerators](https://arxiv.org/abs/2304.03352)：了解自动生成低存储、低功耗图像处理加速器的研究方向。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab06-硬件数据流与定点.md](../labs/lab06-硬件数据流与定点.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter12-第12章：ISP存储架构与数据流.md)
- 项目落点：
  - [Stage 3 C++ ISP](../../stage3_cpp_isp/README.md)
- [Pipeline benchmark](../../stage3_cpp_isp/benchmarks/bench_pipeline.cpp)
- [测试向量清单](../../stage3_cpp_isp/data/test_vectors_manifest.csv)
- 原始资料：[原教程正文归档](../source_archive/chapter12-第12章：ISP存储架构与数据流.md)

导航：[上一章](./chapter11-第11章：ISP硬件架构基础.md) · [下一章](./chapter13-第13章：ISP时序与功耗优化.md) · [完整课程索引](../full_content_index.md)
