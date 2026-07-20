# 第10章：色彩科学与ISP色彩处理


> 课程阶段：传统 ISP 与成像基础　|　难度：入门 → 中级　|　优先级：核心
>
> 建议用时：3–4 小时阅读 + 2–4 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**区分 camera RGB、线性 RGB、sRGB、XYZ/Lab、YCbCr，并完成 AWB/CCM 评价。**

## 1. 本章先解决什么问题

色彩处理要解决的核心问题是：相机传感器记录到的颜色，不等于人眼感知的颜色，也不等于显示器、JPEG、视频编码标准里定义的 RGB。

传感器的 R/G/B 来自它自己的彩色滤镜和光谱响应。不同相机的 R 滤镜、G 滤镜、B 滤镜透过的光谱范围不同；同一个物体在太阳光、钨丝灯、荧光灯、LED 灯下反射到传感器上的三通道比例也不同。因此，相机内部必须做一系列“翻译”：

```text
传感器自己的 camera RGB -> 消除光源色偏 -> 映射到标准色彩空间 -> 做显示/编码需要的非线性变换 -> 输出 RGB/YUV
```

本章最小链路是：

```text
输入：demosaic 后的线性 camera RGB，或白平衡前后的 RGB 统计
处理：AWB、颜色校正矩阵 CCM、色彩空间转换、OETF/gamma、YUV/YCbCr 编码、色彩评价
输出：更接近目标标准或目标风格的 RGB/YUV 图像
```

读完本章，至少要能回答：

- 为什么传感器 RGB 不是 sRGB。
- AWB 和 CCM 分别解决什么问题。
- 线性 RGB、gamma/sRGB、XYZ、Lab、YUV/YCbCr 各自是什么。
- 为什么色彩处理顺序和处理域不能乱。
- 为什么“颜色准确”和“颜色讨喜”有时会冲突。

## 2. 先区分三种 RGB

初学者最容易把所有 RGB 都当成一回事。实际上至少要区分三种。

| 名称 | 数据含义 | 常见位置 | 关键提醒 |
|---|---|---|---|
| Camera RGB | 相机传感器三通道响应 | demosaic 后、CCM 前 | 设备相关，不是标准颜色 |
| Linear RGB | 与场景光强近似成线性关系的 RGB | AWB、CCM、物理计算阶段 | 适合矩阵、增益、曝光相关处理 |
| sRGB/Display RGB | 面向显示和存储的非线性编码 RGB | 输出图、网页、普通 PNG/JPEG | 经过 OETF/gamma，不能当线性光强用 |

如果把 sRGB 当线性 RGB 做矩阵和平均，会出现错误。比如两个像素的 sRGB 数值平均，并不等于真实光强平均；在 gamma 编码后做颜色矩阵，也会让颜色和亮度关系变形。

一个简单判断：

```text
做 AWB 增益、CCM、曝光比例、物理亮度计算：优先在线性域。
做显示、JPEG/PNG 输出、UI 查看：通常用 sRGB 或其他显示编码。
做视频编码：常会转到 YUV/YCbCr，并带有特定标准矩阵和范围。
```

## 3. AWB 解决光源色偏，不是解决所有颜色问题

AWB 是 Auto White Balance，自动白平衡。它的目标不是让所有颜色都“更好看”，而是估计光源颜色，并把中性物体拉回中性灰。

同一张白纸，在不同光源下会让传感器记录出不同比例：

```text
日光下白纸：R、G、B 比例可能比较均衡
钨丝灯下白纸：R 明显偏高，B 明显偏低
阴天或蓝天阴影：B 可能偏高
```

AWB 常用通道增益处理：

```text
R' = gain_R * R
G' = gain_G * G
B' = gain_B * B
```

通常会固定 G 或让整体亮度保持稳定，然后调 R/B 增益。灰世界算法的直觉是：自然场景平均起来应该接近灰色。因此如果全图平均偏红，就降低红或提高其他通道；如果平均偏蓝，就调整蓝通道。

一个极简例子：

```text
某张图中性区域平均：
R_avg = 180
G_avg = 120
B_avg = 80

希望拉到 G 作为参考：
gain_R = 120 / 180 = 0.67
gain_G = 1.00
gain_B = 120 / 80  = 1.50
```

