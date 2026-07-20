# 第5章：ISP前端处理：光学缺陷校正


> 课程阶段：传统 ISP 与成像基础　|　难度：入门　|　优先级：核心
>
> 建议用时：2–3 小时阅读 + 1–2 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**区分并验证 shading、暗角、畸变和色差校正。**

## 1. 本章先解决“镜头为什么会让 RAW 不均匀”

第 4 章处理的是传感器和读出链路造成的原始数据偏差。第 5 章开始处理光学系统造成的问题。镜头不是一个理想的透明窗口，它会改变不同位置、不同颜色、不同入射角光线到达传感器的方式。

可以先把光学缺陷分成三类：

```text
亮度不均：画面中心亮，边缘暗，也就是 vignetting / lens shading
颜色不均：中心和边缘颜色不一致，也就是 color shading
几何不准：直线变弯、边缘拉伸，也就是 distortion
```

这些问题如果不在 ISP 前端校正，会继续影响：

- AWB：边缘颜色偏会污染白平衡统计。
- CCM：颜色矩阵无法同时修正中心和边缘色偏。
- Demosaic：边缘通道响应不均可能增加伪色。
- Denoise：边缘补偿增益会把噪声一起放大。
- 机器视觉：畸变会影响测距、几何定位、双目匹配。

所以光学缺陷校正不是“把四角调亮一点”这么简单，而是让图像在空间位置上变得更均匀、更可解释。

## 2. 光学缺陷先分清：shading、vignetting、distortion、aberration

初学者容易把这些词混在一起。可以这样拆：

| 术语 | 中文直觉 | 影响什么 | 常见校正 |
|---|---|---|---|
| Vignetting | 暗角、渐晕 | 亮度随位置变化 | Lens Shading Correction / flat-field |
| Lens Shading | 镜头/传感器空间响应不均 | 亮度和颜色都可能变 | 分通道 gain map |
| Color Shading | 空间位置相关色偏 | R/G/B 比例随位置变化 | 分通道 LSC、AWB/CCM 配合 |
| Geometric Distortion | 几何畸变 | 直线变弯、形状变形 | remap / undistort |
| Chromatic Aberration | 色差 | 彩边、不同颜色位置错开 | 通道缩放/warp/边缘修正 |
| PRNU | 像素响应不均 | 像素/局部固定亮暗差异 | flat-field / gain correction |

关键区别：

```text
LSC/flat-field 是“像素值强度校正”
畸变/色差校正是“像素位置重映射”
```

一个改亮度，一个改几何位置；实现方式和副作用完全不同。

## 3. Lens Shading Correction：为什么中心和四角亮度不一样

### 3.1 暗角的来源

暗角可能来自多个原因：

- **自然渐晕**：离轴光线照到像面时，照度随角度下降，常用 cos^4 law 近似。
- **光学渐晕**：镜头结构遮挡离轴光束，大光圈更明显。
- **机械渐晕**：滤镜、遮光罩、镜筒等挡住边缘光线。
- **像素渐晕**：CMOS 微透镜和感光区域对斜入射光响应下降。
- **模组装配偏差**：光学中心和传感器中心不完全一致。

所以真实 shading 不一定是完美圆形，也不一定以图像中心为圆心。这就是为什么实际 ISP 常用二维网格 gain map，而不是只用一个简单径向公式。

### 3.2 LSC 的基本形式

最简单的 LSC 可以写成：

```text
corrected(x, y, c) = raw(x, y, c) * gain_map(x, y, c)
```

其中：

- `(x, y)` 是图像位置。
- `c` 是颜色通道，例如 R、Gr、Gb、B。
- `gain_map` 在边缘通常大于 1。

如果四角比中心暗 30%，直觉上四角可能需要乘大约：

```text
gain ≈ center_brightness / corner_brightness
```

但这只是直觉。真实系统还要考虑黑电平、噪声、通道差异和插值。

### 3.3 为什么 LSC 必须先减 black level

假设：

```text
raw = black + signal
```

如果直接做：

```text
wrong = raw * gain
```

那么 black 也被一起放大了。正确思路通常是：

```text
corrected = (raw - black) * gain
```

这和第 4 章的 offset/gain 顺序完全一致。LSC 是 gain 类校正，通常应建立在 BLC 之后。

## 4. Color Shading：为什么边缘可能偏绿、偏红或偏紫

亮度 shading 只看整体变暗；color shading 看的是不同颜色通道的空间响应不一致。

比如中心区域 R/G/B 比例正常，但四角：

