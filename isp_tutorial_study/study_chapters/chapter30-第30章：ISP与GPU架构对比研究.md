# 第30章：ISP与GPU架构对比研究


> 课程阶段：AI-ISP 与异构架构　|　难度：中级 → 进阶　|　优先级：选修/按方向
>
> 建议用时：3–4 小时阅读 + 2–4 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**比较 ISP 流水线、GPU SIMT、NPU 和异构调度的适用边界。**

## 1. 本章先建立直觉：ISP 是专用流水线，GPU 是通用并行机器

ISP 和 GPU 都在处理大量像素，但它们的设计哲学完全不同。ISP 更像一条为相机 RAW 数据定制的专用流水线：传感器像素一行一行进来，经过黑电平、坏点、镜头阴影、去马赛克、降噪、颜色、tone mapping 等固定阶段，尽量少访问外部内存，以稳定、低延迟、低功耗的方式持续输出图像。GPU 更像一台可编程并行机器：它可以运行 shader、CUDA/OpenCL/Metal/Vulkan compute，适合复杂、变化快、可迭代的图像和视觉算法，但调度、缓存、内存搬运和同步成本更高。

本章的目标不是判断“ISP 好还是 GPU 好”，而是建立架构选择能力：

- 固定、流式、逐像素、低功耗的任务通常更适合 ISP。
- 复杂、可变、全局依赖、研究迭代快的任务通常更适合 GPU 或 NPU。
- GPU 峰值算力高，不代表相机 pipeline 一定快。
- ISP 不灵活，不代表它落后；它的能效和确定性正是优势。
- 实际产品常用混合架构：ISP 做基础成像，GPU/NPU 做计算摄影、后处理、AI 和可变算法。

## 2. 输入、处理、输出：两者面对的数据形态不同

ISP 的典型链路：

```text
输入：
传感器 RAW / Bayer stream / MIPI CSI 数据流 / 3A统计

处理：
固定或半固定流水线模块 + line buffer + 小窗口滤波 + 统计反馈

输出：
linear RGB / YUV / sRGB / JPEG/视频编码器输入 / metadata
```

GPU 的典型图像处理链路：

```text
输入：
纹理 / buffer / framebuffer / YUV/RGB图像 / ISP输出中间图 / 计算摄影多帧

处理：
shader或compute kernel + cache/shared memory + 全局内存读写 + 多pass算法

输出：
增强图像 / 后处理图 / 显示buffer / 编码输入 / AI前后处理结果
```

关键区别在于，ISP 通常靠流式数据和少量 line buffer 解决问题；GPU 通常把图像作为纹理或 buffer 放在内存里，再由大量线程并行访问。ISP 的数据路径更固定，GPU 的数据路径更自由，但自由通常意味着更多内存访问和调度成本。

## 3. 为什么 GPU 峰值算力不等于 ISP pipeline 性能

初学者常见误区是：GPU 有很多 TFLOPS，所以图像处理一定比 ISP 快。真实系统里，性能常常被以下因素限制：

- 数据要从 ISP 输出搬到 GPU 可访问的内存。
- 格式可能要从 RAW/YUV 转成 RGB 或纹理格式。
- GPU kernel 启动有调度开销。
- 多个 pass 之间要读写中间结果。
- GPU 正在和 UI、渲染、AI、视频后处理共享资源。
- 移动设备里 GPU 长时间满载会发热降频。
- GPU 高吞吐不一定带来低尾延迟，预览和视频更怕帧间抖动。

因此选择平台时要算完整链路：

```text
总延迟 =
传感器读出 + ISP处理 + 格式转换 + 内存搬运 + GPU排队 + GPU计算 + 同步 + 后续编码/显示
```

如果只算 GPU kernel 时间，很容易高估收益。

## 4. 并行模型：SIMT 线程 vs 确定性流水线

GPU 的并行模型通常是 SIMT/SIMD：很多线程执行同一段程序，每个线程处理一个像素、一个 tile、一个 block 或一个输出元素。NVIDIA CUDA 的 warp 通常是 32 个线程，AMD wavefront 常见 32 或 64 个 lane，移动 GPU 也有自己的 wave/quad/warp 概念。GPU 的优势是大规模并行和可编程性，适合复杂分支、纹理采样、多 pass 和通用计算。

ISP 的并行模型是流水线和局部窗口并行。每个模块像硬件工位一样持续处理像素流，多个模块可以同时处理不同阶段的数据。对 3x3、5x5 滤波，ISP 用 line buffer 保留相邻几行即可；对颜色矩阵、gamma、LUT、锐化等模块，数据路径非常确定。它的优势是延迟可预测、能效高、面积可控。

