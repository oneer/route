# ISP 算法工程师面试题：Week1-Week3

范围：RAW / Sensor 数据直觉、BLC、DPC、Demosaic、AWB，以及工程验证方法。

这份题不是背诵题，而是按 ISP 算法工程师面试的追问方式整理：每道题都要求能说明输入输出、数学假设、失败场景和工程验证。

## 调研资料

本题库结合了本项目 Week1-Week3 的实现和以下公开资料整理：

1. [OpenCV Color conversions / Bayer demosaicing 文档](https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html)
2. [LibRaw 官方仓库与 RAW 处理资料入口](https://github.com/LibRaw/LibRaw)
3. [rawpy 文档](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html)
4. [Karaimer and Brown, A Software Platform for Manipulating the Camera Imaging Pipeline, ECCV 2016](https://karaimer.github.io/camera-pipeline/)
5. [Hasinoff et al., Burst Photography for High Dynamic Range and Low-Light Imaging on Mobile Cameras, SIGGRAPH Asia 2016](https://hdrplusdata.org/hdrplus.pdf)
6. [Stanford EE367 Computational Imaging 课程资料](https://web.stanford.edu/class/ee367/)
7. [Cornell CS6640 Computational Photography 课程资料](https://www.cs.cornell.edu/courses/cs6640/)
8. [Gray World Assumption 相关介绍与颜色恒常性资料](https://en.wikipedia.org/wiki/Color_constancy)

## 一、RAW / Sensor / Metadata

### 1. RAW 和普通 RGB 图片的本质区别是什么？

**答案：**

普通 RGB 图片通常已经经过完整 ISP：BLC、Demosaic、AWB、CCM、Gamma、Tone Mapping、压缩等步骤，像素是面向显示或存储的三通道颜色值。

RAW 更接近传感器读数。常见 Bayer RAW 是二维单通道数组，每个像素只采 R/G/B 其中一种颜色响应。RAW 数值通常是线性光响应，还包含 black level 偏置、饱和上限、坏点、暗角、噪声等传感器和镜头特性。

面试中要强调：RAW 不是“更暗的 RGB”，而是另一个数据域。直接拿 RAW 当 RGB 处理会导致颜色、亮度和噪声判断全部错位。

### 2. 处理 DNG/RAW 时，最先要读哪些 metadata？

**答案：**

至少要读：

- `raw_image_visible` 的 shape 和 dtype
- `raw_pattern` / `color_desc`，用于推断 Bayer pattern
- `black_level_per_channel`
- `white_level` 或 `camera_white_level_per_channel`
- active area / visible area
- color matrix / camera white balance，如果后续要做颜色校正

这些 metadata 决定了后续处理的数值范围和空间排列。例如 Bayer pattern 错了，Demosaic 会直接串色；black level 错了，暗部和 AWB 都会带偏。

### 3. 为什么 RAW 四个通道 R / Gr / Gb / B 均值通常不同？

**答案：**

原因有几层：

1. 场景光源不是均匀白光，不同波段能量不同。
2. 传感器 R/G/B 滤色片透过率不同。
3. 人眼对亮度敏感，所以 Bayer 设计里 G 像素更多。
4. RAW 还没有做 AWB、CCM、Gamma。
5. 镜头阴影、角度响应、局部场景纹理也会影响通道均值。

Gr/Gb 理论上应接近，因为它们都是绿色，只是空间位置不同。如果 Gr/Gb 差很多，要怀疑 Bayer pattern、行列 offset、镜头阴影、局部纹理或读取区域不对。

### 4. black level 和 white level 分别代表什么？

**答案：**

black level 是相机认为“没有光时”的基线读数。由于传感器和读出电路有偏置，暗场不一定是 0。

white level 是有效信号上限，接近传感器饱和或相机定义的最大可靠值。超过或贴近 white level 的区域可能已经 clipping。

BLC 后有效白电平应变成：

```text
white_after = white_level - black_level
```

如果 black level 是 per-channel 或 per-Bayer-position 的，white_after 也应按位置计算。

### 5. Histogram 在 RAW 分析里能回答什么？

**答案：**

Histogram 回答的是像素数值分布：

- 大部分像素靠左：整体暗或黑电平附近像素多
- 右侧贴近 white level：高光可能饱和
- 分布跨度大：动态范围压力大
- 四通道曲线分离：说明 RGB 响应还没被白平衡和颜色校正统一

它不能直接回答“图像好不好看”，也不能单独判断最终颜色，因为 RAW 仍然是线性传感器域。

### 6. 为什么要做 ROI 分析，而不是只看全图统计？

**答案：**

全图统计会被大面积背景主导。例如一张大面积天空或草地的图，全图均值不代表主体区域。ROI 可以拆开看暗部、中间调、高光：

- 暗部 ROI：检查 black level、噪声和 BLC 后是否压到 0
- 中间调 ROI：适合比较 AWB 前后和颜色变化
- 高光 ROI：检查 clipping 和 tone mapping 风险

工程里很多问题只有局部可见，全图平均会掩盖问题。

### 7. p01、p50、p99 比 min/max 更有用的原因是什么？

**答案：**

min/max 容易被极少数异常点影响。一个坏点就能改变 max，一个黑点就能改变 min。

p01、p50、p99 是百分位统计，更能代表整体分布：

- p01：暗部下界
- p50：中位亮度
- p99：高光上界

在 RAW 分析里，p99 是否接近 white level 比 max 是否等于 white level 更稳定。

## 二、BLC 黑电平校正

### 8. BLC 的输入、输出和核心公式是什么？

**答案：**

输入：Bayer RAW、black level、white level、Bayer pattern 或 raw_pattern。

输出：扣除黑电平后的 Bayer RAW，仍然是单通道 Bayer。

公式：

```text
corrected = raw - black_level
corrected = clip(corrected, 0, white_level - black_level)
```

如果 black level 是 per-channel，就要按 Bayer 位置生成 black map，而不是用一个全局常数。

### 9. black level 为 0，是不是 BLC 可以不做？

**答案：**

数值上可以不改变结果，但工程流程里通常仍然保留 BLC 模块。原因是：

1. 统一 pipeline，方便不同相机和不同样张处理。
2. black level 为 0 是一个 identity case，可以验证模块没有破坏数据。
3. 后续代码可以统一假设输入已经在“有效光信号域”。

所以不是“删除 BLC”，而是当前样张中 BLC 的输出等于输入。

### 10. 如果 BLC 做错，会怎样影响后续模块？

**答案：**

如果 black level 没扣干净，暗部会带正偏置：

- Demosaic 会把偏置插值到 RGB 三通道
- AWB 会基于错误通道均值估计 gain
- DPC 阈值可能被暗部偏置影响
- Gamma/Tone 会把暗部偏置抬起来，导致黑位发灰

如果扣多了，会造成暗部被 clip 到 0，细节丢失。

### 11. 为什么 BLC 后要更新 white level？

**答案：**

因为信号域整体左移了。原始有效范围大致是：

```text
[black_level, white_level]
```

BLC 后变成：

```text
[0, white_level - black_level]
```

如果不更新 white level，后续归一化会把图压暗，或者错误判断饱和距离。

### 12. per-channel black level 和 scalar black level 有什么区别？

**答案：**

scalar black level 对所有像素扣同一个值。per-channel black level 对 Bayer 2x2 中不同位置扣不同值，例如 R、Gr、Gb、B 各有一个黑电平。

per-channel 更精确，因为不同读出通道或滤色片位置可能有不同偏置。实现时要根据 raw_pattern 生成和 RAW 同尺寸的 black map。

## 三、DPC 坏点校正

### 13. DPC 为什么通常放在 Demosaic 之前？

**答案：**

坏点是 Bayer RAW 上的孤立异常。如果不先修复，Demosaic 会把一个坏点影响扩散到周围多个 RGB 像素，甚至产生彩色斑点。

DPC 在 RAW 域做，影响范围小、定位准；Demosaic 后再修，异常已经扩散，更难区分是坏点还是真实纹理。

### 14. 为什么 DPC 不能直接拿上下左右像素比较？

**答案：**

Bayer RAW 相邻像素通常不是同一种颜色。例如 RGGB 中，一个 R 像素旁边可能是 G，而不是 R。不同颜色响应天然不同，直接比较会把正常颜色差异误判成坏点。

正确做法是按 Bayer pattern 提取同色平面，在同色邻域内比较。

### 15. 用 median 做坏点修复有什么优点？

**答案：**

median 对孤立极端值鲁棒。坏点通常表现为单个异常高或异常低像素，如果用 mean，均值会被异常值拉偏；用 median 更接近周围真实结构。

但 median 也有局限：强边缘、高频纹理、高光区域可能让真实像素看起来像异常点。

### 16. DPC 阈值为什么要结合 `min_delta` 和 MAD？

**答案：**

`min_delta` 提供绝对最低门槛，避免在平滑区域因为微小噪声误检。

MAD 是 Median Absolute Deviation，反映 residual 的鲁棒离散程度。使用：

```text
threshold = median(residual) + mad_k * MAD(residual)
```

可以让阈值随图像噪声水平变化。最终取：

```text
max(min_delta, robust_threshold)
```

兼顾固定门槛和自适应门槛。

### 17. DPC 的 false positive 和 false negative 分别是什么？

**答案：**

false positive：把正常像素误判为坏点。常见于强边缘、高光、纹理区域。后果是抹掉真实细节。

false negative：坏点没有被检测到。后果是坏点进入 Demosaic，扩散成彩色伪影。

工程上要在二者之间权衡。学习阶段通常宁愿保守一些，减少误修真实细节。

### 18. 产品级 DPC 和学习版 DPC 有什么区别？

**答案：**

学习版常用单帧局部统计检测，适合理解原理。

产品级 DPC 往往结合：

- 工厂暗场 / 亮场标定
- 固定坏点表
- 温度和曝光时间
- 动态坏点检测
- 与降噪、Demosaic 联合设计

产品级目标是稳定、低误检、跨场景一致，而不是只在一张图上看起来合理。

## 四、LSC 镜头阴影校正

### 19. LSC 解决什么问题？

**答案：**

LSC 解决 Lens Shading，也就是镜头导致的亮度和颜色位置相关不均匀。典型现象是画面中心亮、边缘暗，或者边缘有颜色偏移。

LSC 一般在 Demosaic 前的 RAW 域完成，对每个 Bayer 通道乘一个位置相关 gain map：

```text
raw_lsc(y, x) = raw(y, x) * gain_channel(y, x)
```

### 20. 为什么 LSC 会影响 AWB？

**答案：**

AWB 假设通道均值或灰色区域能代表光源颜色。如果镜头边缘有明显暗角或色偏，全图均值会混入位置相关偏差。这样 AWB 可能把镜头问题误认为光源颜色问题。

所以产品 pipeline 常在 AWB 前做 LSC。

### 21. 没有 flat-field 标定图时，能不能做 LSC？

**答案：**

可以做简化估计，但风险较高。

有 flat-field 图时，LSC gain map 可以比较可靠地从均匀光照图估计。没有 flat-field 时，可以尝试低频拟合、径向模型或多图统计，但容易把真实场景亮度变化误当成镜头暗角。

工程上要明确区分“标定 LSC”和“图像内容估计 LSC”。

## 五、Demosaic 去马赛克

### 22. Demosaic 的输入和输出是什么？

**答案：**

输入：BLC/DPC/LSC 后的单通道 Bayer RAW，shape 是 `(H, W)`。

输出：线性 RGB，shape 是 `(H, W, 3)`。

Demosaic 只补齐缺失颜色，不负责白平衡、颜色空间转换、Gamma 或 Tone Mapping。

### 23. 为什么 Bayer RAW 每个位置缺两个颜色？

**答案：**

Bayer 传感器每个像素上方有一个彩色滤光片，只允许 R/G/B 中一类光主要通过。于是每个位置只测得一个颜色响应。

对于 RGGB：

```text
R G
G B
```

R 位置只有 R，缺 G/B；G 位置只有 G，缺 R/B；B 位置只有 B，缺 R/G。

### 24. 用数学形式描述 Bayer 采样。

**答案：**

令完整彩色图像为：

```text
RGB(y, x) = [R(y, x), G(y, x), B(y, x)]
```

定义采样 mask：

```text
M_R, M_G, M_B
```

则 Bayer RAW 可写成：

```text
RAW = M_R * R + M_G * G + M_B * B
```

Demosaic 要估计：

```text
R_hat, G_hat, B_hat
```

其中很多值是估计值，不是传感器直接测得。

### 25. Bilinear demosaic 的核心公式是什么？

**答案：**

对每个颜色通道 C：

```text
C_hat = conv(RAW * M_C, K) / conv(M_C, K)
```

其中 `M_C` 是该颜色的采样 mask，`K` 是加权核。本项目使用：

```text
1 2 1
2 4 2
1 2 1
```

最后真实采样位置保留原值。

### 26. Bilinear demosaic 的优缺点是什么？

**答案：**

优点：

- 原理直观
- 实现简单
- 速度快
- 适合作为 baseline

缺点：

- 不判断边缘方向
- 边缘容易糊
- 高频纹理容易出现假彩色
- 可能有 zipper artifact

所以高质量 ISP 通常使用边缘感知或更复杂的 demosaic 方法。

### 27. Bayer pattern 搞错会发生什么？

**答案：**

如果 RGGB 被当成 BGGR，R 和 B 位置会反，颜色严重串通道。结果可能表现为整体偏色、红蓝颠倒、局部彩色伪影。

这是非常基础但很常见的 bug。验证方法包括：

- 从 metadata 推断 pattern
- 检查 R/G/B 统计是否合理
- 与 rawpy reference 对比
- 用小型合成 Bayer 图做单元测试

### 28. Demosaic 后为什么颜色仍然不对？

**答案：**

因为 Demosaic 只补缺失通道。它输出的是相机传感器线性 RGB，不是标准 sRGB。

后面还需要：

- AWB：校正光源色温
- CCM：相机 RGB 到标准颜色空间
- Gamma：线性光到显示编码
- Tone Mapping：动态范围压缩

因此不能用 Demosaic 输出直接评价最终颜色。

## 六、AWB 自动白平衡

### 29. AWB 的输入、输出和目标是什么？

**答案：**

输入：Demosaic 后的线性 RGB。

输出：乘过白平衡 gain 的线性 RGB。

目标：估计光源颜色或通道响应偏差，让中性物体的 R/G/B 更接近相等。

形式：

```text
R_awb = R * R_gain
G_awb = G * G_gain
B_awb = B * B_gain
```

通常会固定 G gain 为 1，让 R/B 向 G 对齐。

### 30. Gray World AWB 的假设和公式是什么？

**答案：**

假设：如果一张自然图像包含足够丰富的颜色，整张图的平均颜色应该接近灰色。

公式：

```text
R_gain = G_mean / R_mean
G_gain = 1
B_gain = G_mean / B_mean
```

本项目还排除了最暗和最亮部分，减少噪声和饱和区域影响。

### 31. Gray World 为什么会失败？

**答案：**

它依赖“平均颜色接近灰色”。如果场景本身不是灰色均衡，比如大面积草地、天空、红墙、舞台灯、海水，它会把真实颜色错误中和。

混合光源也会失败，因为一个全局 RGB gain 不能同时修正不同区域的光源。

### 32. AWB 为什么应该在线性 RGB 上做？

**答案：**

白平衡本质是光强比例校正，应该作用在线性光信号上。如果在 gamma 后的非线性 sRGB 上做，通道比例不再对应真实光强比例，gain 的物理意义会变差。

所以典型顺序是：

```text
Demosaic -> AWB -> CCM -> Gamma/Tone
```

### 33. AWB 和 CCM 有什么区别？

**答案：**

AWB 是每通道缩放：

```text
[R, G, B] * [r_gain, g_gain, b_gain]
```

CCM 是 3x3 矩阵变换：

```text
[R', G', B']^T = M * [R, G, B]^T
```

AWB 主要处理光源色偏；CCM 主要处理相机 RGB 到标准颜色空间的映射。AWB 不足以解决传感器滤色片和标准观察者之间的光谱差异。

### 34. 怎么验证 AWB 有效？

**答案：**

数值上：

- AWB 后灰色区域 R/G/B 更接近
- 全图或 ROI 的 R/G、B/G 更接近 1

视觉上：

- 明显偏绿、偏蓝、偏红趋势减轻

工程上：

- 用灰卡或中性 ROI 验证
- 避免饱和区参与统计
- 对比 rawpy / 相机 JPEG 的白平衡趋势

但不能只看“好看”，因为还没有 CCM 和 tone。

## 七、工程实现与验证

### 35. 你会如何设计一个可调试的 Soft-ISP pipeline？

**答案：**

每个模块都应有明确输入输出，并能保存中间结果：

```text
RAW
-> BLC
-> DPC
-> LSC
-> Demosaic
-> AWB
-> CCM
-> Gamma/Tone
```

每一步都保存：

- 统计 JSON
- before/after 图
- 关键参数
- 可视化图

这样出现问题时可以定位是哪一层引入的，而不是只看最终图。

### 36. 如果最终图严重偏色，你会怎么排查？

**答案：**

按顺序排查：

1. Bayer pattern 是否正确
2. BLC 是否扣对
3. Demosaic 是否 R/B 通道反了
4. AWB gain 是否异常
5. 是否用了错误 white level 归一化
6. CCM 是否矩阵方向用反
7. Gamma/Tone 是否在错误数据域执行

优先看中间图和通道统计，不要只凭最终视觉判断。

### 37. 如果图像边缘出现彩色锯齿，可能是哪一步问题？

**答案：**

常见原因：

- Demosaic 方法太简单，bilinear 跨边缘平均
- DPC 漏掉坏点，坏点扩散
- Bayer pattern 错误
- 锐化过强，如果后续有 sharpening

Week3 当前最可能是 bilinear demosaic 的局限。解决方向是边缘感知 demosaic 或更高级算法。

### 38. 为什么要把算法报告和代码一起维护？

**答案：**

ISP 很容易出现“代码能跑但不知道对不对”的情况。报告记录：

- 输入输出规格
- 公式
- 参数
- 统计结果
- 可视化
- 失败场景

这样可以让后续排查、复现实验和面试讲解都有依据。

### 39. 如何判断一个模块是否应该放在 Demosaic 前还是后？

**答案：**

看它处理的问题发生在哪个数据域：

- 传感器偏置、坏点、镜头阴影：发生在 RAW/Bayer 域，通常放在 Demosaic 前
- 白平衡：需要 RGB 通道，通常放在 Demosaic 后
- 颜色空间映射：需要 RGB，放在 AWB 后
- Gamma/Tone：面向显示，放在颜色校正后

原则是尽量在问题产生的原始域解决问题。

### 40. 面试官问“你这个 pipeline 和 rawpy 不一样，说明你错了吗？”怎么回答？

**答案：**

不一定。rawpy / LibRaw 的默认输出包含完整 ISP，包括更复杂的 demosaic、相机白平衡、颜色矩阵、gamma、亮度映射等。本项目当前 Week1-Week3 只做到 BLC、DPC、Demosaic、AWB，没有 CCM 和 Tone Mapping。

正确对比方式是分阶段对比：

- RAW 统计是否一致
- BLC 后黑位是否一致
- Demosaic 后结构是否正确
- AWB 后偏色趋势是否改善
- 最终阶段再比较 sRGB 视觉效果

## 八、综合追问题

### 41. 给你一张 DNG，你如何从 0 到 1 判断它能否进入 ISP pipeline？

**答案：**

先读 metadata：shape、dtype、black level、white level、Bayer pattern。再看 histogram：暗部是否大量贴 black level，高光是否贴 white level。然后拆 R/Gr/Gb/B，确认 Gr/Gb 接近，通道统计合理。最后生成 rawpy reference 做方向性对照。

如果 metadata 缺失、Bayer pattern 不明确、white level 异常或 RAW 数据明显损坏，就不能盲目进入 pipeline。

### 42. 如果 S03 的 DPC 候选点远多于 S01，你会怎么分析？

**答案：**

先看 S03 是否高光更多、纹理更强、p99 是否接近或超过 white level。DPC 候选多不一定都是坏点，可能是高光边缘和强纹理导致 residual 大。

接着看 mask overlay 是否集中在结构边缘。如果是，说明阈值可能偏敏感。可以提高 `min_delta`、调大 `mad_k`，或加入边缘保护策略。

### 43. 如果 AWB 后图像反而更差，可能是什么原因？

**答案：**

可能原因：

- 场景违反 Gray World 假设
- 大面积单色物体主导均值
- 饱和高光参与统计
- 暗部噪声参与统计
- Demosaic 或 Bayer pattern 已经错了
- 没有做 LSC，边缘色偏影响全图均值

解决方式：使用灰卡 ROI、排除饱和和暗部、使用更稳健的白点检测或学习型 AWB。

### 44. 如果你要把当前学习版 pipeline 产品化，最先补哪些能力？

**答案：**

优先补：

1. LSC 标定或估计
2. 更稳健的 DPC，结合固定坏点表
3. 边缘感知 Demosaic
4. 更稳健 AWB，如灰点检测、白点检测、统计分类
5. CCM 标定
6. Gamma/Tone Mapping
7. 系统化 IQA：PSNR、SSIM、DeltaE、人工主观评价

产品化的重点不是单张图效果，而是跨场景稳定性和可解释调参。

### 45. ISP 算法工程师为什么要懂传感器和成像物理？

**答案：**

因为很多问题不是普通图像处理问题，而是成像链路问题。例如 black level 来自读出电路，坏点来自传感器缺陷，lens shading 来自镜头和像素角度响应，AWB 和光源光谱相关。

如果只把输入当普通 RGB 图片，会在错误数据域修问题，导致越修越乱。

## 九、候选人可以主动讲的项目亮点

### 46. 如何介绍本项目？

**答案：**

可以这样说：

我从真实 DNG 开始搭建了一个可解释 Soft-ISP pipeline。前几周完成了 RAW metadata 检查、Bayer 通道统计、histogram / ROI 分析、BLC、DPC、bilinear Demosaic 和 Gray World AWB。每个模块都有独立脚本、统计 JSON、可视化结果和 Markdown 报告。我的重点不是调用黑盒库，而是能解释每一步输入输出、数学假设、失败场景和验证方法。

### 47. 面试官问“你的 Demosaic 为什么不用 OpenCV 直接做？”怎么答？

**答案：**

OpenCV 可以作为 baseline，但学习阶段我选择自己实现 bilinear，是为了明确 Bayer mask、插值核、真实采样位置保留这些细节。这样后续对比 OpenCV 或 AHD 时，我知道差异来自哪里。

工程上我会保留 OpenCV/rawpy 作为参考输出，但核心学习实现保持可解释。

### 48. 面试官问“你怎么证明不是写错了？”怎么答？

**答案：**

我会分模块验证：

- metadata：和 rawpy 输出一致
- BLC：black level 为 0 的样张不变，非 0 样张暗部向 0 移动
- DPC：mask 稀疏，crop 修复合理
- Demosaic：shape 从 `(H,W)` 到 `(H,W,3)`，图像结构正确
- AWB：R/G 和 B/G 更接近 1
- 全流程：与 rawpy reference 对比趋势

不是只看最终图，而是每一步都有可观测证据。

### 49. 如果要继续 Week4，你会怎么做？

**答案：**

Week4 应进入 CCM、Gamma、Tone Mapping：

1. CCM：把相机 RGB 映射到接近标准 sRGB 的颜色空间。
2. Gamma：把线性光信号转换成更适合显示和人眼感知的非线性编码。
3. Tone Mapping：压缩动态范围，处理高光和整体对比。

实现上先做简单 3x3 矩阵和 sRGB gamma，再逐步做更复杂 tone curve。

### 50. 当前 Week1-Week3 最大的技术短板是什么？

**答案：**

主要短板有：

1. 没有 LSC，位置相关亮度和色偏还没处理。
2. Demosaic 是 bilinear，边缘和纹理区域质量有限。
3. AWB 是 Gray World，强依赖场景平均颜色假设。
4. 还没有 CCM，所以颜色不在标准显示空间。
5. 还没有 Gamma/Tone，所以输出只是工程预览，不是最终照片。

但这正好形成后续学习路线：每个短板都对应一个可实现、可验证的 ISP 模块。