这表示画面可能在暖光下偏红，需要压 R、抬 B。实际 ISP 还会限制增益范围、排除饱和区、排除高色彩区域、使用灰点检测、色温轨迹和时域平滑。

## 4. 灰世界、白点、灰边和学习型 AWB

AWB 属于 color constancy 问题，也就是颜色恒常性：希望相机在不同光源下仍能稳定表达物体颜色。

常见 AWB 假设包括：

| 方法 | 基本假设 | 优点 | 失败场景 |
|---|---|---|---|
| 灰世界 Gray World | 场景平均反射接近灰 | 简单、硬件友好 | 大面积单一颜色，如草地、海洋、红墙 |
| 白点 White Patch/Max-RGB | 场景最亮区域应接近白 | 对有白物体场景有效 | 高光饱和、彩色高亮物体 |
| Shades of Gray | 灰世界和白点的泛化 | 可调节统计范数 | 参数依赖场景 |
| Gray Edge | 图像边缘/导数统计应接近灰 | 关注结构而非均值 | 噪声、纹理和边缘检测影响大 |
| 学习型 AWB | 从数据学习光源估计 | 复杂场景更强 | 数据偏差、传感器泛化、可解释性 |

AWB 很容易出错，因为它不知道场景里哪些东西本来就应该是灰色。比如一张全是绿色草地的照片，灰世界会误以为画面偏绿，从而把颜色拉偏。真实相机通常会结合多种线索：灰点候选、肤色保护、色温轨迹、历史帧稳定性、场景分类和人工调色偏好。

## 5. CCM：把 camera RGB 翻译到标准颜色

AWB 主要修正光源色偏，但它不能解决“传感器颜色响应和标准观察者不一致”的问题。这个问题通常由 CCM，Color Correction Matrix，颜色校正矩阵处理。

CCM 常见形式是 3x3 矩阵：

```text
[R_out]   [m00 m01 m02] [R_in]
[G_out] = [m10 m11 m12] [G_in]
[B_out]   [m20 m21 m22] [B_in]
```

其中：

- `R_in/G_in/B_in`：通常是白平衡后的线性 camera RGB。
- `R_out/G_out/B_out`：目标色彩空间的线性 RGB，或进入下一步色彩处理的 RGB。
- `m00...m22`：通过标定或调参得到的矩阵系数。

CCM 为什么需要混通道？因为相机的 R/G/B 滤镜并不等于标准 RGB 原色。某个传感器 R 通道可能也会收到一部分橙色、黄色甚至近红外残余；G/B 也有光谱重叠。单独给每个通道乘增益只能缩放通道，不能把这种光谱响应差异校正到目标颜色空间。

CCM 标定常用色卡，例如 ColorChecker。基本思路：

1. 在已知光源下拍摄色卡。
2. 取每个色块的 camera RGB 均值。
3. 准备每个色块的目标 XYZ、Lab 或目标 RGB。
4. 用最小二乘求一个 3x3 矩阵，让预测颜色尽量接近目标颜色。
5. 用 Delta E 等指标评估误差。

## 6. AWB 和 CCM 的顺序为什么重要

一个常见 pipeline 是：

```text
linear camera RGB -> AWB gains -> CCM -> tone/gamma/OETF -> output RGB/YUV
```

AWB 和 CCM 都是线性域操作，但目标不同：

- AWB：估计光源，让中性物体中性。
- CCM：修正相机色彩响应，让颜色落到目标标准或目标风格。

如果 AWB 错了，CCM 输入就已经带有光源色偏，后面颜色会整体不稳。如果 CCM 错了，即使白色看起来正确，肤色、绿色、蓝天、饱和红等也可能不准。

初学者可以用一句话区分：

```text
AWB 管“白纸在不同灯下还像白纸”。
CCM 管“白纸之外的各种颜色是否落在正确位置”。
```

## 7. XYZ、Lab 和 Delta E 是用来评价颜色的

CIE XYZ 是设备无关色彩空间，源于人眼标准观察者模型。它不是为了好看，而是为了把颜色表示和具体设备分开。

Lab 在 XYZ 基础上做非线性变换，使距离更接近人眼感知差异。常见的色差指标 Delta E 就在 Lab 相关空间里计算。