对比可以这样记：

| 维度 | ISP | GPU |
|---|---|---|
| 并行方式 | 固定流水线、像素流、窗口并行 | 大量线程、SIMT、kernel 并行 |
| 内存策略 | line buffer、片上小缓存、少写 DDR | cache、shared memory、global memory |
| 控制方式 | 寄存器参数、LUT、模式切换 | shader/compute 程序 |
| 优势 | 低功耗、低延迟、确定性 | 灵活、复杂算法、快速迭代 |
| 劣势 | 不灵活、修改硬件困难 | 搬运/调度/功耗成本高 |

## 5. 内存层级：GPU cache 和 ISP line buffer 的根本差别

图像处理常常不是算不动，而是搬不动。ISP 和 GPU 最大差别之一就是内存访问模式。

ISP 的 line buffer 适合流式局部操作。例如 3x3 filter 只需要缓存前两行和当前行的一部分窗口。数据从传感器进入后顺流向前，尽量不写回外部 DDR。这样功耗低、延迟稳定，非常适合实时相机。

GPU 的 cache 更通用。它可以随机访问纹理、采样任意坐标、做复杂邻域和多 pass，但如果访问模式不连续、cache 命中差或中间特征图巨大，外部带宽会成为瓶颈。

一个简单例子：4K 图像一帧约 3840x2160。如果是 16-bit RGB：

```text
3840 * 2160 * 3 * 16 bit ≈ 398 Mb ≈ 49.8 MB
```

如果某个 GPU 算法需要读一次、写一次，中间再读写两个临时 buffer，单帧就可能产生数百 MB 的内存流量。30fps 时就是数 GB/s。ISP 如果能在流水线内完成同类局部处理，外部带宽会小很多。

## 6. Tile-based：GPU TBR 和 ISP tiling 看起来像，但目的不完全一样

移动 GPU 中的 tile-based rendering 通过把屏幕分成小块，在片上 tile buffer 中完成尽可能多的渲染，再写回外部内存，从而节省带宽。Arm Mali、PowerVR 等移动 GPU 都长期强调 tile-based deferred rendering 或类似架构，核心原因是移动设备外部内存带宽和功耗很贵。

ISP tiling 也是为了控制片上缓存和带宽，但关注点不同：

- GPU tile 处理的是渲染中的 geometry、fragment、texture、depth、blend 等。
- ISP tile 处理的是图像滤波、局部 tone、畸变校正、NLM、AI 推理、HDR 融合等。
- GPU tile 需要处理图元跨 tile、深度、混合和纹理采样。
- ISP tile 需要处理 halo、滤波窗口、统计合并、tone mapping 边界和颜色一致性。

初学者要注意：tile 可以省内存，但会引入边界问题。比如 NLM、局部 tone mapping、AI denoise 如果 tile overlap 不够，拼接处会出现接缝、亮度跳变或纹理断裂。

## 7. 纹理单元和 ISP 滤波器：都在采样，但语义不同

GPU 纹理单元擅长做纹理采样、双线性/三线性过滤、mipmap、地址模式、格式转换等。它是图形渲染和图像后处理的重要硬件。ISP 滤波器也做局部采样和加权，例如 demosaic、锐化、降噪、缩放、畸变校正、色差校正。

相似点：

- 都需要读取邻域像素。
- 都要处理边界。
- 都关心插值精度。
- 都可以用固定功能硬件提升能效。

差异点：

- GPU 纹理采样更通用，坐标可以任意，适合 warp、EIS、后处理。
- ISP 滤波器更专用，常以固定窗口、固定格式和固定时序工作。
- ISP 早期模块处理 RAW Bayer，纹理单元通常更偏 RGB/YUV/纹理格式。
- ISP 对 bit depth、黑电平、饱和、噪声模型更敏感。

所以畸变校正、EIS、透视变换等几何类任务有时适合 GPU 或专用 warp engine；而黑电平、LSC、早期去马赛克、基础降噪更适合 ISP。

## 8. 可编程性：Shader 自由度高，可配置 ISP 更可控

GPU 的 shader/compute 编程模型很灵活。开发者可以快速写新算法，调试、更新、发布也方便。计算摄影、AR、滤镜、复杂后处理、研究算法通常喜欢 GPU，因为硬件不用改。

ISP 的可配置性通常体现为：

- 寄存器参数。
- LUT、gain map、CCM、tone curve。
- 模块开关和模式切换。
- 有限可编程单元或 microcode。
- 与 NPU/GPU/DSP 的异构协同。

