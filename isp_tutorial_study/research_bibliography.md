# ISP 学习教程调研资料总表

这份资料表用于支撑 `full_chapters/` 下 35 章的初学者教程化改写。原则：不复制书籍、论文或网页原文；只引用来源、提炼概念，并把知识重新组织成本项目可学习、可验证的教程。

## 专业书籍与基础资料

- Junichi Nakamura, *Image Sensors and Signal Processing for Digital Still Cameras*. 适合建立“传感器 -> RAW -> ISP -> 输出”的完整系统视角。
- Rastislav Lukac, *Single-Sensor Imaging: Methods and Applications for Digital Cameras*. 适合学习 Bayer CFA、去马赛克、颜色重建和单传感器成像。
- Bernd Jähne, *Digital Image Processing*. 适合补图像滤波、噪声、边缘、频域和评价方法基础。
- Richard Szeliski, *Computer Vision: Algorithms and Applications*. 适合补多帧、配准、运动、HDR 和计算摄影基础。
- Charles Poynton, *Digital Video and HD: Algorithms and Interfaces*. 适合补 gamma、颜色编码、视频接口和显示链路。

## 标准、官方文档和工程资料

- EMVA 1288：图像传感器表征标准，用于学习噪声、灵敏度、动态范围、SNR、暗电流和 photon transfer。
  <https://www.emva.org/standards-technology/emva-1288/>
- Raspberry Pi Camera Algorithm and Tuning Guide：公开的 ISP tuning 文档，覆盖 AGC/AE、AWB、ALSC、CCM、denoise、sharpening 等模块。
  <https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf>
- libcamera：开源相机栈，可学习真实 ISP 控制算法、IPA、相机 pipeline handler 和调参结构。
  <https://libcamera.org/>
- Android Camera HAL：适合理解移动平台相机链路、metadata、3A 控制和应用接口。
  <https://source.android.com/docs/core/camera>
- OpenCV Image Processing 文档：适合快速验证 demosaic、颜色转换、滤波、几何变换等基础实验。
  <https://docs.opencv.org/>
- AMD/Xilinx Vitis Vision Library：适合学习 HLS/FPGA 视觉模块、ISP pipeline、demosaic、AWB、HDR、LTM 等硬件友好实现。
  <https://docs.amd.com/r/en-US/Vitis_Libraries/vision/>
- NVIDIA VPI：适合学习 GPU/PVA 等异构视觉处理模块和图像变换、去噪、畸变校正等加速思路。
  <https://docs.nvidia.com/vpi/>
- TI Jacinto/TDA4 VPAC/VISS/LDC 文档：适合学习车载视觉预处理加速器、VISS、LDC、MSC 和车载数据流。
  <https://www.ti.com/processors/automotive-processors/overview.html>

## 开源项目

- Infinite-ISP：Verilog ISP pipeline，适合学习 RTL 级 BLC、DPC、LSC、demosaic、AWB、color correction 等模块边界。
  <https://github.com/10x-Engineers/Infinite-ISP>
- openISP / cruxopen openISP：Python/C++ 风格的 ISP 学习实现，适合和本仓库 `stage1_soft_isp` 对照。
  <https://github.com/cruxopen/openISP>
- rawpy / LibRaw：RAW 解码与参考处理工具，适合建立和商业 RAW pipeline 的对照。
  <https://github.com/letmaik/rawpy>
  <https://www.libraw.org/>
- colour-science：色彩科学 Python 工具，适合学习色彩空间、色度图、白点、矩阵和 Delta E。
  <https://www.colour-science.org/>
- scikit-image：适合学习 PSNR、SSIM、滤波、颜色空间和图像处理基础实验。
  <https://scikit-image.org/>

## 论文与研究方向

- Schwartz et al., “DeepISP: Toward Learning an End-to-End Image Processing Pipeline.” 适合理解端到端学习型 ISP 的早期代表思路。
  <https://arxiv.org/abs/1801.06724>
- Ignatov et al., “Replacing Mobile Camera ISP with a Single Deep Learning Model.” 适合理解移动端神经 ISP 和真实数据训练难点。
  <https://arxiv.org/abs/2002.05509>
- “Learning Raw Image Denoising with Bayer Pattern Unification and Bayer Preserving Augmentation.” 适合学习 RAW denoise、Bayer pattern 和真实噪声建模。
  <https://arxiv.org/abs/1904.12945>
- “FastDVDnet: Towards Real-Time Deep Video Denoising Without Flow Estimation.” 适合学习视频时域降噪和实时性取舍。
  <https://arxiv.org/abs/1907.01361>
- Debevec and Malik, “Recovering High Dynamic Range Radiance Maps from Photographs.” HDR 多曝光融合经典论文。
  <https://www.pauldebevec.com/Research/HDR/>
- Mertens et al., “Exposure Fusion.” 适合学习无需显式 HDR radiance map 的多曝光融合直觉。
  <https://doi.org/10.1111/j.1467-8659.2007.01071.x>
- “Learning to See in the Dark.” 适合学习低照 RAW 到 RGB 图像恢复任务。
  <https://arxiv.org/abs/1805.01934>
- “HDRNet: Deep Bilateral Learning for Real-Time Image Enhancement.” 适合学习实时图像增强、局部映射和移动端部署。
  <https://arxiv.org/abs/1707.02880>

