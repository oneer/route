# 第14章：HDR技术与Tone Mapping


> 课程阶段：硬件架构、HDR、计算摄影与 3A　|　难度：入门 → 中级　|　优先级：核心
>
> 建议用时：3–4 小时阅读 + 2–4 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**区分 HDR 采集、融合、去鬼影、tone mapping 和 HDR 显示。**

## 1. 本章先解决什么问题

真实世界的亮度范围非常大。一个场景里可能同时有阳光下的白墙、隧道里的暗车、夜晚车灯、室内窗外天空。传感器、ISP 内部位宽、显示器和压缩格式都不可能无限表示这些亮度。HDR 和 Tone Mapping 解决的就是这个矛盾：

```text
HDR：尽量捕获或重建更宽的场景亮度范围。
Tone Mapping：把宽动态范围压缩到显示/编码范围里，同时尽量保留可见细节和自然观感。
```

本章最小链路是：

```text
输入：多曝光 RAW、单帧 HDR RAW、DOL-HDR 交错行、split-pixel HDR 或高 bit-depth 线性图像
处理：曝光归一化、配准、运动检测、融合、动态范围压缩、局部对比控制、HDR 显示适配
输出：可显示/编码/感知任务使用的 SDR 或 HDR 图像/视频
```

读完本章，至少要能回答：

- HDR capture、HDR merge、tone mapping 为什么是不同步骤。
- 多曝光 HDR 为什么怕运动和 rolling shutter。
- DOL-HDR、split pixel HDR、多帧包围曝光各自取舍是什么。
- 全局 tone mapping 和局部 tone mapping 差在哪里。
- halo、ghosting、clipping、过度局部对比是怎么来的。

## 2. 先理解动态范围

动态范围描述的是最亮和最暗可分辨信号之间的比例。常用 dB 表示：

```text
DR = 20 * log10(Lmax / Lmin)
```

如果最亮亮度是最暗亮度的 1000 倍：

```text
DR = 20 * log10(1000) = 60 dB
```

如果比例是 1,000,000 倍：

```text
DR = 20 * log10(1,000,000) = 120 dB
```

真实场景可能远超普通显示器和普通单次曝光能覆盖的范围。单次曝光通常会遇到两难：

```text
曝光偏长：暗部看清了，亮部饱和成一片白。
曝光偏短：亮部保住了，暗部一片黑或噪声很大。
```

HDR 的目标就是同时拿到暗部和亮部更多有效信息。但拿到更多信息后，还必须把它压回屏幕能显示的范围，这就是 tone mapping。

## 3. HDR Capture、HDR Merge、Tone Mapping 不要混

初学者经常把 HDR 和 tone mapping 混成一个词。工程上最好拆开：

| 阶段 | 解决什么 | 输入 | 输出 | 常见问题 |
|---|---|---|---|---|
| HDR Capture | 如何采到更多动态范围 | 多曝光/特殊传感器 RAW | 多路曝光或 HDR RAW | 运动、读出、噪声、饱和 |
| HDR Merge | 如何融合不同曝光 | 长/中/短曝光图 | 高动态范围线性图 | 配准、权重、鬼影 |
| Tone Mapping | 如何压到显示范围 | HDR 线性图 | SDR/HDR display image | halo、局部对比、自然度 |
| HDR Display | 如何按标准显示 | PQ/HLG/metadata | HDR 视频/图像 | 显示能力、元数据、色域 |

一句话：

```text
HDR capture/merge 是“把信息拿回来”。
Tone mapping 是“把信息压给人看或给系统用”。
```

## 4. 多曝光 HDR：长曝光看暗部，短曝光保高光

最直观的 HDR 方法是拍多张不同曝光：

```text
长曝光 LE：暗部信号强，暗部细节多，但亮部容易饱和。
短曝光 SE：亮部不容易饱和，但暗部信号弱、噪声大。
中曝光 ME：连接长短曝光之间的过渡。
```

融合前通常要做曝光归一化。假设长曝光时间是短曝光的 16 倍：

```text
LE_time / SE_time = 16
若 SE 像素值要对齐到 LE 曝光尺度，可乘以 16
若 LE 像素值要对齐到 SE 曝光尺度，可除以 16
```