可编程 ISP 是一个诱人方向，但挑战也大：

- 可编程性增加，验证难度增加。
- 灵活硬件通常比固定功能硬件功耗更高。
- 相机 pipeline 对实时性、稳定性和时序要求高。
- 开放编程接口会带来安全、兼容和画质一致性问题。

因此现实方案常是“固定 ISP + 可配置参数 + GPU/NPU 可编程后处理”的折中。

## 9. 任务选择：哪些适合 ISP，哪些适合 GPU，哪些适合 NPU

可以用任务特性判断平台：

| 任务 | 更适合平台 | 原因 |
|---|---|---|
| Black Level / Bad Pixel | ISP | 物理意义明确、流式、低成本 |
| LSC | ISP | gain map 插值和逐像素乘法，早期 RAW 处理 |
| Demosaic | ISP 或混合 | 固定算法适合 ISP，AI refine 可用 NPU/GPU |
| 基础降噪 | ISP | 局部窗口、实时、低功耗 |
| NLM/BM3D 类复杂降噪 | GPU/NPU/专用加速器 | 搜索窗口大、计算复杂 |
| HDR 多帧融合 | ISP+GPU/NPU | 对齐/融合复杂，实时性要求高 |
| Tone Mapping | ISP 或 GPU | 简单曲线适合 ISP，局部复杂增强适合 GPU |
| EIS/Warp | GPU 或专用 warp engine | 任意坐标采样和几何变换 |
| AR/滤镜/风格化 | GPU | shader 灵活，迭代快 |
| AI Denoise/SR | NPU/GPU | 神经网络算子 |
| 编码前轻量预处理 | ISP/GPU | 取决于是否需要复杂自适应 |

## 10. NVIDIA VPI 的启发：现代视觉系统是异构的

NVIDIA VPI 的设计很有代表性：同一个视觉算法 API 可以选择不同后端，例如 CPU、CUDA GPU、PVA 等。它说明现代图像和视觉系统不再迷信单个处理器，而是根据任务、平台和延迟选择后端。

对 ISP 学习者来说，这个思路很重要：

- 不要把全部算法塞进 ISP。
- 不要把全部算法丢给 GPU。
- 不要只看算力，要看数据在哪、输出给谁、下一步是什么。
- 最好的架构常常是把数据路径和算法边界一起设计。

例如相机预览链路可能是：

```text
传感器 -> ISP基础处理 -> GPU做EIS/AR合成 -> 显示
                      -> NPU做人脸/场景分析 -> 回写ISP参数
                      -> 编码器做视频压缩
```

这时真正困难的是同步和调度：GPU、NPU、ISP、编码器都在争用内存和功耗预算。

## 11. 小计算：为什么“搬到 GPU 做一下”并不免费

假设 4K 60fps YUV420 10-bit 视频，粗略按 1.5 个采样平面计算：

```text
3840 * 2160 * 1.5 * 10 bit * 60
≈ 7.46 Gbps
≈ 933 MB/s
```

如果把它从 ISP 输出搬到 GPU，GPU 处理后再写回给编码器，至少是一读一写：

```text
933 MB/s * 2 ≈ 1.87 GB/s
```

如果中间转成 RGB16、做多 pass，再写多个临时 buffer，带宽可能继续成倍增长。移动设备上，外部内存访问的功耗非常显著。所以很多相机系统宁愿把简单模块放在 ISP 里做，也不愿为了灵活性把整帧来回搬运。

## 12. 延迟、吞吐和确定性：视频链路尤其敏感

GPU 擅长吞吐，但相机预览和视频更关心稳定帧时间。如果某一帧 GPU 排队时间突然变长，用户会看到预览卡顿或视频掉帧。ISP 流水线虽然不灵活，但处理延迟可预测，更适合持续流式输出。

选择 GPU 时要关注：

- kernel 执行时间的平均值和 P95/P99。
- 是否和 UI 渲染竞争。
- 是否和 AI 推理竞争。
- 是否触发热降频。
- 是否需要 CPU 参与同步。
- 是否引入多帧 buffer，增加端到端延迟。

选择 ISP 时要关注：

- 模块是否支持所需算法。
- bit depth 和格式是否合适。
- 参数是否能动态更新。
- line buffer 是否够大。
- 是否会引入 tile 边界或统计不一致。

