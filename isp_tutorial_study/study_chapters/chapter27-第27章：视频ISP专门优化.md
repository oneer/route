# 第27章：视频ISP专门优化


> 课程阶段：产业平台与应用场景（选修）　|　难度：中级/选修　|　优先级：选修/按方向
>
> 建议用时：2–3 小时阅读 + 1–2 小时证据分析　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**以时域稳定、带宽、HDR/Log、色度采样和编码协同评价视频 ISP。**

## 1. 本章先建立直觉：视频 ISP 的敌人是“帧间不稳定”

照片 ISP 可以把一张图修到最好；视频 ISP 要让一串连续图像看起来自然、稳定、低延迟、可编码。很多问题在单帧上不明显，播放起来才会暴露：亮度闪、白平衡跳、降噪强度变、锐化忽强忽弱、HDR tone mapping 抽动、EIS 拉扯、rolling shutter 果冻、运动目标拖影、压缩后蚊噪。

所以视频 ISP 的核心不是“每帧单独最优”，而是“连续时间上的整体最优”。这带来几个特殊要求：

- 帧间一致性比单帧指标更重要。
- 所有自动参数都要平滑：AE、AWB、AF、NR、sharpen、tone curve、LUT。
- 时域算法必须区分静态背景和运动目标。
- 低延迟限制多帧缓存和复杂后处理。
- 输出要编码友好，不能制造过多随机噪声和高频伪影。
- 长时间 4K/8K/HDR/高帧率视频要考虑功耗和热。

## 2. 输入、处理、输出：视频 ISP 是连续流系统

视频 ISP 的最小链路可以写成：

```text
输入：
连续RAW帧 / 多曝光RAW / sensor metadata / 3A统计 / gyro/IMU / lens/OIS状态 / 编码器反馈

处理：
基础ISP -> AE/AWB/AF平滑 -> TNR/视频降噪 -> HDR视频融合 -> EIS/rolling shutter correction
-> 色彩管理/Log/HDR格式 -> 编码前预处理 -> buffer和metadata同步

输出：
预览YUV / 录制YUV或RGB / HDR/Log视频 / 编码器输入 / 稳定化视频 / 同步metadata
```

和拍照相比，视频链路更强调：

- 固定帧率。
- 固定延迟上限。
- 帧间参数连续。
- buffer 不爆、不饿、不乱序。
- metadata 和图像严格对齐。
- 与编码器、显示、NPU/GPU 同步。

## 3. 8K、高帧率和 HDR：先被数据量压住

8K 60fps 12-bit RAW 的输入数据量约为：

```text
7680 * 4320 * 60 * 12 bit
= 23,887,872,000 bit/s
≈ 23.9 Gbps
≈ 2.99 GB/s
```

这只是单路 RAW 输入。如果经过多帧降噪、HDR 融合、EIS、编码前处理，中间读写可能是输入的数倍。高帧率如 4K120 或 1080p240，也会把吞吐、DDR、功耗和热推到很高。

视频 ISP 常用优化：

- 多像素并行 pipeline。
- line buffer 和 tile processing。
- 中间数据压缩。
- 减少全帧写回。
- 分辨率自适应处理。
- 对预览、录像、AI 分析分流。
- 按场景关闭非关键模块。

## 4. 时域降噪 TNR：背景越干净，运动越容易拖影

视频降噪和单帧降噪不同。TNR 可以利用历史帧降低随机噪声：

```text
Y_out(t) = α * Y_current(t) + (1 - α) * Y_history(t-1)
```

如果画面静止，历史帧很有用；如果目标在运动，历史帧位置不对，就会拖影。`α` 越小，历史权重越大，降噪越强，拖影风险越高；`α` 越大，当前帧权重越大，拖影少但噪声多。

工程上的 TNR 通常需要：

- 运动检测或运动补偿。
- 静态区域强降噪，运动区域弱降噪。
- 暗部增强后特别注意色噪。
- 帧间参数平滑，避免降噪强度闪烁。
- 和编码器协同，减少背景噪声码率。

FastDVDnet 提出不依赖显式 optical flow 的实时视频降噪思路；EMVD 这类低复杂度视频降噪工作则强调移动 SoC 上的实时和低内存需求。它们给视频 ISP 的启发是：多帧信息非常有价值，但必须为实时性和运动伪影付出设计成本。

