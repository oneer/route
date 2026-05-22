# 阶段 1：传统 ISP 与 RAW 基础学习路线

> **适用对象**：已有 Python / C++ / ISP Pipeline 工程经验，做过模块对齐、定点化、四通道改造和测试验证，但对 Sensor 物理、传统 ISP 模块原理、画质评价和调参逻辑还不够系统。
>
> **阶段周期**：6 周。
>
> **阶段目标**：能从真实 RAW / DNG 输入开始，独立完成一个 Python Soft-ISP Pipeline，并能解释每个模块的输入输出、物理意义、核心公式、参数影响、失败场景和验证方法。
>
> **阶段产出**：一个 `soft_isp_stage1/` 项目、一份实验报告、至少 5 张 RAW 样张的完整处理结果、每个模块的 Before / After 图、统计指标表和面试复述笔记。

---

## 0. 阶段一的正确学习姿势

你已经有 ISP 工程背景，所以阶段一不应该学成“照着教程写几个函数”。更合理的目标是把过去的工程经验升级成算法表达能力：

- 过去：我改过某个模块，让 Python 和 C++ 输出一致。
- 现在：我能解释这个模块为什么存在、处理什么数据域、参数怎么影响画质、怎么验证它没有引入副作用。

每个模块都按同一套模板学习：

1. **输入是什么**：RAW Bayer、linear RGB、sRGB、YUV，还是统计信息。
2. **输出是什么**：输出数据域是否改变，bit depth / range 是否改变。
3. **解决什么问题**：偏置、坏点、暗角、缺色、白平衡、色彩映射、非线性显示。
4. **核心假设是什么**：灰度世界、局部平滑、线性颜色变换、固定黑电平等。
5. **参数怎么调**：参数变大/变小会怎样，副作用是什么。
6. **怎么验证**：统计、ROI、图像对比、与 rawpy / LibRaw / Lightroom 输出对照。
7. **失败场景是什么**：低光、高光、纯色、大面积饱和、边缘纹理、混合光。

---

## 1. 最终项目结构

建议阶段一结束时形成下面这个项目。它不需要一开始就很漂亮，但每个脚本都要能运行，每个输出都要能解释。

```text
soft_isp_stage1/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                       # 少量 RAW / DNG 样张，不提交大文件
│   └── references/                # rawpy / Lightroom / LibRaw 输出参考
├── configs/
│   └── default.yaml               # black level、white level、bayer pattern 等参数
├── soft_isp/
│   ├── io.py                      # RAW 读取、metadata 解析
│   ├── stats.py                   # 四通道统计、histogram、饱和检测
│   ├── blc.py
│   ├── dpc.py
│   ├── lsc.py
│   ├── demosaic.py
│   ├── awb.py
│   ├── ccm.py
│   ├── tone.py                    # gamma / simple tone mapping
│   ├── metrics.py                 # PSNR / SSIM / DeltaE / 基础统计
│   └── pipeline.py
├── scripts/
│   ├── 01_inspect_raw.py
│   ├── 02_run_pipeline.py
│   ├── 03_compare_reference.py
│   └── 04_make_report_figures.py
├── notebooks/
│   ├── 01_raw_statistics.ipynb
│   ├── 02_module_ablation.ipynb
│   └── 03_iq_comparison.ipynb
└── reports/
    ├── stage1_report.md
    └── figures/
```

**项目验收标准**：

- 输入一张真实 RAW / DNG，能输出可正常观看的 RGB 图。
- 每个模块可以单独打开/关闭，并保存中间结果。
- 至少处理 5 张不同场景 RAW：日光、室内、低光、高动态范围、纯色/纹理场景。
- 每张图都有 rawpy 或 Lightroom 参考输出。
- 能指出你自己的 pipeline 和参考输出之间至少 5 类差异，并能解释可能原因。

---

## 2. 公开资源调研与使用方式

### 2.1 课程 / 讲义