## 13. 常见失败现象速查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| GPU 算法单独很快，接入相机后变慢 | 数据搬运、格式转换、同步开销 | 量测完整链路，不只量 kernel |
| 预览偶发卡顿 | GPU 与 UI/AI 争用，队列抖动 | 看 P95/P99 延迟和资源调度 |
| GPU 后处理功耗过高 | 多 pass 和 DDR 读写过多 | 合并 pass、降低格式、tile、放回 ISP |
| ISP 输出边界接缝 | tiling overlap 不足 | 增加 halo、边界融合、统计合并 |
| GPU 结果和 ISP 结果色彩不同 | 色彩空间、range、gamma 不一致 | 检查 full/limited range、BT.709/BT.2020 |
| GPU filter 有边缘伪影 | 采样坐标、边界模式、插值精度问题 | 检查 clamp/mirror/wrap 和半像素偏移 |
| 同一算法不同平台结果不一致 | 精度、rounding、定点/浮点差异 | 统一量化和误差容忍 |
| 把 RAW 直接给 GPU 处理后画质异常 | RAW 黑电平、CFA、bit packing 未处理 | 检查 RAW 解包和前端校正 |

## 14. 最小可验证实验

实验 1：给任务选平台

```text
列出任务：
black level、LSC、demosaic、NLM、EIS、AI denoise、AR滤镜、tone mapping

为每个任务选择：
ISP / GPU / NPU / 混合
并写出计算模式、内存访问、延迟和功耗理由。
```

实验 2：完整链路延迟表

```text
假设一个GPU后处理算法 kernel 只要 2ms。
列出接入相机后还可能增加的时间：
格式转换、内存拷贝、GPU排队、同步、写回、编码等待。
```

实验 3：line buffer vs 全帧 buffer

```text
以 3x3 filter 为例：
说明 ISP 只需几行 buffer。
再说明 GPU 如果用全图纹理处理，需要如何读写图像。
比较两种方式的外部内存压力。
```

实验 4：tile 边界观察

```text
对一张图做局部增强或滤波。
整图处理一次，再分tile处理后拼接。
放大tile边界，观察亮度、颜色、纹理是否连续。
```

实验 5：色彩空间一致性检查

```text
把同一帧分别走 ISP 输出和 GPU 后处理输出。
检查 RGB/YUV range、gamma、BT.709/BT.2020、bit depth。
观察是否有偏色、灰阶压缩或高光异常。
```

## 15. 学习优先级

必须掌握：

- ISP 是流式专用流水线，GPU 是可编程并行处理器。
- GPU 峰值算力不等于相机链路性能。
- 数据搬运、格式转换、同步和外部内存带宽是关键成本。
- ISP line buffer 和 GPU cache 的设计目标不同。
- Tile-based 思想在 GPU 和 ISP 中都存在，但边界问题不同。
- 混合架构通常比单一平台更现实。

### 必须掌握点调研笔记

下面这几条不是背诵结论，而是判断相机系统架构时必须会用的分析框架。初学者可以把它们当作第 30 章的核心复习笔记。

## 1. ISP 是流式专用流水线，GPU 是可编程并行处理器

ISP 的基本假设是：图像数据从传感器连续进入，最好沿着固定 pipeline 一路向前流动。每个模块只处理自己负责的一小段任务，例如 black level、bad pixel、LSC、demosaic、denoise、CCM、gamma、tone mapping 等。硬件设计会尽量让像素不要频繁写回外部 DRAM，而是在片上寄存器、line buffer、局部窗口和 LUT 中完成处理。

GPU 的基本假设不同：它不是为了某一条相机 pipeline 固定设计的，而是为了大规模可编程并行计算。NVIDIA CUDA 文档把 CUDA 程序描述为由 thread block、shared memory、barrier synchronization 等抽象组织起来的并行程序；线程可以访问 global、shared、local、constant、texture 等不同内存空间。这个模型非常灵活，但也意味着程序员或运行时系统必须处理线程组织、内存访问、同步和 kernel 调度。

两者的差异可以这样理解：

| 维度 | ISP | GPU |
|---|---|---|
| 核心目标 | 稳定实时成像 | 通用并行计算和图形/视觉加速 |
| 数据形态 | sensor stream / Bayer stream / line-based dataflow | buffer / texture / image / tensor |
| 编程方式 | 寄存器、LUT、固定模块、有限可编程单元 | shader、CUDA/OpenCL/Metal/Vulkan compute |
| 典型优势 | 低功耗、低延迟、确定性强 | 灵活、吞吐高、算法迭代快 |
| 典型代价 | 算法变化不灵活，硬件改动贵 | 搬运、同步、缓存失效、功耗和调度成本高 |