但不能简单平均，因为每个曝光的可信区域不同：

- 长曝光暗部可信，亮部可能饱和。
- 短曝光亮部可信，暗部可能被 read noise 淹没。
- 中曝光负责过渡。

所以 HDR merge 常用权重图：

```text
融合值 = sum(weight_i * normalized_exposure_i) / sum(weight_i)
```

权重通常会降低太暗、太亮、饱和、低信噪比区域的贡献。

## 5. 权重融合的直觉和例子

假设一个场景点在三种曝光下归一化到同一亮度尺度：

```text
短曝光 SE：900，未饱和但暗部噪声较大
中曝光 ME：920，可信
长曝光 LE：4095，已经饱和
```

如果简单平均：

```text
(900 + 920 + 4095) / 3 = 1971.7
```

这显然被饱和的长曝光拉坏了。

合理融合应给长曝光很低权重：

```text
w_SE = 0.4
w_ME = 0.6
w_LE = 0.0
result = (0.4*900 + 0.6*920) / 1.0 = 912
```

另一个暗部例子：

```text
SE：15，几乎全是噪声
ME：120，有一些信号
LE：1900，可信
```

此时应主要相信长曝光：

```text
w_SE = 0.0
w_ME = 0.2
w_LE = 0.8
```

这就是多曝光融合的核心：不是让每张图贡献一样多，而是在每个像素位置选择最可信曝光。

## 6. 多曝光 HDR 最怕运动和鬼影

多曝光需要不同时间采集。如果相机或物体动了，同一个空间点在不同曝光里位置不同，直接融合会出现 ghosting：

- 人或车出现半透明重影。
- 树叶边缘糊成多层。
- 车灯拖出奇怪轮廓。
- 运动物体周围局部亮度跳变。

处理方法包括：

- 全局配准：补偿相机整体移动。
- 局部运动估计：估计物体或区域运动。
- 运动掩码：运动区域只信单个曝光或降低融合强度。
- deghosting：识别冲突区域，避免多曝光混合。
- DOL/sensor HDR：尽量缩短曝光间时间差。

Mertens、Kautz、Van Reeth 的 Exposure Fusion 提供了一个重要思路：不一定先恢复完整 HDR radiance map，也可以根据对比度、饱和度和曝光合适程度直接融合成显示图。但它同样需要面对配准和运动问题。

## 7. 传感器 HDR：DOL、Split Pixel、DCG

真实相机里，HDR 不一定靠连续拍多帧。传感器本身也可以提供 HDR 模式。

| 模式 | 核心思路 | 优点 | 风险 |
|---|---|---|---|
| 多帧包围曝光 | 连续拍长/中/短曝光 | 动态范围扩展大，灵活 | 运动鬼影、帧缓存和延迟 |
| DOL-HDR | 一帧读出中交错多种曝光 | 时间差小，车载常见 | 行重组、带宽、rolling shutter 复杂 |
| Split Pixel HDR | 不同像素灵敏度不同 | 单次曝光，运动友好 | 空间分辨率和 demosaic 更复杂 |
| Dual Conversion Gain | 同一像素不同转换增益 | 噪声/满阱折中好 | 传感器和融合模型依赖硬件 |
| LOFIC 等扩展满阱技术 | 增强高光容量 | 单帧高动态 | 工艺复杂，模型不同 |

DOL-HDR 的一个重要特点是数据可能以交错行形式输出，例如某些行属于短曝光，某些行属于长曝光。ISP 前端要先做 line de-interleave、曝光对齐和融合，再进入后续 pipeline。

Split pixel HDR 则在空间上混合不同灵敏度像素，运动更友好，但要付出空间采样和重建复杂度代价。

## 8. Tone Mapping：压缩动态范围，不是简单变亮

HDR merge 后得到的是更宽动态范围的线性亮度或 RGB。显示器或 SDR 图像无法直接显示这么宽的范围，所以要 tone mapping。

Tone mapping 的目标是：

```text
保住高光层次
抬起暗部可见性
保持中间调自然
避免局部对比过度
避免 halo 和灰雾感
符合显示标准或主观风格
```