| 资源 | 链接 | 阶段一怎么用 |
|---|---|---|
| Stanford EE367 / CS448I Computational Imaging | https://stanford.edu/class/ee367/ | 重点看 digital cameras / ISPs、denoising、HDR、inverse problems。用它建立成像系统和 ISP 的宏观框架。 |
| Stanford EE367 图像处理管线课件 | https://stanford.edu/class/ee367/slides/lecture4.pdf | 重点看相机传感器、RAW 到 RGB、ISP 模块顺序和 pipeline 直觉。 |
| UC Berkeley CS194-26 Computational Photography | https://www2.eecs.berkeley.edu/Courses/CS194_1871/ | 重点看 cameras and image formation、HDR、computational photography 项目思路。 |
| Cornell CS6640 Computational Photography Pipeline | https://www.cs.cornell.edu/courses/cs6640/2012fa/slides/07-Pipeline.pdf | 用来补数字相机 pipeline 的整体视角。 |

**使用要求**：课程不需要完整刷。每看一份课件，都必须转化成一页笔记：这份资料解决了我哪个问题？能不能用于我的 Soft-ISP 项目？

### 2.2 论文 / 技术论文

| 论文 | 链接 | 阶段一怎么用 |
|---|---|---|
| A Software Platform for Manipulating the Camera Imaging Pipeline | https://karaimer.github.io/camera-pipeline/ | 必读。理解为什么要做可控 ISP pipeline，以及修改单个模块如何影响最终图像。 |
| Practical ISP / Camera Pipeline 相关论文 PDF | https://karaimer.github.io/camera-pipeline/paper/Karaimer_Brown_ECCV16.pdf | 重点看 pipeline 结构和模块关系，不需要抠全部实验。 |
| Burst photography for high dynamic range and low-light imaging on mobile cameras | https://research.google/pubs/pub45586 | 阶段一只读 introduction 和 pipeline 相关部分，理解为什么 Google HDR+ 从 RAW burst 做处理。 |
| Learning to See in the Dark | https://cchen156.github.io/paper/18CVPR_SID.pdf | 阶段一只看 RAW 数据、pack、短曝光/长曝光数据定义，为后续 AI-ISP 做铺垫。 |

**阅读模板**：

```text
论文解决的问题：
输入数据域：
输出数据域：
pipeline 中涉及的模块：
对阶段一项目有用的点：
暂时不用深挖的点：
```

### 2.3 开源项目 / 工具库

| 项目 | 链接 | 阶段一怎么用 |
|---|---|---|
| OpenISP | https://github.com/cruxopen/openISP | 作为 Soft-ISP 项目结构参考，重点看模块拆分、配置和 pipeline 组织方式。 |
| Infinite-ISP | https://github.com/10x-Engineers/Infinite-ISP | 作为更完整的 ISP pipeline 参考，重点看模块命名、输入输出和文档结构。 |
| rawpy | https://pypi.org/project/rawpy/ | 用于读取 RAW / DNG，生成参考输出，理解 LibRaw 参数。 |
| rawpy API 文档 | https://letmaik.github.io/rawpy/api/rawpy.RawPy.html | 查 `raw_image_visible`、`postprocess`、metadata、黑白电平等接口。 |
| OpenCV Bayer / color conversion | https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html | 用 `cv2.cvtColor` / Bayer conversion 做 demosaic baseline，对照自己的 bilinear 实现。 |
| scikit-image metrics | https://scikit-image.org/docs/stable/api/skimage.metrics.html | 用 `peak_signal_noise_ratio`、`structural_similarity` 做基础指标。 |
| Colour Science for Python | https://www.colour-science.org/ | 用于色彩空间、DeltaE、色温和色彩科学相关实验。 |

**使用要求**：开源项目不要一开始大段照搬。先自己实现最小版本，再用开源项目对照你的模块顺序、参数设计和结果。

### 2.4 数据集 / RAW 样张

| 数据 | 链接 | 阶段一怎么用 |
|---|---|---|
| MIT-Adobe FiveK Dataset | https://data.csail.mit.edu/graphics/fivek/ | 首选。包含大量 DNG 和专家修图输出。阶段一选 5～10 张即可，不要下载全量大包。 |
| Google HDR+ Burst Photography Dataset | https://www.hdrplusdata.org/dataset.html | 可选。阶段一只选单帧 DNG 做 RAW 分析；HDR / burst 留到后续阶段。 |
| SID Dataset | https://cchen156.github.io/ | 可选。阶段一用于观察低光 RAW，暂不训练模型。 |