```text
R 通道衰减更多 -> 四角偏青/绿
B 通道衰减更多 -> 四角偏黄
G 通道两个子通道 Gr/Gb 不一致 -> 可能出现棋盘或局部色偏
```

color shading 的来源包括：

- 镜头不同波长透过率随角度变化。
- 微透镜和 CFA 对斜入射光响应不同。
- IR filter 或 cover glass 的角度响应。
- sensor stack 与 lens chief ray angle 不匹配。

### 为什么 color shading 很麻烦

AWB 通常根据全图或局部统计估计光源颜色。如果边缘本身因为光学原因偏色，AWB 可能误以为光源变了。CCM 是全局颜色矩阵，也很难同时修正中心和四角不同的色偏。

所以 color shading 最好在 RAW 域或早期 RGB 域用分通道 gain map 先处理。

## 5. Flat-field 与 LSC 的关系

flat-field correction 是更通用的概念：通过拍摄均匀光场，估计系统的空间响应不均。

一个基础公式是：

```text
corrected = (raw - dark) / (flat - dark) * mean(flat - dark)
```

而 ISP 里的 LSC 可以看作面向镜头/传感器通道响应的实时 flat-field correction，只是工程上通常会：

- 用稀疏网格而不是 per-pixel map。
- 分通道存储 R/Gr/Gb/B gain。
- 用双线性插值生成每个像素 gain。
- 对不同色温、焦距、光圈、sensor mode 使用不同表。
- 限制最大 gain，避免边缘噪声过度放大。

## 6. Gain Map 如何标定

一个基础 LSC 标定流程：

1. 固定镜头、传感器、焦距、光圈和 sensor mode。
2. 拍摄均匀光源，例如积分球、均匀灯箱、均匀白板。
3. 拍 dark frame，先估计黑电平和暗信号。
4. 对 flat frame 做 black/dark correction。
5. 分 R/Gr/Gb/B 通道计算低频响应图。
6. 用中心或全图均值归一化，得到 gain map。
7. 对 gain map 平滑，去掉噪声和局部污点。
8. 量化成硬件或 ISP 可用的 grid table。
9. 用新场景验证过补、欠补、色偏和噪声放大。

### 为什么不能直接拿一张白墙就标定

普通白墙可能不均匀，照明也可能不均匀。这样得到的 gain map 会把照明不均误认为镜头 shading。论文 “Camera Shading Calibration Using a Spatially Modulated Field” 的价值就在于讨论如何在不完美照明场中估计相机 shading。工业和实验室通常会用更受控的平场条件。

## 7. LSC 的副作用：补亮四角也补亮噪声

LSC 经常需要在四角乘较大 gain。问题是：

```text
signal 被放大
noise 也被放大
```

所以四角校正后亮度均匀了，但噪声可能更明显。尤其在低照、高 ISO、短曝光、边缘暗角严重时，LSC 会让边缘噪声变得刺眼。

这带来几个工程策略：

- 限制最大 gain。
- LSC 后根据位置调整降噪强度。
- 低照模式下减少 LSC 强度，避免边缘噪声爆炸。
- 对亮度 shading 和 color shading 分开处理。
- 在机器视觉场景中，有时宁可保留轻微暗角，也不要过度放大噪声。

## 8. 几何畸变：不是亮度问题，而是位置问题

镜头畸变会让图像中本应是直线的结构变弯。常见类型：

- Barrel distortion：桶形畸变，广角镜头常见，直线向外鼓。
- Pincushion distortion：枕形畸变，直线向内收。
- Tangential distortion：镜头和传感器不完全平行或装配偏差导致。
- Fisheye distortion：超广角/鱼眼镜头的强畸变。

OpenCV 的相机标定模型常用径向和切向畸变参数：

```text
x_distorted = x * (1 + k1*r^2 + k2*r^4 + k3*r^6) + tangential_terms
y_distorted = y * (1 + k1*r^2 + k2*r^4 + k3*r^6) + tangential_terms
```

初学者不用先背公式，但要理解：

```text
畸变校正 = 给输出图每个像素找回输入图中应该采样的位置
```

也就是 remap。

## 9. 畸变校正的工程问题

畸变校正看起来只是几何变换，但对 ISP 很重：

- 需要查 remap table 或计算畸变模型。
- 输出像素通常对应输入的非整数坐标，需要插值。
- 边缘区域可能没有有效输入，需要裁切或填充。
- 访问模式不再是简单顺序流，缓存压力变大。
- 如果在 Bayer RAW 域做，要考虑 CFA 对齐；如果在 RGB/YUV 域做，计算和带宽更大。

常见实现方式：