最简单的 tone curve 可能是：

- 线性缩放。
- gamma 曲线。
- S-curve。
- logarithmic curve。
- Reinhard operator。
- filmic curve。
- 局部 tone mapping。

线性缩放最简单，但如果场景动态范围很大，绝大部分像素会被压在暗部，观感很差。S-curve 可以提升中间调对比，同时压缩高光和暗部。Reinhard 2002 的 photographic tone reproduction 是经典 tone mapping 论文，把摄影经验引入数字图像动态范围压缩。

## 9. 全局 Tone Mapping 和局部 Tone Mapping

全局 tone mapping 对所有像素使用同一条曲线：

```text
out = f(in)
```

优点：

- 稳定。
- 易硬件实现。
- 视频不容易闪烁。
- 不容易产生局部 halo。

缺点：

- 局部细节可能被压平。
- 亮暗同时存在的场景很难兼顾。

局部 tone mapping 会根据邻域亮度或 base/detail 分解调整不同区域：

```text
out(x,y) = f(in(x,y), local_context(x,y))
```

优点：

- 暗部和亮部细节可见性更强。
- 能提升局部对比。

缺点：

- 容易产生 halo。
- 可能看起来不自然。
- 视频中可能闪烁。
- 硬件需要更多缓存和计算。

## 10. Halo 为什么出现

局部 tone mapping 常先分解：

```text
图像 = base layer + detail layer
```

base layer 表示大范围亮度，detail layer 表示局部细节。问题是，如果 base layer 在强边缘附近估计不准，就会在亮暗边界产生光晕 halo。

典型场景：

- 黑色建筑边缘挨着亮天空。
- 人物轮廓挨着窗户。
- 车身挨着强车灯。
- 树枝挨着白云。

抑制 halo 的方法：

- 使用边缘保持滤波，如 bilateral filter、guided filter。
- 控制局部增强强度。
- 对高对比边缘做保护。
- 多尺度融合时约束 base/detail。
- 视频中对 tone map 参数做时域平滑。

## 11. HDR 显示：PQ、HLG 和 SDR 输出不是一回事

Tone mapping 不一定只输出 SDR。现代 HDR 显示涉及 PQ、HLG、BT.2020、HDR10、Dolby Vision 等标准或生态。

简单区分：

| 输出目标 | 特点 | 关注点 |
|---|---|---|
| SDR sRGB/BT.709 | 普通显示和网页图像 | 压缩到较窄动态范围 |
| HDR10/PQ | 绝对亮度编码，常配静态元数据 | 峰值亮度、MaxCLL、MaxFALL |
| HLG | 广播友好，相对亮度方式 | 兼容 SDR 广播链路 |
| 车载/机器视觉输出 | 未必追求好看 | 目标可见性、稳定性、低延迟 |

PQ 和 HLG 是 HDR 显示传输函数，不等于 ISP 内部的 HDR merge。初学者要分清：

```text
HDR sensor/merge：图像采集与重建问题。
Tone mapping：动态范围压缩问题。
PQ/HLG：HDR 显示编码问题。
```

## 12. 车载和机器人场景更重视稳定可见

消费相机 HDR 常追求观感：天空不过曝、暗部有细节、整体好看。车载、机器人、安防场景更关注：

- 隧道口是否能同时看清暗车和亮出口。
- 夜晚车灯旁边的行人是否可见。
- LED 交通灯是否饱和变色。
- HDR 融合是否产生鬼影影响检测。
- tone mapping 是否让目标边缘稳定。
- 视频帧间亮度是否闪烁。

对机器视觉来说，局部 tone mapping 过强可能让人眼觉得“细节多”，但会改变特征分布，影响检测、跟踪、SLAM 或测距。因此 HDR 的评价要结合下游任务，而不只是看主观漂亮。

## 13. HDR ISP 的硬件和数据流压力

HDR 比普通 ISP 更吃资源：

- 多曝光需要更多输入数据。
- DOL-HDR 需要行解交错和重组。
- 多帧 HDR 需要帧缓存。
- 融合需要权重图、运动检测和归一化。
- 局部 tone mapping 需要 base/detail、滤波和局部统计。
- HDR 显示可能需要更高 bit depth 和元数据。