**样张选择标准**：

- 一张白天室外正常曝光。
- 一张室内暖光。
- 一张低光高 ISO。
- 一张高动态范围，包含亮窗/天空和暗部。
- 一张有高频纹理或边缘，例如建筑、文字、布料。

### 2.5 图书 / 参考书

| 图书 | 链接 | 阶段一怎么用 |
|---|---|---|
| Digital Image Processing, Gonzalez & Woods | https://www.pearson.com/store/p/digital-image-processing/P200000003224 | 查基础图像处理、空间滤波、频域、色彩和图像增强。不要从头通读。 |
| The Essential Guide to Image Processing, Bovik | https://books.google.com/books/about/The_Essential_Guide_to_Image_Processing.html?id=6TOUgytafmQC | 查图像质量、滤波、去噪、感知评价相关章节。 |
| Color Imaging: Fundamentals and Applications | https://www.routledge.com/Color-Imaging-Fundamentals-and-Applications/Reinhard/p/book/9780429062544 | 查色彩成像、色彩空间、色彩校正和视觉感知。 |

---

## 3. 六周详细路线

### Week 0.5：环境、数据和项目骨架

**目标**：先把项目跑起来，不在环境上拖太久。

**学习内容**：

- Python 项目结构。
- RAW / DNG 文件读取方式。
- 基础依赖：NumPy、OpenCV、rawpy、matplotlib、scikit-image、colour-science、PyYAML。

**具体步骤**：

1. 新建 `soft_isp_stage1/` 项目目录。
2. 创建虚拟环境，安装依赖。
3. 准备 5 张 RAW / DNG 样张。
4. 写 `scripts/01_inspect_raw.py`，能读取 RAW 并打印：
   - 图像尺寸
   - dtype
   - black level
   - white level
   - Bayer pattern
   - raw min / max / mean / std
5. 用 rawpy 生成一个默认参考图和一个线性参考图。

**建议命令**：

```bash
pip install numpy opencv-python rawpy matplotlib scikit-image colour-science pyyaml imageio
```

**掌握标准**：

- 你能解释 `raw.raw_image`、`raw.raw_image_visible`、`raw.postprocess()` 的区别。
- 你知道为什么参考输出要保存一份默认 sRGB、一份线性输出。
- 你能说清楚这阶段项目不追求商业 ISP 效果，而追求数据流可解释。

**交付物**：

- `requirements.txt`
- `scripts/01_inspect_raw.py`
- 5 张样张的 metadata 表格

### Week 1：RAW / Sensor 数据直觉

**目标**：理解 RAW 数值和 Sensor 物理的关系。

**学习内容**：

- RAW 是 Bayer mosaic，不是普通灰度图。
- black level、white level、bit depth、saturation。
- R / Gr / Gb / B 四通道统计。
- shot noise 和 read noise 的直观区别。

**具体步骤**：

1. 实现 `split_bayer(raw, pattern)`，把 RGGB / BGGR / GRBG / GBRG 拆成四个通道。
2. 对每张 RAW 输出四通道统计：
   - min / max / mean / std
   - 1%、50%、99% 分位数
   - clipped pixel ratio
   - black-level-near pixel ratio
3. 画每个通道的 histogram。
4. 选 3 个 ROI：暗部、中间亮度、高光区域，比较四通道统计。
5. 写笔记：《RAW 域统计怎么看》。

**小实验**：

- 对同一张图，分别画扣黑电平前后的 histogram。
- 对比 Gr 和 Gb 的均值差异，观察是否存在通道不一致。
- 找一张过曝图，观察高光区域是否大量接近 white level。

**掌握标准**：

- 看到 RAW 直方图，能判断是否明显欠曝、过曝、黑电平异常。
- 能解释为什么 Gr / Gb 通常分开处理，而不是直接当一个 G。
- 能说明高 ISO 下噪声为什么更明显，但 shot noise 和 read noise 的来源不同。

**交付物**：

- `soft_isp/stats.py`
- `notebooks/01_raw_statistics.ipynb`
- `reports/week1_raw_statistics.md`

### Week 2：BLC / DPC / LSC 前端校正

**目标**：实现 ISP 前端的基础校正，理解它们为什么必须在 RAW 域做。