| 方法 | 优点 | 缺点 |
|---|---|---|
| 多项式实时计算 | 参数少，灵活 | 计算复杂 |
| remap LUT | 速度快，适合硬件 | 存储大 |
| coarse grid + interpolation | 存储和精度折中 | 插值误差 |
| 鱼眼专用模型 | 适合广角 | 模型复杂，边界处理难 |

## 10. 色差 Chromatic Aberration

色差来自不同波长光线在镜头中的折射和聚焦差异。常见表现：

- 高对比边缘出现紫边、绿边、红蓝边。
- 画面边缘比中心更明显。
- R/G/B 通道边缘位置不完全对齐。

可以分成：

- Longitudinal chromatic aberration：不同颜色焦点前后位置不同，表现为焦外色边。
- Lateral chromatic aberration：不同颜色在图像平面上的放大率不同，边缘通道错位。

ISP 更常处理的是 lateral CA：通过对 R/B 通道相对 G 通道做缩放、位移或 warp，让边缘对齐。

## 11. 光学缺陷校正应该放在 pipeline 哪个位置

不同校正适合的位置不同：

| 校正 | 常见位置 | 原因 |
|---|---|---|
| LSC / color shading | BLC 后、demosaic 前较常见 | Bayer 域可分通道补偿，带宽低 |
| PRNU / flat-field | BLC/dark 后 | gain 类校正需要先减 offset |
| 几何畸变 | RGB/YUV 域或专用硬件路径 | 需要重采样，Bayer 域要小心 CFA 对齐 |
| 色差校正 | demosaic 后更常见 | 需要比较/移动颜色通道 |
| 鱼眼矫正 | 多在 RGB/YUV 或 CV 前处理 | 几何 remap 强，依赖应用视场 |

### 为什么 LSC 常在 demosaic 前

RAW Bayer 仍然保留通道采样结构，LSC 可以对 R/Gr/Gb/B 分别做 gain。这样带宽低，且能在颜色重建前先消除空间不均。

### 为什么几何畸变不总在 RAW 域做

RAW 域 remap 会破坏 Bayer pattern 的规则位置关系。除非有专门设计，否则更常见是在 demosaic 后或专用几何校正模块中处理。

## 12. 多光源和色温对 LSC 的影响

LSC 不一定只和位置有关，也可能和光源光谱有关。因为不同颜色通道和不同入射角响应不同，换光源后 color shading 可能变化。

例如：

- 日光下四角略偏绿。
- 钨丝灯下四角偏色方向不同。
- LED 光源因为谱线不连续，某些颜色通道响应更怪。

所以高级系统可能有：

- 多组 LSC table，按色温插值。
- AWB 与 LSC 联动。
- ALSC，Automatic Lens Shading Correction，动态估计或修正 shading。

但 ALSC 有风险：如果把真实场景的亮度变化误认为 shading，会过度校正。因此 ALSC 通常需要场景判断和平滑策略。

## 13. 最小可验证实验

### 实验 1：平场观察暗角和 color shading

拍一张均匀白墙或均匀光源，先减 black/dark，然后：

- 分别显示 R、Gr、Gb、B 四个通道。
- 计算中心和四角平均值。
- 画出每个通道的响应热力图。

观察：

- 四角是否都变暗？
- R/B/G 哪个通道衰减更明显？
- Gr 和 Gb 是否一致？

### 实验 2：构造简单径向 LSC

构造一个径向 gain：

```text
gain(r) = 1 + a * r^2
```

尝试不同 `a`：

- `a` 太小：欠补，四角仍暗。
- `a` 合适：亮度较均匀。
- `a` 太大：四角过亮，噪声明显。

输出中心、边缘、四角 crop。

### 实验 3：LSC 前后噪声比较

在低照图上应用强 LSC，比较：

- 中心暗部噪声
- 四角暗部噪声
- LSC 前后四角 SNR 是否变差

结论：校正亮度均匀性和保持边缘噪声之间存在 tradeoff。

### 实验 4：OpenCV 棋盘格畸变校正

使用棋盘格图片做 OpenCV camera calibration：

- 标定内参和畸变系数。
- undistort 一张图。
- 观察直线是否变直。
- 观察边缘是否裁切或拉伸。

重点不是背公式，而是理解畸变校正是 remap + interpolation。

### 实验 5：色差观察

找高对比边缘，例如黑白边缘、树枝天空边缘。放大四角区域观察：

- 是否有紫边/绿边？
- R/B 通道边缘是否相对 G 通道偏移？
- 中心和边缘色差强度是否不同？