直觉上：

```text
XYZ：设备无关的颜色计量基础。
Lab：更接近人眼感知均匀性的颜色空间。
Delta E：两个颜色差多远的数字。
```

常见理解：

- Delta E 越小，颜色越接近目标。
- 平均 Delta E 可以衡量整体色彩准确性。
- 最大 Delta E 可以暴露某些色块严重跑偏。
- 色彩调参不能只看平均值，因为肤色、灰阶、饱和色可能有不同优先级。

注意：Delta E 评价的是颜色准确性，不等于主观讨喜。很多消费相机会故意让天空更蓝、草地更绿、肤色更暖。这是风格选择，不一定是色度计意义上的准确。

## 8. sRGB、Gamma 和 OETF

很多人把 gamma 简单理解成“调亮图像”，这是不够的。更准确地说，OETF 是 Opto-Electronic Transfer Function，用来把场景线性光信号编码成更适合存储、传输和显示的非线性信号。sRGB 的非线性传输函数由 IEC 61966-2-1 标准定义，常被近似说成 gamma 约 2.2，但它并不是单纯一条 `x^(1/2.2)` 曲线，而是在暗部有线性段、之后是幂函数段。

为什么要非线性编码？

- 人眼对暗部相对变化更敏感。
- 非线性编码可以把有限 bit 更有效地分配给视觉重要区域。
- 显示和图像文件通常期望 sRGB 等标准编码。

一个关键提醒：

```text
线性 RGB 适合物理计算和矩阵变换。
sRGB 适合显示和普通图像文件。
不要在 sRGB 非线性域里随便做应该在线性域完成的颜色矩阵和光照计算。
```

## 9. YUV/YCbCr：为什么视频不总存 RGB

YUV 或更准确的数字视频 YCbCr，把亮度和色度分开：

```text
Y：亮度或 luma
Cb/Cr：蓝差、红差色度分量
```

这样做有两个重要原因：

1. 人眼对亮度细节更敏感，对色度细节相对不敏感。
2. 视频编码可以对色度做子采样，例如 4:2:2、4:2:0，以节省带宽。

但 YCbCr 不是只有一个公式。BT.601、BT.709、BT.2020 等标准的矩阵、范围和用途不同：

| 标准 | 常见用途 | 关键提醒 |
|---|---|---|
| BT.601 | SD 视频 | 不适合随便套到 HD/4K |
| BT.709 | HD/sRGB 相关视频场景 | 常见于高清内容 |
| BT.2020 | UHD/HDR 宽色域 | 原色和矩阵不同 |

还要注意 full range 和 limited range：

```text
Full range 8-bit：Y 可用 0-255
Limited range 8-bit：Y 常用 16-235，Cb/Cr 常用 16-240
```

范围弄错会导致画面发灰、黑位抬高、白位压缩或颜色异常。

## 10. 色彩准确和主观风格的冲突

ISP 色彩处理有两个目标经常拉扯：

```text
色彩准确：尽量接近真实或标准目标。
主观风格：让用户觉得好看、舒服、有品牌味道。
```

比如：

- 肤色可能被调得更暖、更均匀。
- 天空可能被调得更蓝。
- 草地可能被调得更绿。
- 食物可能被提高暖色饱和度。
- 夜景可能保留一点暖光氛围，而不是完全拉成中性白。

这些不是简单的对错，而是目标不同。工业检测、医学、文档扫描、自动驾驶可能更重视一致性和可测量性；手机摄影和社交照片可能更重视观感。初学者要先学会“准确”和“讨喜”是两套评价语言，再学习如何折中。

## 11. 硬件实现关注点

色彩处理看起来只是几个矩阵和曲线，但在硬件 ISP 中仍有很多细节。

常见关注点：

- 矩阵乘法：CCM、RGB 到 YCbCr 都是矩阵运算，需要定点系数。
- 位宽增长：3x3 矩阵乘加可能产生负值和溢出，中间位宽要足够。
- 系数量化：浮点矩阵转定点会引入误差。
- clipping/saturation：矩阵后超出范围的值如何裁剪会影响饱和色。
- LUT：gamma/OETF、tone curve、Lab 变换可用查表或分段线性近似。
- 时域平滑：AWB 增益突然跳变会造成视频颜色闪烁。
- 统计区域：AWB 统计要排除饱和、暗噪声、强彩色物体和异常区域。
- 标准匹配：RGB/YUV 矩阵必须和输出标准、范围、bit depth 一致。