## 本项目内对照

- `stage1_soft_isp/`：传统 ISP pipeline 的学习和实验对照。
- `stage2_ai_isp/`：AI 图像恢复、denoise baseline、训练循环和评估指标对照。
- `study-roadmap/`：阶段化学习路线对照。

## 按章节映射的一手入口

以下映射优先选择标准、官方文档、作者论文和项目主页。推荐资料列表中的书名或论文名应回链到本表，避免只有名称没有 URL。

| 章节 | 主题 | 推荐一手入口 |
|---|---|---|
| 1–3 | 传感器、RAW、接口 | [EMVA 1288](https://www.emva.org/standards-technology/emva-1288/)、[MIPI CSI-2](https://www.mipi.org/specifications/csi-2)、[libcamera](https://libcamera.org/) |
| 4–7 | RAW 前端、LSC、DPC、Demosaic | [Raspberry Pi Camera Algorithm and Tuning Guide](https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf)、[Vitis Vision](https://docs.amd.com/r/en-US/Vitis_Libraries/vision/) |
| 8–9 | 降噪/NLM | [NLM 原始论文](https://ieeexplore.ieee.org/document/1467423)、[IPOL NLM](https://www.ipol.im/pub/art/2011/bcm_nlm/)、[BM3D](https://pubmed.ncbi.nlm.nih.gov/17688213/) |
| 10、16 | 色彩与 3A | [CIE](https://cie.co.at/)、[ICC sRGB](https://www.color.org/chardata/rgb/srgb.pdf)、[colour-science](https://www.colour-science.org/) |
| 11–13、33 | 硬件、存储、后端 | [Vitis Vision](https://docs.amd.com/r/en-US/Vitis_Libraries/vision/)、[OpenROAD](https://theopenroadproject.org/)、[IEEE 1801/UPF](https://standards.ieee.org/standard/1801-2018.html) |
| 14–15 | HDR 与计算摄影 | [Debevec HDR](https://www.pauldebevec.com/Research/HDR/)、[Exposure Fusion](https://doi.org/10.1111/j.1467-8659.2007.01071.x)、[HDRNet](https://arxiv.org/abs/1707.02880) |
| 17–19 | 移动平台 | [Qualcomm Snapdragon](https://www.qualcomm.com/snapdragon/overview)、[MediaTek Dimensity](https://www.mediatek.com/products/smartphones/dimensity)、[Apple Newsroom](https://www.apple.com/newsroom/) |
| 20–22 | 车载 ISP | [TI Jacinto Imaging](https://www.ti.com/lit/an/spracx9/spracx9.pdf)、[NVIDIA DRIVE](https://developer.nvidia.com/drive)、[ISO 26262 概览](https://www.iso.org/standard/68383.html) |
| 23–24 | 专业相机与 IQ | [ISO 12233](https://www.iso.org/standard/88626.html)、[LibRaw](https://www.libraw.org/)、[rawpy](https://github.com/letmaik/rawpy) |
| 25 | 消费电子与相机栈 | [Android Camera HAL](https://source.android.com/docs/core/camera)、[libcamera](https://libcamera.org/)、[HDRNet](https://arxiv.org/abs/1707.02880) |
| 26 | 安防与低照 | [Learning to See in the Dark](https://arxiv.org/abs/1805.01934)、[ONVIF](https://www.onvif.org/)、[FastDVDnet](https://arxiv.org/abs/1907.01361) |
| 27、31 | 视频与 Codec | [ITU-R BT.2100](https://www.itu.int/rec/R-REC-BT.2100/)、[FFmpeg](https://ffmpeg.org/documentation.html)、[AOM AV1](https://aomedia.org/av1/) |
| 28–29 | AI-ISP | [DeepISP](https://arxiv.org/abs/1801.06724)、[Replacing Mobile ISP](https://arxiv.org/abs/2002.05509)、[SIDD](https://www.eecs.yorku.ca/~kamel/sidd/) |
| 30 | GPU/异构 | [NVIDIA VPI](https://docs.nvidia.com/vpi/)、[CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)、[Halide](https://halide-lang.org/) |
| 32 | 验证与 IQ | [Accellera UVM](https://accellera.org/downloads/standards/uvm)、[Imatest documentation](https://www.imatest.com/docs/)、[scikit-image metrics](https://scikit-image.org/docs/stable/api/skimage.metrics.html) |
| 34 | 系统集成 | [Linux V4L2](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html)、[Android Camera](https://source.android.com/docs/core/camera)、[GStreamer](https://gstreamer.freedesktop.org/documentation/) |
| 35 | 新型传感器与趋势 | [Event-based Vision Survey](https://arxiv.org/abs/1904.08405)、[Quanta Image Sensor](https://ieeexplore.ieee.org/document/7809005)、[来源分级规范](SOURCE_POLICY.md) |

## 引用维护规则

- 产业章节的关键数字必须在句子附近给出来源，不只在章末列资料名。
- 论文结论不能直接写成某量产产品的内部实现。
- 链接失效时优先更新到同一机构的新页面；找不到时标为 `[待核实]`，不要悄悄换成低质量二手来源。
- 每条来源记录发布日期或版本；动态产品页另记访问日期。