判断一个任务更像 ISP 任务还是 GPU 任务，可以问四个问题：

1. 输入是不是严格按行或按像素流入？
2. 算法是不是固定、局部、每帧都要做？
3. 是否需要尽量少访问外部内存？
4. 是否比起灵活性，更关心稳定帧率、低功耗和确定延迟？

如果答案大多是“是”，它通常更适合 ISP 或专用硬件。如果算法经常变化、需要复杂几何变换、多 pass、全局优化、AI 模型或产品快速迭代，则 GPU/NPU/DSP 可能更合适。

## 2. GPU 峰值算力不等于相机链路性能

GPU 宣传资料里的 TFLOPS 或 TOPS 只说明理论计算吞吐，不等于真实相机 pipeline 的端到端性能。相机链路的关键指标通常包括：

- preview 延迟；
- video frame time 抖动；
- 连续拍摄时的热稳定；
- ISP/GPU/NPU/codec 之间的同步成本；
- 外部内存带宽；
- format conversion 成本；
- 与 UI、渲染、AI、编码器共享资源后的最坏情况延迟。

一个 GPU kernel 单独跑很快，不代表放到相机链路里仍然快。真实链路常常是：

```text
sensor readout
-> ISP base pipeline
-> format conversion / buffer export
-> GPU queue
-> GPU compute
-> synchronization fence
-> copy/import/export
-> display or video encoder
```

如果只测 `GPU compute`，就漏掉了前后的搬运、排队、同步和格式适配。CUDA 编程指南中也强调 GPU 作为 host 之外的协处理器使用时，host/device 内存空间和数据传输是编程模型的一部分。即使在统一内存、共享内存或移动 SoC 的 zero-copy 场景里，也仍然要考虑 cache coherency、buffer ownership、fence、layout 和访问模式。

一个简单估算可以帮助建立直觉。4K 60fps 的 10-bit YUV420 数据量约为：

```text
3840 * 2160 * 1.5 * 10 bit * 60
= 7.46 Gbit/s
= 933 MB/s
```

如果某个 GPU 后处理需要读一遍、写一遍，最少就是约 1.87 GB/s 的主存流量。若中间转成 RGB16、生成多个临时 buffer、做多 pass，带宽会继续翻倍。移动设备上外部内存访问不仅慢，而且功耗高，所以“把任务丢给 GPU”并不免费。

实际评估 GPU 接入相机链路时，应至少记录：

- 输入分辨率、fps、bit depth、pixel format；
- 每帧读写了几个 full-frame buffer；
- 是否发生 RAW/YUV/RGB 转换；
- 是否跨硬件模块导入/导出 buffer；
- 是否需要 CPU 参与同步或调度；
- GPU 平均耗时、P95/P99 耗时，而不仅是平均 FPS；
- 长时间运行后是否因温度降频。

## 3. 数据搬运、格式转换、同步和外部内存带宽是关键成本

图像系统里最贵的事情常常不是“算一下”，而是“把一整帧搬来搬去”。尤其在移动 SoC 中，外部 DRAM 带宽和功耗是系统瓶颈之一。Arm 对 Mali tile-based rendering 的解释也强调，tile-based GPU 的重要动机就是减少功耗很高的外部内存访问。

相机链路中的常见隐性成本包括：

- **搬运成本**：ISP 输出 buffer 给 GPU，GPU 再输出给 display 或 encoder。即使没有 CPU copy，也可能有 DMA、IOMMU 映射、cache flush/invalidate 或 buffer ownership 切换。
- **格式成本**：ISP 可能输出 RAW、YUV420、YUV422、RGB、10-bit packed、10-bit unpacked 等格式；GPU shader 更喜欢纹理友好的布局。一次格式转换可能引入额外 pass 和额外 full-frame buffer。
- **同步成本**：GPU、ISP、NPU、codec 和 display 之间不能随便读写同一块 buffer，需要 fence 或队列同步。同步粒度太细会拖慢系统，太粗会增加延迟。
- **带宽成本**：多 pass 算法每一轮读写 full-frame buffer，带宽会按 pass 数线性甚至更快增长。
- **缓存一致性成本**：一个模块写完，另一个模块读之前，需要保证看到的是最新数据。对初学者来说，可以先把它理解为“数据所有权交接不是免费的”。

因此评价一个 ISP/GPU 混合方案时，不要只问“这个算法 GPU 能不能跑”，还要问：

```text
数据现在在哪里？
下一步谁要用？
格式是否正好可用？
是否必须整帧落内存？
是否可以只传 ROI、metadata、统计量或低分辨率辅助图？
是否有多余的 readback？
```

