# 阶段 1 材料入口

这份清单按“今天就能开始”的优先级排。PDF 已下载到本地的会写明本地路径；网页、数据集和 API 文档保留原始链接。

## 0. 本地已经准备好的材料

| 类型 | 文件 | 先看哪里 |
|---|---|---|
| 论文 | `materials/papers/Karaimer_Brown_ECCV16_camera_pipeline.pdf` | pipeline 模块结构、可控 ISP 的意义 |
| 论文 | `materials/papers/Hasinoff_2016_HDRPlus_Burst_Photography.pdf` | RAW burst、低光、高动态 pipeline 思路 |
| 论文 | `materials/papers/Hasinoff_2016_HDRPlus_supplement.pdf` | HDR+ 细节补充，阶段 1 可先略读 |
| 论文 | `materials/papers/Chen_2018_Learning_to_See_in_the_Dark.pdf` | RAW 数据定义、低光短曝光/长曝光设定 |
| 讲义 | `materials/slides/Stanford_EE367_lecture4_camera_pipeline.pdf` | 相机传感器、RAW 到 RGB、ISP 顺序 |
| 讲义 | `materials/slides/Cornell_CS6640_07_Pipeline.pdf` | 数字相机 pipeline 整体视角 |
| 数据 | `data/raw/T01_a0006-IMG_2787.dng` | 水面细节 / 高频纹理 |
| 数据 | `data/raw/T02_a0008-WP_CRW_3959.dng` | 人像 / 肤色 / AWB |
| 数据 | `data/raw/T07_a0020-jmac_MG_6225.dng` | 大面积绿色 / AWB 失败案例 |
| 数据 | `data/raw/T10_a0026-kme_391.dng` | 隧道暗部 / 高对比 |
| 数据 | `data/raw/T14_a0040-_DSC5693.dng` | 蓝天建筑 / 边缘与颜色 |

## 1. 必读顺序

| 顺序 | 材料 | 目标 | 输出 |
|---:|---|---|---|
| 1 | Stanford lecture4 | 建立 RAW -> RGB pipeline 直觉 | 写一页 pipeline 顺序笔记 |
| 2 | Karaimer & Brown ECCV16 | 理解为什么要做可控 Soft-ISP | 写论文阅读模板 |
| 3 | FiveK starter DNG | 跑通 `01_inspect_raw.py` | 填 RAW 样张登记表 |
| 4 | Cornell pipeline slides | 补全数字相机模块视角 | 更新模块学习模板 |
| 5 | SID / HDR+ | 只看 RAW 数据和低光/HDR 背景 | 写“后续阶段问题清单” |

## 2. 课程 / 讲义

| 资源 | 链接 | 本地状态 | 阶段 1 怎么用 |
|---|---|---|---|
| Stanford EE367 / CS448I Computational Imaging | https://stanford.edu/class/ee367/ | 网页入口 | 看 digital cameras / ISPs、denoising、HDR、inverse problems。 |
| Stanford EE367 lecture4 | https://stanford.edu/class/ee367/slides/lecture4.pdf | 已下载：`materials/slides/Stanford_EE367_lecture4_camera_pipeline.pdf` | 重点看相机传感器、RAW 到 RGB、ISP 模块顺序。 |
| UC Berkeley Computational Photography | https://www2.eecs.berkeley.edu/Courses/CS194_1871/ | 网页入口 | 看 cameras and image formation、HDR、项目思路。 |
| Cornell CS6640 Pipeline Slides | https://www.cs.cornell.edu/courses/cs6640/2012fa/slides/07-Pipeline.pdf | 已下载：`materials/slides/Cornell_CS6640_07_Pipeline.pdf` | 补数字相机 pipeline 整体视角。 |

## 3. 论文

| 论文 | 链接 | 本地状态 | 阶段 1 怎么用 |
|---|---|---|---|
| A Software Platform for Manipulating the Camera Imaging Pipeline | https://karaimer.github.io/camera-pipeline/ | 项目页 | 必读，理解可控 ISP pipeline 的意义。 |
| Karaimer & Brown ECCV16 PDF | https://karaimer.github.io/camera-pipeline/paper/Karaimer_Brown_ECCV16.pdf | 已下载：`materials/papers/Karaimer_Brown_ECCV16_camera_pipeline.pdf` | 看 pipeline 结构、模块关系、实验方式。 |
| Burst Photography for HDR and Low-light Imaging | https://www.hdrplusdata.org/hdrplus.pdf | 已下载：`materials/papers/Hasinoff_2016_HDRPlus_Burst_Photography.pdf` | 阶段 1 只读 introduction 和 pipeline 相关部分。 |
| HDR+ Supplement | https://www.hdrplusdata.org/hdrplus_supp.pdf | 已下载：`materials/papers/Hasinoff_2016_HDRPlus_supplement.pdf` | 暂时不深挖，后续 HDR 阶段再看。 |
| Learning to See in the Dark | https://openaccess.thecvf.com/content_cvpr_2018/CameraReady/1981.pdf | 已下载：`materials/papers/Chen_2018_Learning_to_See_in_the_Dark.pdf` | 看 RAW 数据、pack、短曝光/长曝光定义。 |

## 4. 开源项目 / 工具库

| 项目 | 链接 | 阶段 1 怎么用 |
|---|---|---|
| OpenISP | https://github.com/cruxopen/openISP | 只参考模块拆分、配置、pipeline 组织，不照搬实现。 |
| Infinite-ISP | https://github.com/10x-Engineers/Infinite-ISP | 参考完整 ISP 模块命名和文档结构。 |
| rawpy | https://pypi.org/project/rawpy/ | 读取 RAW / DNG，生成参考输出。 |
| rawpy API | https://letmaik.github.io/rawpy/api/rawpy.RawPy.html | 查 `raw_image_visible`、`postprocess`、metadata 接口。 |
| OpenCV Color Conversion | https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html | 用 Bayer conversion 做 demosaic baseline。 |
| scikit-image metrics | https://scikit-image.org/docs/stable/api/skimage.metrics.html | 用 PSNR / SSIM 做基础指标。 |
| Colour Science for Python | https://www.colour-science.org/ | 做色彩空间、DeltaE、色温实验。 |

## 5. RAW 数据集

| 数据集 | 链接 | 本地状态 | 建议 |
|---|---|---|---|
| MIT-Adobe FiveK | https://data.csail.mit.edu/graphics/fivek/ | 已保存索引页：`materials/datasets/fivek_index.html`；已下载 5 张 DNG 到 `data/raw/` | 阶段 1 首选，先用 5 张跑通，不下载 50GB 全量包。 |
| Google HDR+ Dataset | https://www.hdrplusdata.org/dataset.html | 网页入口 | 可选。阶段 1 只挑单帧 DNG 看 RAW，不做 burst。 |
| SID Dataset | https://cchen156.github.io/ | 网页入口 | 可选。观察低光 RAW，暂不训练模型。 |