**学习内容**：

- BLC：黑电平扣除、归一化、clip。
- DPC：hot pixel、dead pixel、静态 defect map、动态检测。
- LSC：镜头暗角、颜色 shading、R/Gr/Gb/B 分通道 gain map。

**具体步骤**：

1. 实现 `black_level_correction(raw, black_level, white_level)`。
2. 实现简单 DPC：
   - 使用同色邻域 median 替换异常点。
   - 异常点检测避免跨 CFA 颜色直接比较。
3. 实现简化 LSC：
   - 先做径向 gain map。
   - 再扩展成 R / Gr / Gb / B 四通道 gain map。
4. 每个模块保存前后图和统计变化。
5. 做模块顺序实验：BLC 前后做 DPC / LSC，观察差异。

**小实验**：

- 手动注入 50 个 hot pixels，验证 DPC 是否能修掉。
- 把 LSC edge gain 从 1.0 调到 2.0，观察四角亮度和噪声变化。
- 对比全通道同一个 LSC gain map 与四通道独立 gain map 的偏色风险。

**掌握标准**：

- 能解释为什么 BLC 是很多模块之前的必要步骤。
- 能解释坏点检测为什么要考虑 Bayer 同色邻域。
- 能说明 LSC 会放大边缘噪声，因此不是“无脑提亮四角”。
- 能回答：LSC gain map 工程上如何标定？积分球 / 均匀光源 / 网格 LUT 各自作用是什么？

**交付物**：

- `soft_isp/blc.py`
- `soft_isp/dpc.py`
- `soft_isp/lsc.py`
- `reports/week2_frontend_correction.md`

### Week 3：Demosaic / AWB

**目标**：把 RAW mosaic 转成 RGB，并理解白平衡为何会改变颜色和噪声。

**学习内容**：

- Demosaic：bilinear、边缘伪彩、zipper artifact。
- OpenCV Bayer conversion 作为 baseline。
- AWB：gray world、white patch、简单 ROI 筛选。
- AWB gain 与通道噪声放大的关系。

**具体步骤**：

1. 自己实现 bilinear demosaic，不依赖 `scipy.zoom` 作为最终版本。
2. 用 OpenCV `cv2.cvtColor` 的 Bayer conversion 输出 baseline。
3. 对比自己的 demosaic 和 OpenCV 输出：
   - 平坦区域
   - 边缘区域
   - 高频纹理区域
4. 实现 gray world AWB。
5. 实现 white patch AWB。
6. 实现简单区域筛选：
   - 剔除过暗区域
   - 剔除饱和区域
   - 剔除颜色过于极端区域

**小实验**：

- 在大面积绿色场景上比较 gray world 是否失败。
- 在有镜面高光的图上比较 white patch 是否被误导。
- 对低光图提高 R/B gain，观察 chroma noise 是否更明显。

**掌握标准**：

- 能解释 Bayer pattern 选错为什么会导致明显偏色或颜色错位。
- 能说明 bilinear demosaic 的优点、缺点和典型伪影。
- 能解释 AWB 不是“让每张图都变白”，而是在估计光源和校正通道响应。
- 能回答灰度世界、白点法各自的失败场景。

**交付物**：

- `soft_isp/demosaic.py`
- `soft_isp/awb.py`
- `reports/week3_demosaic_awb.md`

### Week 4：CCM / Gamma / Tone Mapping

**目标**：把“能看见颜色”推进到“能解释色彩和显示映射”。

**学习内容**：

- 线性 RGB、camera RGB、sRGB、XYZ、Lab。
- CCM：3x3 矩阵、白平衡后再做色彩校正、色卡拟合思想。
- Gamma：线性光到显示编码。
- 简单 tone mapping：全局曲线、压高光、提暗部。

**具体步骤**：

1. 实现 `apply_ccm(rgb_linear, matrix)`。
2. 使用默认 / 手工 CCM，观察色彩变化。
3. 使用 Colour Science 或 OpenCV 做 RGB ↔ Lab 转换实验。
4. 实现 sRGB gamma。
5. 实现简单 tone curve：
   - 线性
   - gamma
   - S-curve
6. 对比 rawpy 默认输出和自己的输出，分析色彩与亮度差异。