很多工程优化的本质，是把 full-frame buffer 的读写次数降下来。例如：

- 能在 ISP 早期完成的线性校正，不要拖到 GPU 后处理；
- 能用统计量反馈的，不要传整帧；
- 能用硬件 scaler/warp/codec 前处理的，不要让 GPU 做无谓搬运；
- 多个 GPU pass 能融合就融合，减少中间图；
- 避免不必要的 RGB/YUV 来回转换；
- 对实时视频，优先保证稳定帧时间，而不是单帧峰值速度。

## 4. ISP line buffer 和 GPU cache 的设计目标不同

line buffer 是为流式图像处理服务的。许多 ISP 模块只需要当前像素附近的小窗口，例如 3x3、5x5、7x7。硬件只要保存前几行和当前行的一部分，就能持续产生窗口数据，而不必把整帧反复写入外部内存。图像处理 FPGA/硬件论文中常见的 streaming window、line buffer、SWIM/D-SWIM 架构，核心目标都是让图像流在片上缓存中形成局部窗口，从而支持高吞吐、低外存访问的实时处理。

以 3x3 filter 为例，如果按从左到右、从上到下的顺序处理图像，硬件只需要保留最近两行，加上当前行正在进入的数据，就能组成 3 行窗口：

```text
上一上一行：p00 p01 p02 ...
上一行：    p10 p11 p12 ...
当前行：    p20 p21 p22 ...

当前 3x3 window = 这些行中相邻的 3 列
```

GPU cache 的目标更通用。CUDA 文档中的 GPU 内存层级包括 global memory、shared memory、local memory、constant memory、texture memory 等。cache/shared memory 的目标是提升大量线程访问数据时的吞吐，适配不同程序的访问模式。它可以很好地支持纹理采样、矩阵运算、随机访问、复杂 neighborhood、block/tile 计算，但它不是为某一条固定相机流水线定制的。

两者不能简单互相替代：

| 问题 | ISP line buffer | GPU cache/shared memory |
|---|---|---|
| 数据流方向 | 强顺序、强流式 | 由 kernel 访问模式决定 |
| 缓存对象 | 少量相邻行和窗口 | block 内共享数据、纹理、全局内存访问 |
| 典型目标 | 减少整帧落外存，保证确定吞吐 | 提高可编程并行任务的吞吐 |
| 适合任务 | demosaic、局部滤波、基础降噪、卷积窗口 | warp、复杂后处理、多 pass、AI 前后处理 |
| 边界问题 | 图像边缘、行切换、窗口填充 | block/tile halo、cache miss、coalescing、同步 |

初学者容易犯的错误，是认为“GPU 有 cache，所以也能像 ISP 一样省带宽”。实际要看访问模式。如果 GPU kernel 每个 pass 都读写整帧，并且中间结果都落到 global memory，那么 cache 只能缓解局部访问，不能消除 full-frame buffer 的读写成本。

## 5. Tile-based 思想在 GPU 和 ISP 中都存在，但边界问题不同

Tile-based 思想的共同点是：不要一次处理整张大图，而是把画面切成小块，在片上缓存或局部内存里尽量完成更多工作，从而减少外部内存访问。

在移动 GPU 中，tile-based rendering 的对象是图形渲染。Arm Mali 和 PowerVR 等移动 GPU 长期使用 tile-based 架构，一个重要原因是移动平台外部内存访问昂贵。TBR 会把 framebuffer 分成 tile，尽量在片上 tile buffer 中完成 color、depth、stencil、blend 等工作，最后再把必要结果写回外部内存。Vulkan 的 TBR best practices 也会建议通过 render pass、load/store op 等方式减少不必要的带宽浪费。

在 ISP 中，tiling 的对象是图像算法。它可能用于局部 tone mapping、NLM、畸变校正、EIS、AI denoise、HDR 融合或大图处理。ISP tiling 关注的是图像连续性和算法窗口，而不是图形渲染里的 geometry/depth/blend。

两个领域最容易混淆的是“边界”。GPU TBR 的边界问题包括：

- primitive 跨 tile；
- depth/stencil 的保留或丢弃；
- render target load/store；
- texture sampling；
- blending 和 subpass 依赖。

ISP tiling 的边界问题包括：

- filter halo 是否足够；
- NLM 搜索窗口是否跨 tile；
- 局部 tone mapping 的统计量是否连续；
- 畸变校正和 EIS 的采样是否越界；
- AI denoise/SR 的 receptive field 是否在 tile 边缘截断；
- tile 拼接处亮度、颜色、纹理是否出现接缝。