## 5. EIS 与 rolling shutter：视频稳定不是简单裁切

电子防抖 EIS 常利用陀螺仪/IMU 或图像特征估计相机运动，然后对图像做 warp 和裁切。手机、运动相机、无人机、车载记录仪都依赖它。

难点是很多 CMOS 传感器是 rolling shutter：一帧图像不是同一时刻曝光，而是一行一行读出。相机在读出期间运动，会产生果冻、斜线弯曲、画面摆动。基于陀螺仪的视频稳定论文指出，陀螺仪能提供相机旋转信息，可用于实时防抖和 rolling shutter correction。

EIS 需要同步：

```text
gyro timestamp <-> sensor row exposure time <-> frame timestamp <-> ISP output frame
```

如果时间戳不准，稳定算法会补错方向。EIS 还会带来：

- 裁切视场损失。
- warp 插值模糊。
- 边缘填充问题。
- 运动物体局部扭曲。
- 与 OIS、AF、HDR、多帧降噪冲突。

## 6. HDR 视频、Log 和标准：视频不是照片 HDR

HDR 照片可以花更长时间融合和 tone mapping；HDR 视频必须连续、实时、稳定，还要符合显示和编码标准。

常见路线：

- 多曝光 HDR：短曝光保高光，长曝光保暗部。
- staggered HDR：传感器交错输出不同曝光。
- 单帧 HDR sensor：传感器内部扩展动态范围。
- Log 曲线：保留更多动态范围，供后期调色。
- HLG/PQ HDR：面向 HDR 显示和分发。

ITU-R BT.2100 定义了 HDR-TV 的关键参数，包含 PQ 和 HLG 两种转移函数，以及宽色域等要求。视频 ISP 要处理：

- 10-bit/12-bit 精度。
- BT.2020/P3/BT.709 色域转换。
- PQ/HLG/Log 曲线。
- HDR metadata。
- 高光 roll-off。
- 帧间 tone curve 稳定。
- 编码器对 HDR 格式的支持。

如果 HDR tone mapping 每帧独立计算，视频可能出现亮度抽动。视频 HDR 的关键是“亮得好看”和“连续稳定”同时成立。

## 7. 色度采样 4:2:0、4:2:2、4:4:4：格式影响画质和带宽

视频常用 YUV，因为人眼对亮度更敏感，对色度分辨率不如亮度敏感。色度采样表示色度信息保留多少：

- 4:4:4：亮度和色度同分辨率，质量高，带宽大。
- 4:2:2：水平方向色度减半，专业视频常见。
- 4:2:0：水平和垂直方向色度都减半，消费视频和编码常见。

视频 ISP 需要正确处理：

- RGB 到 YUV 的矩阵。
- full range / limited range。
- BT.601 / BT.709 / BT.2020。
- chroma siting。
- 色度下采样滤波。
- 高饱和边缘的色度 aliasing。

初学者常见错误是把 YUV 当成“RGB 换个名字”。一旦矩阵或 range 错，黑位、白位、肤色和饱和色都会出问题。

## 8. 实时 3D LUT 和色彩管理：视频调色要稳定且可编码

3D LUT 可以做复杂颜色映射，例如电影感、Log 转 Rec.709、HDR 预览、肤色保护、风格滤镜。视频里使用 LUT 要特别注意：

- 插值精度：17x17x17、33x33x33 等 LUT 精度影响平滑度。
- 带宽和 SRAM：LUT 太大可能增加访问压力。
- 时域一致性：切 LUT 或动态调 LUT 不能造成颜色跳变。
- 色域映射：BT.2020 到 BT.709/P3 要处理 gamut clipping。
- 编码友好：过强色彩和局部对比会增加码率或压缩伪影。

视频色彩管理的目标是从 capture 到 display 的完整一致性，不只是 ISP 内部调色。

## 9. 去拜耳纹、摩尔纹和 aliasing：视频里会动的伪影更刺眼

高频纹理、细密织物、建筑栏杆、LED 屏幕容易出现摩尔纹和伪色。照片里摩尔纹已经难看，视频里更麻烦，因为相机或物体运动时，摩尔纹会闪烁、滚动、跳动。

处理方向：

- 传感器和光学低通滤波。
- 更好的 demosaic。
- 频率检测和局部抑制。
- 视频时域一致性约束。
- 不把伪纹理过度锐化。

