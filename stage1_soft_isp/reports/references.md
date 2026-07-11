# Stage 1 参考文献与外部资料

本页记录教程中实际使用的规范、论文、官方 API 和开源项目。链接用于追溯定义与方法，不表示仓库有权再分发上游 PDF、数据或代码；第三方资产状态仍以根目录 `THIRD_PARTY_NOTICES.md` 为准。

## Week 1：RAW、DNG 与数据集

| 来源 | 本教程用途 |
|---|---|
| [Adobe Digital Negative (DNG) 与规范入口](https://helpx.adobe.com/camera-raw/digital-negative.html) | DNG 文件结构、RAW metadata、black/white level、颜色矩阵和方向字段的规范背景 |
| [rawpy RawPy API](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html) | `raw_image_visible`、Bayer metadata 和 `postprocess` 接口 |
| [MIT-Adobe FiveK Dataset](https://data.csail.mit.edu/graphics/fivek/) | T01–T14 DNG 的数据来源；逐文件登记见 `materials/raw_sample_manifest.md` |
| [Karaimer & Brown, A Software Platform for Manipulating the Camera Imaging Pipeline](https://karaimer.github.io/camera-pipeline/) | 可控 Camera Pipeline、模块化实验和处理顺序 |

## Week 2：前端校正

| 来源 | 本教程用途 |
|---|---|
| [OpenISP](https://github.com/cruxopen/openISP) | BLC、DPC、RAW 域降噪和模块接口的阅读参考；当前仓库需要继续核实确切 revision 与许可证 |
| [Infinite-ISP](https://github.com/10x-Engineers/Infinite-ISP) | 完整传统 ISP 模块命名、配置和文档组织参考 |

LSC 的学习版径向 gain 和 synthetic flat-field 实验不是来自某个相机的标定数据。真实 LSC 结论需要均匀光源、多帧平均、四通道 mesh 和残差验证。

## Week 3：Demosaic 与 AWB

| 来源 | 本教程用途 |
|---|---|
| [Malvar, He, Cutler, High-Quality Linear Interpolation for Demosaicing of Bayer-Patterned Color Images](https://www.microsoft.com/en-us/research/publication/high-quality-linear-interpolation-for-demosaicing-of-bayer-patterned-color-images/) | 从 bilinear 进入跨通道、梯度校正线性插值的进阶阅读 |
| [OpenCV Color Conversion Documentation](https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html) | Bayer conversion code 和 OpenCV demosaic baseline 的通道约定 |

Gray World、White Patch 和 Shades-of-Gray 在本教程中是可解释 baseline，不代表完整产品 AWB。评价应结合中性 ROI、饱和排除、失败场景和时序稳定性。

## Week 4：颜色、Tone 与显示编码

| 来源 | 本教程用途 |
|---|---|
| [Reinhard et al., Photographic Tone Reproduction for Digital Images](https://w3.impa.br/~lvelho/ip02/papers/reinhard/) | 全局 photographic tone mapping 的原始方法与适用问题 |
| [W3C sRGB 资料入口](https://www.w3.org/Graphics/Color/sRGB.html) | sRGB 编码、显示颜色空间和标准资料入口 |
| [Colour Science for Python](https://www.colour-science.org/) | RGB/XYZ/Lab、色彩矩阵和 DeltaE 实验工具 |

当前 CCM 是 metadata 的简化使用，不是 ColorChecker 拟合；当前相对 rawpy 的 DeltaE 也不是标准光源下的色卡 DeltaE。

## Week 5–6：图像质量评价

| 来源 | 本教程用途 |
|---|---|
| [Wang et al., Image Quality Assessment: From Error Visibility to Structural Similarity](https://doi.org/10.1109/TIP.2003.819861) | SSIM 的原始定义、结构相似性动机和 full-reference 前提 |
| [scikit-image metrics API](https://scikit-image.org/docs/stable/api/skimage.metrics.html) | 本项目 PSNR/SSIM 实现所调用的库接口和参数约定 |

PSNR、SSIM、MAD 和自然图 ROI proxy 只能回答限定问题。稀疏坏点、颜色准确性、主观观感、标准 MTF/SNR 和视频稳定性需要专门数据与协议。

## 引用规则

1. 报告第一次使用一个外部算法名时，应链接本页对应来源。
2. 必须区分“本仓库实测”“论文结论”“工程常识”和“待验证假设”。
3. 不从论文或上游项目复制长段文字、图片或代码；需要时用短摘要并保留来源。
4. 开源项目必须记录 URL、revision、许可证和本仓库实际使用方式。
5. 数据集必须记录来源、用途、文件 hash 和再分发状态。