一个实用判断是：

```text
如果算法输出像素只依赖局部 R 半径内的输入，
tile 至少要额外读取 R 像素 halo。

如果算法依赖全局统计量或自适应曲线，
tile 之间还必须共享统计量或做平滑融合。
```

例如 5x5 filter 至少需要 2 像素 halo；NLM、AI denoise、local tone mapping 的有效依赖范围更大，halo 不足时会出现拼接线、纹理断裂、亮度跳变或色彩不一致。

## 6. 混合架构通常比单一平台更现实

现实产品很少是“全部 ISP”或“全部 GPU”。更常见的做法是让不同硬件处理自己最擅长的部分：

```text
sensor
-> ISP: black level / bad pixel / LSC / demosaic / basic denoise / color
-> NPU: scene/person/face/semantic analysis or AI denoise
-> GPU: EIS / AR / preview composition / flexible post-processing
-> codec/display
```

NVIDIA VPI 的设计可以作为一个很好的参考：同一套视觉 API 可以把不同算法放到 CPU、CUDA GPU、PVA 等后端执行；其中 PVA 是 Jetson 平台上面向图像处理和计算机视觉的专用处理器，文档明确强调它在相关任务上比 CPU/CUDA 更省电。这说明现代视觉系统的重点不是信仰某一个处理器，而是按任务特征选择后端。

混合架构的优势是：

- 固定、稳定、低延迟的成像基础模块放 ISP；
- 经常变化、产品差异化强的后处理放 GPU；
- 神经网络推理放 NPU；
- CPU 负责控制、策略、调参和异常处理；
- codec/display 使用专用硬件，避免占用 GPU。

混合架构的难点是：

- buffer 在多个硬件模块之间流转；
- fence 和 queue 设计复杂；
- cache coherency 和 DMA 配置容易出错；
- 多模块共享内存带宽和功耗预算；
- 算法拆分不当会导致来回搬运；
- 画质问题可能来自任意模块，定位困难。

因此做架构选择时，建议使用下面的决策表：

| 任务特征 | 优先考虑 |
|---|---|
| 每帧必做、局部窗口、低延迟、固定算法 | ISP / fixed-function hardware |
| 任意坐标采样、几何变换、AR 合成、快速迭代 | GPU / warp engine |
| CNN/Transformer/语义分割/超分/AI 降噪 | NPU / GPU |
| 复杂控制逻辑、策略、低频调参 | CPU |
| 视频压缩、显示扫描、格式封装 | codec/display 专用模块 |

最重要的原则是：先设计数据路径，再分配计算任务。不要先决定“用 GPU 做”或“用 ISP 做”，而要先画清楚数据从哪里来、在哪里被消费、是否需要落外存、是否需要跨模块同步，以及每一步是否改变格式和 bit depth。

## 7. 推荐资料与出处

- NVIDIA CUDA C++ Programming Guide：用于理解 GPU 编程模型、thread hierarchy、shared memory、global memory、texture memory、host/device memory 和数据传输问题。  
  https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- NVIDIA VPI Architecture：用于理解现代视觉系统为什么会按 CPU、CUDA、PVA 等不同 backend 分配算法。  
  https://docs.nvidia.com/vpi/html/architecture.html
- Arm Mali tile-based rendering 资料：用于理解移动 GPU 为什么通过 tile-based rendering 减少外部内存访问和功耗。  
  https://community.arm.com/arm-community-blogs/b/mobile-graphics-and-gaming-blog/posts/the-mali-gpu-an-abstract-machine-part-2---tile-based-rendering
- Vulkan Guide: Tile Based Rendering Best Practices：用于理解 render pass、load/store op 等机制如何影响 tile-based GPU 带宽。  
  https://github.khronos.org/Vulkan-Site/guide/latest/tile_based_rendering_best_practices.html
- High-Throughput Line Buffer Microarchitecture for Arbitrary Sized Streaming Image Processing：用于理解 line buffer / stream-windowing 架构为什么适合实时流式图像处理。  
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8320917/

了解即可：

- 各家 GPU 的具体 warp/wavefront/线程调度细节。
- 每种移动 GPU 的 tile renderer 微架构。
- 图形管线中 tessellation、deferred rendering 的全部细节。
- 具体 API 的完整编程语法。

后面再回看：

- CUDA/OpenCL/Metal/Vulkan compute 性能优化。
- GPU texture cache 和 shared memory 调优。
- ISP RTL line buffer 和流水线时序。
- 异构调度、zero-copy buffer、DMA 和 cache coherency。
- 可编程 ISP 和统一视觉处理器架构。