一个常见硬件数据流可以写成：

```text
linear RGB -> AWB gain -> 3x3 CCM -> clamp -> tone/OETF LUT -> RGB/YUV matrix -> output
```

## 12. 最小可验证实验

实验 1：AWB 增益实验。

1. 找一张带灰卡或白纸的图。
2. 分别关闭 AWB、使用灰世界 AWB、手动白点 AWB。
3. 观察灰卡是否中性，肤色和背景是否被误伤。
4. 记录 R/G/B 灰卡均值是否接近。

实验 2：CCM 错误实验。

1. 准备一张色卡图或颜色丰富的图。
2. 使用单位矩阵、正确 CCM、故意交换 R/B 的错误矩阵。
3. 对比肤色、红色、绿色、蓝色和灰阶。
4. 观察“白平衡看似正确但颜色仍不准”的情况。

实验 3：线性域和 sRGB 域对比。

1. 在线性 RGB 中做 CCM 后再转 sRGB。
2. 另一路先转 sRGB 再做同样矩阵。
3. 比较暗部、肤色、饱和色差异。
4. 记录为什么处理域不能混用。

实验 4：sRGB/OETF 观察。

1. 生成一条线性灰阶 ramp。
2. 应用 sRGB OETF。
3. 对比数值和视觉亮度分布。
4. 理解为什么 gamma 不是简单“变亮”。

实验 5：Delta E 色卡评估。

1. 拍摄 ColorChecker 或使用公开色卡数据。
2. 提取每个色块平均 RGB。
3. 转到 XYZ/Lab。
4. 和目标 Lab 比较 Delta E。
5. 同时看平均 Delta E、最大 Delta E、灰阶误差和肤色色块误差。

## 13. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 整体偏黄/偏蓝 | AWB 光源估计错误 | 看灰卡/中性区域 R/G/B，检查增益和色温 |
| 白色正确但颜色仍不准 | CCM 不准或光源不匹配 | 用色卡看各色块 Delta E |
| 红蓝互换 | CFA pattern 或通道顺序错 | 回查 demosaic pattern 和 RGB/BGR 顺序 |
| 画面发灰 | YUV full/limited range 弄错，或 gamma/tone 错 | 检查输出范围和显示解释 |
| 暗部颜色怪 | 黑电平、AWB 增益、OETF 或噪声放大 | 回到线性 RAW/RGB 检查 |
| 饱和色断层 | CCM 后 clipping 或位宽不足 | 查看矩阵后是否溢出 |
| 视频颜色跳变 | AWB 收敛过快或统计不稳 | 加时域平滑，检查统计区域 |
| 色卡平均好但肤色差 | 优化目标没有加权关注肤色 | 分色块看 Delta E，不只看平均值 |
| sRGB 显示过暗/过亮 | 线性数据被当 sRGB，或 sRGB 被当线性 | 检查 transfer function 标记和处理顺序 |

## 14. 常见误区

- 误区 1：传感器 RGB 就是标准 RGB。传感器响应是设备相关的，需要 CCM 或更复杂模型映射。
- 误区 2：AWB 可以解决所有偏色。AWB 主要解决光源色偏，不能替代色彩校正。
- 误区 3：CCM 随便调到好看就行。没有色卡和 Delta E，很容易牺牲某些颜色。
- 误区 4：Gamma 就是调亮。OETF 是标准化非线性编码，处理域错会造成系统性错误。
- 误区 5：YUV 公式只有一种。BT.601/709/2020、full/limited range 都会影响结果。
- 误区 6：色彩准确就是最好看。准确、风格、肤色偏好、品牌调色可能冲突。
- 误区 7：只看一张图就能调好颜色。色彩处理需要多光源、多场景、色卡和主观图共同验证。

## 15. 学习优先级

必须掌握：