一个简单带宽直觉：

```text
普通 RAW12 4K30：一份 RAW 输入。
2-exposure HDR：可能接近 2 份 RAW 数据量，加上融合中间结果。
3-exposure HDR：可能接近 3 份 RAW 数据量，或通过 DOL 压缩但仍显著增加。
```

因此 HDR pipeline 需要格外关注：

- line buffer 和 frame buffer。
- exposure 对齐。
- 位宽增长。
- 饱和标记。
- 运动掩码。
- 参数在帧间平滑。
- 最坏情况 DDR 带宽。

## 14. 最小可验证实验

实验 1：曝光融合直觉。

1. 准备一张高对比场景，或用同一场景生成短/中/长曝光版本。
2. 标出长曝光饱和区域、短曝光暗噪区域。
3. 用简单权重融合。
4. 对比简单平均和可信权重融合。

实验 2：运动鬼影。

1. 准备两张曝光不同且物体位置有轻微变化的图。
2. 直接融合。
3. 观察运动物体边缘是否出现重影。
4. 加入运动 mask，只在静态区域融合多曝光。

实验 3：tone curve 对比。

1. 使用一张 HDR 或高 bit-depth 线性图。
2. 分别应用线性缩放、gamma、S-curve、Reinhard。
3. 比较暗部、亮部、中间调和整体对比。
4. 记录哪种曲线更容易压高光，哪种更容易灰。

实验 4：局部 tone mapping 与 halo。

1. 选择强边缘图，例如建筑对天空。
2. 用局部增强提高暗部。
3. 调大和调小边缘保持滤波参数。
4. 观察建筑边缘是否出现光晕。

实验 5：任务稳定性。

1. 用连续视频或多帧模拟 HDR/tone mapping。
2. 观察帧间亮度和色彩是否跳变。
3. 对同一目标区域记录亮度曲线。
4. 判断 tone mapping 是否对检测/跟踪稳定。

## 15. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 亮部仍然一片白 | 短曝光不足、饱和权重没排除、tone curve 压缩不够 | 看各曝光饱和 mask |
| 暗部噪声很脏 | 长曝光不足或短曝光被过度用于暗部 | 看融合权重和暗部 SNR |
| 运动物体有重影 | 多曝光未配准或 deghost 失败 | 看运动 mask 和曝光时间差 |
| 边缘有 halo | 局部 tone mapping/base layer 估计不稳 | 调边缘保持滤波和局部增强强度 |
| 画面发灰 | 全局压缩过强，中间调对比不足 | 调 S-curve、局部对比和黑白点 |
| 高光颜色怪 | 某些通道饱和但融合仍使用 | 检查 per-channel saturation |
| 视频闪烁 | HDR 融合权重或 tone 参数帧间跳变 | 做时域平滑和场景切换检测 |
| DOL 行纹/错行 | 曝光行解交错或重组错误 | 检查 DOL raw packing 和行映射 |
| AI/检测效果下降 | tone mapping 改变特征分布 | 加任务指标评估，不只看视觉 |

## 16. 常见误区

- 误区 1：HDR 就是把图变亮。HDR 是扩展可用动态范围，tone mapping 才决定最终亮度外观。
- 误区 2：多曝光直接平均就行。饱和、噪声和运动区域必须有不同权重。
- 误区 3：局部 tone mapping 越强越好。过强会 halo、假细节、视频闪烁。
- 误区 4：HDR merge 后就能直接显示。宽动态线性数据必须经过合适显示映射。
- 误区 5：只看单帧 HDR 效果。视频 HDR 更要看帧间稳定和运动伪影。
- 误区 6：消费 HDR 和机器视觉 HDR 评价一样。前者偏观感，后者更重视目标可见性和稳定性。
- 误区 7：HDR 只增加算法，不增加系统压力。多曝光、缓存、带宽、位宽和功耗都会上升。

## 17. 学习优先级

必须掌握：

