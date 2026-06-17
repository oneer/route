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