## 14. 常见错误现象速查表

| 现象 | 可能原因 | 优先检查 |
|---|---|---|
| 四角仍然偏暗 | LSC gain 不够 | flat field、gain map |
| 四角过亮 | LSC 过补 | gain 限幅、中心归一化 |
| 四角噪声很重 | gain 放大噪声 | 低照策略、边缘降噪 |
| 四角偏绿/偏紫 | color shading 未校正 | 分通道 gain map、AWB 统计 |
| 中心正常边缘颜色怪 | LSC/CCM/AWB 未联动 | 色温相关 LSC |
| 直线弯曲 | 几何畸变 | 标定参数、remap |
| undistort 后边缘拉伸 | 视场裁切/插值 | new camera matrix、crop |
| 高对比边缘有紫边 | 色差 | R/B 通道对齐 |

## 15. 常见误区

- **误区 1：LSC 就是把四角调亮。**  
  不完整。LSC 还要处理通道差异、color shading、噪声放大和不同光源条件。

- **误区 2：flat field 不需要先减 dark。**  
  错。offset 没去掉，gain map 会把黑电平也当响应差异。

- **误区 3：畸变校正和 LSC 是一类东西。**  
  错。LSC 改像素强度，畸变校正改采样位置。

- **误区 4：LSC 越强越好。**  
  不一定。强补偿会放大边缘噪声，也可能造成过补。

- **误区 5：一张 LSC 表适合所有光源、焦距和模式。**  
  实际可能需要按色温、焦距、光圈、sensor mode 插值或切换。

## 16. 读完本章应该达到的标准

读完本章后，应该能做到：

- 解释 vignetting、lens shading、color shading、distortion、chromatic aberration 的区别。
- 说出 LSC 为什么通常要在 BLC 后执行。
- 用 flat field 推导一个基础 gain map。
- 解释 LSC 为什么会放大边缘噪声。
- 说明几何畸变校正为什么是 remap，而不是简单乘 gain。
- 判断色差、暗角、color shading 在图像上的不同表现。
- 设计一套平场标定和 OpenCV 畸变标定的最小实验。

## 17. 推荐资料与论文

- OpenCV Camera Calibration：适合学习径向畸变、切向畸变、相机内参、畸变参数和 undistort。  
  <https://docs.opencv.org/trunk/dc/dbb/tutorial_py_calibration.html>
- Raspberry Pi Camera Algorithm and Tuning Guide：适合学习 ALSC / lens shading table 在真实相机调参中的作用。  
  <https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf>
- “Flat-field and colour correction for the Raspberry Pi camera module”：适合学习低成本相机模组的 flat-field、lens shading table 和颜色校正。  
  <https://arxiv.org/abs/1911.13295>
- “Camera Shading Calibration Using a Spatially Modulated Field”：适合学习不完美平场条件下如何估计 shading。  
  <https://doi.org/10.1109/IVCNZ.2009.5378412>
- “Automatic Removal of Chromatic Aberration from a Single Image”：适合了解单图色差校正思路。  
  <https://doi.org/10.1109/CVPR.2008.4587741>
- “Chromatic Aberration Recovery on Arbitrary Images”：适合了解现代自动色差恢复方法。  
  <https://arxiv.org/abs/2110.04030>
## 补充自测题

1. 用一句话说明本章对象的输入、处理和输出。
2. 哪一个参数或前置假设最容易设置错误？错误图像现象是什么？
3. 设计一个最小实验，说明如何区分算法问题、输入契约问题和标定问题。
## 学习优先级

- **必须掌握**：本章学习结果、输入输出、关键失败现象和最小验证方法。
- **了解即可**：历史背景、少见硬件变种和暂时无法从公开资料验证的细节。
- **后面再回看**：需要真实 RAW、标定数据或硬件经验才能完整理解的内容。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab02-raw前端校正.md](../labs/lab02-raw前端校正.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter05-第5章：ISP前端处理：光学缺陷校正.md)
- 项目落点：
  - [LSC 实现](../../stage1_soft_isp/soft_isp/lsc.py)
- [LSC 实验脚本](../../stage1_soft_isp/scripts/14_apply_lsc.py)
- [标定工具](../../stage1_soft_isp/soft_isp/calibration.py)
- 原始资料：[原教程正文归档](../source_archive/chapter05-第5章：ISP前端处理：光学缺陷校正.md)

导航：[上一章](./chapter04-第4章：ISP前端处理：原始数据校正.md) · [下一章](./chapter06-第6章：ISP前端处理：像素级处理.md) · [完整课程索引](../full_content_index.md)