**小实验**：

- 同一张图分别使用 identity CCM、手工 CCM、rawpy camera WB 输出，对比偏色。
- 对一张高动态范围图使用不同 tone curve，观察高光压缩和暗部细节。
- 计算简单色块或人工 ROI 的 Lab 差异。

**掌握标准**：

- 能说明 CCM 应该作用在线性 RGB 上，而不是随意作用在 gamma 后图像上。
- 能解释 Gamma 和 Tone Mapping 不是一回事。
- 能说明为什么同一个 RAW 在 Lightroom、rawpy、你的 pipeline 中颜色会不同。
- 能回答 DeltaE 的作用：它衡量色彩差异，但不等于完整主观画质。

**交付物**：

- `soft_isp/ccm.py`
- `soft_isp/tone.py`
- `reports/week4_color_tone.md`

### Week 5：IQA / 模块消融 / 对比报告

**目标**：补上“如何证明结果变好”的能力。

**学习内容**：

- PSNR、SSIM、DeltaE、直方图、ROI 对比。
- 主观问题标签：偏色、伪彩、过曝、欠曝、暗部脏、过平滑、边缘彩边。
- 消融实验：关闭某个模块、改参数、改变顺序。

**具体步骤**：

1. 实现 `metrics.py`：
   - PSNR
   - SSIM
   - DeltaE
   - mean / std / histogram difference
2. 对 5 张样张建立报告表格：
   - rawpy 参考图
   - 你的输出图
   - 关键 ROI
   - 指标
   - 问题描述
3. 做模块消融：
   - no BLC
   - no LSC
   - no AWB
   - no CCM
   - no Gamma
4. 写每个消融造成的画质问题。

**小实验**：

- PSNR 高但主观差的例子：亮度整体偏暗但结构相似。
- SSIM 高但颜色明显偏的例子。
- AWB 修正后整体更自然，但局部噪声被放大的例子。

**掌握标准**：

- 能解释 PSNR / SSIM / DeltaE 各自看什么。
- 能用 ROI 图说明问题，而不是只给一张全图。
- 能根据消融结果说明每个模块的必要性。
- 能写一份像工程评审文档一样的画质对比报告。

**交付物**：

- `soft_isp/metrics.py`
- `scripts/03_compare_reference.py`
- `reports/week5_iqa_ablation.md`

### Week 6：完整 Pipeline 收尾与面试化表达

**目标**：把代码、实验、解释整理成可以放进作品集和面试讲述的阶段成果。

**学习内容**：

- Pipeline 配置化。
- 中间结果保存。
- README 写法。
- 面试问题整理。

**具体步骤**：

1. 整理 `pipeline.py`，支持通过配置打开/关闭模块。
2. 整理 `README.md`：
   - 项目目标
   - Pipeline 图
   - 运行方式
   - 样张结果
   - 指标表
   - 已知问题
3. 写 `reports/stage1_report.md`：
   - 数据集
   - 模块实现
   - 对比结果
   - 消融实验
   - 失败案例
   - 下一阶段计划
4. 准备 10 个面试问题和自己的答案。

**掌握标准**：

- 能在 5 分钟内讲清完整 pipeline。
- 能在 20 分钟内展开讲一个模块，例如 AWB / Demosaic / CCM / LSC。
- 能现场解释一张失败图，指出可能来自哪个模块。
- 能把你过去的 Python/C++ 对齐经验和本阶段 Soft-ISP 项目联系起来。

**最终交付物**：

- 可运行项目：`soft_isp_stage1/`
- 阶段报告：`reports/stage1_report.md`
- 面试笔记：`reports/stage1_interview_notes.md`

---

## 4. 每个模块的掌握标准