- 动态范围 dB 的含义。
- HDR capture、HDR merge、tone mapping、HDR display 的区别。
- 长/中/短曝光各自可信区域。
- 权重融合和饱和/噪声排除。
- ghosting、halo、clipping、灰雾感的原因。
- 全局和局部 tone mapping 的取舍。

了解即可：

- DOL-HDR、split pixel HDR、DCG 等传感器 HDR 模式。
- Reinhard、Exposure Fusion、bilateral/guided local tone mapping。
- PQ、HLG、HDR10 元数据。
- HDR 视频的时域稳定和动态元数据。

后面再回看：

- 相机响应曲线恢复和 radiance map 标定。
- 多帧运动补偿 HDR 和 rolling shutter HDR。
- HDRNet、3D LUT、学习型局部增强和端侧部署。
- HDR/WCG 的色域映射、色调映射和显示适配。

## 18. 自测题

1. HDR capture、HDR merge、tone mapping 分别解决什么问题？
2. 为什么长曝光适合暗部、短曝光适合高光？
3. 多曝光融合为什么不能简单平均？
4. 运动物体为什么会产生 HDR 鬼影？
5. DOL-HDR 和普通多帧包围曝光相比有什么优势和复杂性？
6. 全局 tone mapping 和局部 tone mapping 各自有什么风险？
7. halo 通常出现在哪些区域？为什么？
8. PQ/HLG 和 tone mapping 是同一件事吗？
9. 对车载 HDR，为什么“目标可见性”比“照片好看”更重要？
10. 如何设计实验证明局部 tone mapping 参数过强会影响视频稳定？

## 19. 读完本章的验收标准

合格的学习结果应该是：

- 口头解释：能讲清 HDR 是扩展/融合动态范围，tone mapping 是压缩到显示或任务可用范围。
- 输入输出：能写出多曝光 HDR pipeline 的输入、融合、输出和后续 tone mapping。
- 公式理解：能用 dB 公式算一个亮度比例对应的动态范围。
- 现象排查：能根据鬼影、halo、暗部噪声、高光饱和、视频闪烁提出原因。
- 工程判断：能说明多曝光、DOL、split pixel、全局/局部 tone mapping 的取舍。
- 实验验证：能用曝光融合、tone curve、局部增强和视频稳定实验检查 HDR 效果。

## 20. 推荐资料与进一步阅读

- [Debevec and Malik, Recovering High Dynamic Range Radiance Maps from Photographs](https://people.eecs.berkeley.edu/~malik/papers/debevec-malik97.pdf)：经典 HDR radiance map 恢复论文。
- [Mertens, Kautz, Van Reeth, Exposure Fusion](https://documentserver.uhasselt.be/handle/1942/11392)：多曝光融合的重要方法，适合理解权重和金字塔融合。
- [Reinhard et al., Photographic Tone Reproduction for Digital Images](https://research-information.bris.ac.uk/en/publications/photographic-tone-reproduction-for-digital-images/)：经典 tone mapping 算子。
- [HDRNet: Deep Bilateral Learning for Real-Time Image Enhancement](https://arxiv.org/abs/1707.02880)：学习型实时图像增强和 bilateral grid 思路。
- [Google HDRNet GitHub](https://github.com/google/hdrnet)：HDRNet 的开源实现，可参考训练和推理结构。
- [Raspberry Pi Camera Algorithm and Tuning Guide](https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf)：从真实相机调参角度理解 HDR、tone curve 和 ISP 参数。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab07-HDR计算摄影与3A稳定性.md](../labs/lab07-HDR计算摄影与3A稳定性.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter14-第14章：HDR技术与ToneMapping.md)
- 项目落点：
  - [Tone 实现](../../stage1_soft_isp/soft_isp/tone.py)
- [C++ tone benchmark](../../stage3_cpp_isp/benchmarks/bench_tone_mapping.cpp)
- [HDR/LTM 数据](../../stage3_cpp_isp/data/week7_alignment)
- 原始资料：[原教程正文归档](../source_archive/chapter14-第14章：HDR技术与ToneMapping.md)

导航：[上一章](./chapter13-第13章：ISP时序与功耗优化.md) · [下一章](./chapter15-第15章：计算摄影与高级ISP功能.md) · [完整课程索引](../full_content_index.md)