## 16. 自测题

1. 为什么 ISP 的固定功能硬件在相机链路中仍然很有价值？
2. 为什么 GPU kernel 很快，不代表接入相机后总延迟很低？
3. line buffer 和 GPU cache 的根本差别是什么？
4. tile-based rendering 和 ISP tiling 分别解决什么问题？
5. 为什么 NLM、EIS、AR 滤镜比 black level 更适合 GPU 或专用可编程后端？
6. GPU 后处理为什么可能增加视频编码前的带宽压力？
7. 为什么相机视频更关心 P95/P99 延迟，而不是只看平均时间？
8. 如果 GPU 输出偏色，你会检查哪些格式和色彩空间问题？
9. 可编程 ISP 为什么不一定能完全替代 GPU？
10. 如何设计一个混合 ISP+GPU+NPU 的相机链路？

## 17. Gotchas：初学者最容易踩的坑

- 只看 GPU 峰值算力，不算数据搬运。
- 把图像算法从 CPU/GPU demo 直接搬进相机链路，忽略格式和同步。
- 认为 ISP 固定就是落后，忽略能效和确定性。
- 认为 tile 一定省事，忽略 halo 和边界融合。
- 忽略 RAW/YUV/RGB 的 range、gamma、色彩标准差异。
- 只测平均 FPS，不测帧时间抖动和长时间热稳定。
- 把所有可变算法都塞进 GPU，导致 UI、AI、视频编码争用。
- 用全帧中间 buffer 做多 pass，造成外部带宽爆炸。

## 18. 读完本章的验收标准

读完后，你应该能做到：

- 画出 ISP 流水线和 GPU compute/shader 图像处理链路。
- 解释 ISP line buffer、GPU cache、tile buffer 的差别。
- 给一个具体算法判断更适合 ISP、GPU、NPU 还是混合架构。
- 用 4K60 数据量估算说明 GPU 往返处理的带宽成本。
- 设计一张完整链路性能表，包含计算、搬运、同步、延迟、功耗和热。
- 根据卡顿、偏色、tile 接缝、功耗高等现象推测架构原因。

## 19. 推荐资料、论文与工程资料

- NVIDIA VPI 官方文档：理解同一视觉算法如何选择 CPU、CUDA、PVA 等异构后端。
- CUDA Programming Guide / CUDA Best Practices：理解 SIMT、warp、global/shared memory、occupancy 和带宽优化。
- Arm Mali GPU Best Practices / Tile-based Rendering 资料：理解移动 GPU 为什么重视 tile-based rendering 和外部带宽。
- Imagination PowerVR Tile-Based Deferred Rendering 资料：理解移动 GPU tile buffer、deferred rendering 和 bandwidth saving。
- AMD/Xilinx Vitis Vision Library：理解 FPGA/加速器中的流式图像处理、line buffer 和硬件 pipeline。
- Halide 相关论文和教程：理解图像算法中 algorithm 与 schedule 分离，为什么 tiling、vectorization、parallelization 会改变性能。
- Infinite-ISP、OpenISP、Raspberry Pi libcamera pipeline：理解真实 ISP pipeline、调参和硬件/软件边界。
- GPU Gems / Real-Time Rendering 中的图像后处理章节：理解 shader 风格图像处理和 texture sampling。
## 可追溯资料入口

- [按章节映射的参考资料](../research_bibliography.md#按章节映射的一手入口)
- [来源、证据等级与时效规范](../SOURCE_POLICY.md)
- 本章涉及的产品参数必须记录型号、版本、发布日期/访问日期和证据等级。

## 本章学习闭环

- 配套实验：[lab11-异构性能与编码协同.md](../labs/lab11-异构性能与编码协同.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter30-第30章：ISP与GPU架构对比研究.md)
- 项目落点：
  - [C++ benchmarks](../../stage3_cpp_isp/benchmarks)
- [设备流水线](../../stage4_deploy_isp/cpp/src/device_pipeline.cpp)
- [质量-延迟-内存矩阵](../../stage4_deploy_isp/outputs/device_pipeline/quality_latency_memory_matrix.csv)
- 原始资料：[原教程正文归档](../source_archive/chapter30-第30章：ISP与GPU架构对比研究.md)

导航：[上一章](./chapter29-第29章：深度学习增强的ISP模块.md) · [下一章](./chapter31-第31章：ISP与视频编解码器架构对比.md) · [完整课程索引](../full_content_index.md)