去拜耳纹不能只看单帧局部清晰度，还要看连续视频中伪影是否稳定、是否被编码器放大。

## 10. 编码前处理：视频 ISP 必须考虑 Codec

视频最终常进入 H.264/HEVC/AV1 编码器。ISP 输出会直接影响码率：

- 噪声大 -> 帧间残差大 -> 码率升高。
- 过锐 -> 高频多 -> ringing 和蚊噪增加。
- 亮度闪 -> 编码更难预测。
- 色度噪声 -> 压缩后很难看。
- ROI 不清楚 -> 码率分配不合理。

编码前处理包括：

- 轻量降噪。
- 适度锐化。
- 色度降噪。
- ROI 保细节。
- tone curve 稳定。
- 输出符合编码器格式和 range。

评价视频 ISP 时必须同时看编码前和编码后结果，不能只看 ISP 输出帧。

## 11. 低延迟和 buffer：视频体验是端到端的

视频链路延迟包括：

```text
sensor exposure/readout
-> ISP pipeline
-> multi-frame buffer
-> GPU/NPU/EIS/TNR
-> format conversion
-> encoder
-> mux/network/display
```

视频通话和直播特别敏感，多缓存几帧就会增加端到端延迟。拍照可以等，视频不能随便等。设计时要明确：

- TNR 缓存几帧。
- HDR 是否需要多曝光对齐。
- EIS 是否需要 lookahead。
- 编码器是否有 B 帧或重排序。
- 显示或网络是否有额外 buffer。

## 12. 常见失败现象速查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 亮度一跳一跳 | AE/tone curve 不平滑 | 看每帧曝光、gain、tone 参数 |
| 白平衡闪烁 | AWB 每帧硬切或混合光判断不稳 | 加时域平滑和肤色保护 |
| 夜间拖影 | TNR 历史权重过大 | 区分运动区域，降低融合强度 |
| 视频像果冻 | rolling shutter + EIS/gyro 同步不准 | 查 row time、gyro timestamp、warp |
| HDR 画面抽动 | 每帧 tone mapping 独立变化 | 平滑曲线和局部参数 |
| 色彩偏灰或偏黑 | YUV range/矩阵错误 | 检查 BT.709/2020、full/limited |
| 编码后蚊噪多 | 锐化过强或噪声多 | 调 sharpen、chroma NR、码率 |
| 摩尔纹闪烁 | demosaic/频率抑制不足 | 检查细纹理视频和时域稳定 |
| 长时间录制掉帧 | 热、DDR、编码器争用 | 记录温度、频率、带宽和帧时间 |

## 13. 最小可验证实验

实验 1：时域平均和拖影

```text
取一段静态背景中有人移动的视频。
做简单时域平均：
out = 0.3 * current + 0.7 * history
比较背景噪声和运动目标拖影。
```

实验 2：编码前锐化

```text
同一段视频做三种锐化强度。
用相同编码参数编码。
比较文件大小、边缘ringing、文字和头发细节。
```

实验 3：YUV range 检查

```text
准备灰阶和色条。
分别按 full range 和 limited range 解释。
观察黑位、白位、肤色和饱和色是否异常。
```

实验 4：HDR/tone 稳定性

```text
拍摄从室内转向窗外的片段。
逐帧记录亮度均值、tone curve、曝光和高光区域。
观察是否有突变。
```

实验 5：EIS 同步思维实验

```text
列出一帧视频的 sensor readout start/end、gyro timestamps、ISP output timestamp。
说明如果 gyro 晚 5ms 会造成什么稳定错误。
```

## 14. 学习优先级

必须掌握：

- 视频 ISP 的核心是时域一致性。
- TNR、EIS、HDR 视频、Log/HDR 标准、编码前处理都必须考虑延迟。
- 8K/高帧率/HDR 首先是带宽和功耗问题。
- YUV 色度采样、range、色彩矩阵会直接影响视频输出。
- 评价视频必须看连续片段和编码后结果。

了解即可：

- 每种 Log 曲线的完整数学公式。
- HDR10/HLG/Dolby Vision 的全部 metadata 细节。
- 所有视频编码器内部工具。
- 复杂视频降噪网络结构。

后面再回看：