| 模块 | 入门 | 掌握 | 面试可讲 |
|---|---|---|---|
| RAW 读取 | 能用 rawpy 读出 Bayer 数据 | 能解析 black/white level、Bayer pattern、四通道统计 | 能解释 RAW、linear RGB、sRGB 的区别 |
| BLC | 能扣黑电平并归一化 | 能解释黑电平来源和扣除顺序 | 能说明黑电平错误如何影响暗部和颜色 |
| DPC | 能修复简单 hot pixel | 能用同色邻域做坏点检测 | 能解释动态检测和静态 defect map 的差异 |
| LSC | 能做径向 gain map | 能做四通道独立 gain | 能解释标定、网格 LUT、边缘噪声放大 |
| Demosaic | 能实现 bilinear | 能对比 OpenCV baseline 和伪影 | 能解释 AHD / 方向自适应为什么更好 |
| AWB | 能实现 gray world / white patch | 能做简单 ROI 筛选 | 能解释混合光、纯色场景、饱和区域导致的失败 |
| CCM | 能应用 3x3 矩阵 | 能解释线性 RGB 和 Lab / DeltaE | 能说明 CCM、AWB、Gamma 的顺序关系 |
| Gamma / Tone | 能实现 sRGB gamma | 能做简单 S-curve | 能解释显示编码和动态范围压缩的区别 |
| IQA | 能算 PSNR / SSIM | 能做 ROI + 指标 + 主观标签 | 能解释指标和主观画质冲突 |

---

## 5. 阶段一面试问题清单

1. RAW 图像和普通 RGB 图像有什么区别？
2. Bayer 阵列为什么绿色像素更多？
3. black level 从哪里来？扣错会怎么样？
4. white level / saturation 对高光有什么影响？
5. DPC 为什么要看同色邻域？
6. LSC 为什么要分 R / Gr / Gb / B 四通道？
7. LSC 为什么可能放大边缘噪声？
8. Demosaic 的 bilinear 方法为什么会有伪彩？
9. AHD 比 bilinear 好在哪里？
10. AWB 的 gray world 在什么场景下失效？
11. white patch 为什么容易被镜面高光误导？
12. CCM 为什么要在线性 RGB 上做？
13. Gamma 和 Tone Mapping 有什么区别？
14. 为什么 rawpy / Lightroom / 自己的 pipeline 输出颜色不同？
15. PSNR 高但图像不好看可能是什么原因？
16. 如果图像偏绿，你会从哪些模块排查？
17. 如果暗部噪声很重，你会从哪些模块排查？
18. 如果边缘有彩边，可能和哪些模块有关？
19. 如果 Python 和 C++ 输出不一致，阶段一这些模块里最常见原因有哪些？
20. 你如何证明一个 ISP 模块改动没有引入副作用？

---

## 6. 阶段一结束后的自检

如果下面问题能回答清楚，阶段一就算真正完成：

- 我能不能从一张 RAW 的 metadata 和 histogram 判断它的基本曝光状态？
- 我能不能画出完整 RAW → RGB pipeline，并说明每一步数据域？
- 我能不能解释自己的输出为什么和 rawpy / Lightroom 不一样？
- 我能不能对 5 张不同场景图做模块消融，并说清每个模块的影响？
- 我能不能把 BLC / DPC / LSC / Demosaic / AWB / CCM / Gamma 中任意一个模块讲 10 分钟？
- 我能不能把过去做 Python/C++ 对齐的经验，和这些模块的数值误差来源联系起来？

---

## 7. 阶段一不要做什么

- 不要一开始追商业级画质。
- 不要直接照搬大型开源 ISP 的全部代码。
- 不要过早进入 AI 模型训练。
- 不要把时间花在复杂 C++ 架构上；阶段一先用 Python 建立算法直觉。
- 不要只看全图，要养成看 ROI、看 histogram、看统计的习惯。
- 不要只保存最终图，中间结果比最终图更能说明你是否理解 pipeline。

---

## 8. 推荐执行顺序摘要

```text
Week 0.5  环境和样张
  -> 能读取 RAW、保存 rawpy 参考图

Week 1    RAW / Sensor 数据统计
  -> 能看懂四通道统计和直方图

Week 2    BLC / DPC / LSC
  -> 能做 RAW 前端校正并解释参数影响

Week 3    Demosaic / AWB
  -> 能输出基本正常 RGB，理解伪彩和白平衡失败

Week 4    CCM / Gamma / Tone
  -> 能解释色彩校正和显示映射

Week 5    IQA / 消融 / 对比
  -> 能证明每个模块的作用和副作用

Week 6    项目报告 / 面试表达
  -> 能把阶段成果讲成一个完整项目
```