- Camera RGB、linear RGB、sRGB/display RGB 的区别。
- AWB、CCM、OETF/gamma、YUV/YCbCr 的输入输出。
- AWB 增益公式和灰世界/白点直觉。
- 3x3 CCM 的矩阵含义。
- XYZ、Lab、Delta E 的评价用途。
- 线性域和非线性域不能混用。

了解即可：

- Gray Edge、Shades of Gray、学习型 color constancy。
- 多光源 CCM、色温插值、profile 切换。
- BT.601/709/2020、full/limited range 的标准细节。
- 色卡检测、光谱反射率、标准观察者。

后面再回看：

- 光谱相机模型、metamerism 同色异谱问题。
- 高阶颜色校正、3D LUT、色彩外观模型。
- HDR/WCG 中 PQ、HLG、BT.2020、色调映射与色域映射。
- 跨相机颜色一致性和学习型 CCM/AWB。

## 16. 自测题

1. 为什么 camera RGB 不是 sRGB？
2. AWB 和 CCM 分别解决什么问题？
3. 灰世界 AWB 在什么场景容易失败？
4. 为什么 CCM 通常要在白平衡后的线性 RGB 上做？
5. sRGB 为什么不是简单线性亮度？
6. Delta E 可以评价什么？它不能评价什么？
7. BT.601 和 BT.709 矩阵用错可能出现什么问题？
8. full range 和 limited range 弄错会造成什么视觉现象？
9. 如果白色看起来正常但肤色不对，你会优先检查什么？
10. 如何设计一个实验说明“在线性域做 CCM”和“在 sRGB 域做 CCM”的差异？

## 17. 读完本章的验收标准

合格的学习结果应该是：

- 口头解释：能讲清相机色彩处理是在做设备相关颜色到目标颜色的翻译。
- 输入输出：能写出 AWB、CCM、OETF、YUV 转换各自吃什么、吐什么。
- 公式理解：能用简单数值算一次 AWB 增益，能解释 3x3 CCM 的矩阵乘法。
- 现象排查：能根据偏黄、偏蓝、发灰、饱和色断层、视频跳色提出排查方向。
- 评价能力：能用色卡、灰卡、Delta E、局部主观图共同评价颜色。
- 工程判断：能说明准确色彩、讨喜风格、硬件位宽、标准输出之间的取舍。

## 18. 推荐资料与进一步阅读

- [International Color Consortium: sRGB interpretation](https://www.color.org/chardata/rgb/srgb.pdf)：理解 sRGB 标准、白点、原色和非线性传输函数。
- [CIE 官方网站](https://cie.co.at/)：色度学、标准观察者、XYZ/Lab 等色彩科学标准的源头。
- [colour-science Python library](https://www.colour-science.org/)：适合做 XYZ、Lab、Delta E、色彩空间转换实验。
- [OpenCV Color Conversions](https://docs.opencv.org/3.4/d8/d01/group__imgproc__color__conversions.html)：查看 RGB/YUV/HSV/Lab 等转换接口和注意事项。
- [Raspberry Pi Camera Algorithm and Tuning Guide](https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf)：从真实相机调参角度理解 AWB、CCM、gamma 和 ISP 色彩流程。
- [Automatic White Balancing via Gray Surface Identification](https://www.cs.sfu.ca/~colour/publications/CIC-2007/index_CIC15_XIONG_PG143.html)：AWB/灰点识别相关论文，可帮助理解灰世界方法的局限。
- [Color Homography Color Correction](https://arxiv.org/abs/1607.05947)：理解颜色校正在不同光照、阴影和相机之间的更高级模型。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab05-色彩与3A.md](../labs/lab05-色彩与3A.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter10-第10章：色彩科学与ISP色彩处理.md)
- 项目落点：
  - [AWB 实现](../../stage1_soft_isp/soft_isp/awb.py)
- [CCM 实现](../../stage1_soft_isp/soft_isp/ccm.py)
- [ColorChecker 标定](../../stage1_soft_isp/scripts/21_calibrate_colorchecker.py)
- 原始资料：[原教程正文归档](../source_archive/chapter10-第10章：色彩科学与ISP色彩处理.md)

导航：[上一章](./chapter09-第9章：NLM算法硬件实现专题.md) · [下一章](./chapter11-第11章：ISP硬件架构基础.md) · [完整课程索引](../full_content_index.md)