- BT.2100、PQ、HLG、BT.2020。
- gyro-based video stabilization。
- FastDVDnet、EMVD、BasicVSR 等视频增强。
- rolling shutter correction。
- 编码前预处理和 VMAF/BD-rate。

## 15. 自测题

1. 为什么视频 ISP 不能逐帧独立调到最优？
2. TNR 为什么会带来拖影？
3. EIS 为什么需要 gyro 和 sensor timestamp 对齐？
4. rolling shutter 和 global shutter 的视频差异是什么？
5. HDR 视频为什么比 HDR 照片更难？
6. 4:2:0、4:2:2、4:4:4 的主要区别是什么？
7. 为什么过强锐化会让编码后画质更差？
8. 如果视频白平衡闪烁，你会检查哪些 metadata 和参数？
9. 为什么评价视频 ISP 要看编码后结果？
10. 如何设计一个视频 ISP 的回归测试集？

## 16. Gotchas：初学者最容易踩的坑

- 把照片算法直接搬到视频，不看时域稳定。
- 只抽帧看图，不播放连续片段。
- 只看 ISP 输出，不看编码后结果。
- TNR 只追求背景干净，忽略运动拖影。
- EIS 只看全局运动，不对齐 rolling shutter row time。
- HDR tone mapping 每帧独立，导致亮度抽动。
- YUV range 和色彩矩阵没写清，导致平台间偏色。
- 只测短视频，不测长时间热稳定。

## 17. 读完本章的验收标准

读完后，你应该能做到：

- 画出视频 ISP 从 RAW 到编码输入的完整链路。
- 用 8K60 RAW 数据量解释视频 ISP 的带宽压力。
- 解释 TNR、EIS、rolling shutter correction、HDR video、Log/HLG/PQ、编码前处理各自解决什么问题。
- 根据闪烁、拖影、果冻、偏色、码率异常等现象定位可能原因。
- 设计一套视频 ISP 测试，包括静态、运动、夜景、逆光、HDR、EIS、长时间录制和编码后质量。

## 18. 推荐资料、论文与工程资料

- FastDVDnet: Towards Real-Time Deep Video Denoising Without Flow Estimation：理解实时视频降噪和不显式依赖光流的多帧网络思路。
- EMVD: Efficient Multi-Stage Video Denoising with Recurrent Spatio-Temporal Fusion：理解移动 SoC 上低复杂度、低内存视频降噪。
- Digital Video Stabilization and Rolling Shutter Correction using Gyroscopes：理解 gyro-based EIS 和 rolling shutter correction 的基本思路。
- ITU-R BT.2100 / BT.2390：理解 HDR video、PQ、HLG、宽色域和 HDR 制作/交换参数。
- Blind Video Temporal Consistency：理解图像处理逐帧应用到视频时为什么会出现时域不一致。
- NVIDIA VPI：理解视频稳定、图像处理和异构后端的工程化接口。
- FFmpeg、x264/x265、SVT-AV1、VMAF：用于验证 ISP 输出进入编码器后的码率和视觉质量。
- Raspberry Pi Camera Algorithm and Tuning Guide / libcamera：理解真实相机视频 pipeline、3A 和 metadata 对齐。
## 可追溯资料入口

- [按章节映射的参考资料](../research_bibliography.md#按章节映射的一手入口)
- [来源、证据等级与时效规范](../SOURCE_POLICY.md)
- 本章涉及的产品参数必须记录型号、版本、发布日期/访问日期和证据等级。

## 本章学习闭环

- 配套实验：[lab09-视频场景与系统指标.md](../labs/lab09-视频场景与系统指标.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter27-第27章：视频ISP专门优化.md)
- 项目落点：
  - [系统性能分析](../../camera_system_capstone/scripts/04_run_system_profile.py)
- [Stage 3 pipeline benchmark](../../stage3_cpp_isp/benchmarks/bench_pipeline.cpp)
- [Stage 4 设备流水线分析](../../stage4_deploy_isp/scripts/13_profile_device_pipeline.py)
- 原始资料：[原教程正文归档](../source_archive/chapter27-第27章：视频ISP专门优化.md)

导航：[上一章](./chapter26-第26章：安防监控ISP关键技术.md) · [下一章](./chapter28-第28章：AI-ISP融合架构.md) · [完整课程索引](../full_content_index.md)
