# 第7章：去马赛克技术深度解析


> 课程阶段：传统 ISP 与成像基础　|　难度：入门 → 中级　|　优先级：核心
>
> 建议用时：3–4 小时阅读 + 2–4 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**比较双线性、边缘感知和 MHC 去马赛克的伪影与代价。**

## 1. 本章先解决什么问题

第 7 章讨论的是 demosaicing，也常写作 demosaic、demosaicking、debayer。它是从 RAW Bayer 图像进入 RGB 图像世界的关键一步。

初学者最容易把去马赛克理解成“把一张单通道图插值成三通道图”。这个说法只对了一半。更准确地说，Bayer RAW 里的每个像素只测到一种颜色，去马赛克要在每个像素位置补齐缺失的另外两种颜色，同时尽量不破坏边缘、不制造伪色、不放大噪声、不把坏点扩散成彩色瑕疵。

最小链路是：

```text
输入：BLC/BPC/LSC/RAW 去噪后的一张 Bayer RAW
处理：识别 CFA pattern，在 R/G/B 不同采样位置补齐缺失颜色
输出：每个像素都有 R、G、B 三个分量的线性 RGB 图像
```

这个模块之所以重要，是因为它改变了数据形态：

```text
Bayer RAW：一个坐标只有一个颜色采样值
RGB 图像：一个坐标有 R、G、B 三个颜色值
```

一旦完成 demosaic，后面的颜色校正、白平衡、色彩空间转换、tone mapping、锐化、编码等模块就会以 RGB 或 YUV 图像为对象。也就是说，去马赛克是传统 ISP 中非常重要的一道“边界门”。

读完本章，至少要能回答：

- Bayer RAW 为什么缺颜色。
- 为什么绿色通道通常最重要。
- 最近邻、双线性、边缘感知、Malvar-He-Cutler 这几类方法差在哪里。
- false color 和 zipper artifact 是怎么来的。
- 为什么前面章节的坏点、噪声、镜头阴影问题会影响 demosaic。

## 2. 从 Bayer 图案建立直觉

大多数普通相机不是每个像素同时测 R、G、B 三个颜色，而是在传感器上覆盖一层 Color Filter Array，简称 CFA。最常见的是 Bayer CFA。以 RGGB 为例，一个 2x2 小块是：

```text
R  G
G  B
```

这四个像素里有两个 G，一个 R，一个 B。绿色采样更多，是因为人眼对亮度结构更敏感，而绿色通道常常更接近亮度信息。很多 demosaic 算法会先重建 G，再利用 G 与 R/B 的关系重建红蓝通道。

一个 4x4 Bayer RAW 可以这样看：

```text
R  G  R  G
G  B  G  B
R  G  R  G
G  B  G  B
```

但最终 RGB 图像每个位置都要变成：

```text
(R,G,B) (R,G,B) (R,G,B) ...
(R,G,B) (R,G,B) (R,G,B) ...
```

所以在一个 R 位置：

```text
已有：R
缺失：G、B
```

在一个 G 位置：

```text
已有：G
缺失：R、B
```

在一个 B 位置：

```text
已有：B
缺失：R、G
```

去马赛克就是根据邻域已有采样，估计这些缺失颜色。难点在于：图像里有边缘、纹理、噪声、细线、重复图案和高光。如果只按固定平均去猜，会在这些区域出问题。

## 3. CFA pattern 不能弄错

学习 demosaic 时，第一个工程坑是 CFA pattern。常见 Bayer 排列包括 RGGB、BGGR、GRBG、GBRG。它们看起来只是起始位置不同，但如果 pattern 设错，颜色会整体混乱。

| Pattern | 左上角 2x2 排列 | 常见错误后果 |
|---|---|---|
| RGGB | R G / G B | 正常红蓝关系 |
| BGGR | B G / G R | 若按 RGGB 解，会红蓝互换 |
| GRBG | G R / B G | 若起点错一列，颜色和细节都会异常 |
| GBRG | G B / R G | 若起点错一行，也会出现偏色 |

注意，RAW 文件中的“第一行第一列”不一定就是有效图像的第一行第一列。传感器可能有 optical black 区域、裁剪、奇偶行偏移、binning、skipping。如果 crop 起点改变了奇偶性，CFA pattern 也会跟着变化。

一个简单判断：

```text
如果整幅图明显红蓝互换，优先怀疑 RGGB/BGGR 用反。
如果边缘和彩色细节都怪，但不是单纯红蓝互换，怀疑起始行/列相位错。
如果不同 sensor mode 下颜色表现不同，检查 crop/binning 后的 CFA 坐标映射。
```

OpenCV 的 Bayer 转换接口就明确区分 `COLOR_BayerBG2BGR`、`COLOR_BayerGB2BGR`、`COLOR_BayerRG2BGR`、`COLOR_BayerGR2BGR` 等不同模式。这提醒我们：demosaic 不是只要“有 RAW 就能转 RGB”，必须知道这张 RAW 的 CFA 排列。

## 4. 最近邻和双线性：最简单，也最容易看出问题

最近邻插值的思路是：缺哪个颜色，就找最近的同色像素复制过来。它非常快，但容易产生块状感和彩色锯齿。它的价值主要是教学和调试，因为它让你很容易看出 CFA 采样结构。

双线性插值比最近邻平滑。它会对周围同色像素做平均。例如在 R 位置补 G，通常会用上下左右的 G：

```text
G_est = (G_up + G_down + G_left + G_right) / 4
```

变量解释：

- `G_est`：当前 R 或 B 位置缺失的绿色估计值。
- `G_up/down/left/right`：上下左右已采样的绿色像素。
- `/4`：简单平均，硬件上可以用移位实现。

在 B 位置补 R，通常会用四个对角 R：

```text
R_est = (R_ul + R_ur + R_dl + R_dr) / 4
```

双线性方法的优点：

- 实现简单。
- 速度快。
- 窗口小，硬件成本低。
- 适合做 baseline。

双线性方法的缺点：

- 把边缘两侧的颜色平均在一起，边缘会变糊。
- 高频纹理容易产生 false color。
- 斜线和文字边缘容易出现 zipper artifact。
- 前端坏点或噪声可能被扩散到多个颜色通道。

所以双线性不是“没用”，而是它的角色更像一把尺子：先用它建立最低基准，再看更高级算法到底改善了什么。

## 5. 为什么绿色通道常常先重建

Bayer 中 G 的采样密度是 R/B 的两倍。很多自然图像里，R、G、B 通道的边缘位置高度相关，而 G 通道又更接近亮度结构。因此不少经典算法会先尽量把 G 通道重建好，再利用色差关系补 R/B。

这里有一个重要经验：颜色通道本身变化可能很大，但色差在局部区域往往更平滑。例如：

```text
R - G
B - G
```

这两个差值在同一物体表面上通常比 R、G、B 原值更平滑。Malvar-He-Cutler 一类线性高质量插值方法，就利用了跨通道校正思想：不是只平均同色邻居，而是把另一个通道的拉普拉斯信息作为校正项加入缺失颜色估计。

用初学者语言说：

```text
普通插值：只看同一种颜色附近的值。
色差/跨通道校正：利用“颜色边缘通常和亮度边缘对齐”这个事实，让估计更聪明。
```

这也是为什么 demosaic 不是单纯的图像缩放。图像缩放是在同一个通道里插值；demosaic 是在被 CFA 欠采样的多颜色通道之间做联合重建。

## 6. 边缘感知：沿边缘插值，而不是跨边缘平均

边缘是 demosaic 的核心难点。假设一条竖直黑白边界穿过图像，边界左边暗，右边亮。如果算法把边界左右两侧拿来平均，边缘就会变灰、变糊，还可能产生彩色边。

边缘感知算法的基本思想是：

```text
先估计当前像素附近是水平边缘、垂直边缘，还是无明显方向。
再沿变化更小的方向插值。
```

一个非常简化的方向判断：

```text
horizontal_diff = abs(left - right)
vertical_diff   = abs(up - down)

如果 horizontal_diff < vertical_diff：
    说明左右更平滑，优先水平插值
如果 vertical_diff < horizontal_diff：
    说明上下更平滑，优先垂直插值
否则：
    两个方向加权平均
```

这里要小心一个词：“沿边缘插值”。如果一条边缘是竖直的，那么沿边缘方向是上下；跨边缘方向是左右。算法通常希望沿着更一致的方向补值，避免把边缘两侧的内容混在一起。

Hamilton-Adams 类方法、梯度方向方法、边缘自适应方法，都在不同程度上围绕这个思想展开。区别在于它们怎么计算梯度、怎么融合方向、怎么利用颜色差和拉普拉斯校正。

## 7. False Color 和 Zipper Artifact

去马赛克失败最典型的两个现象是 false color 和 zipper artifact。

False color 指本来没有彩色细节的地方出现彩色条纹、彩色网格或彩色噪点。常见于：

- 黑白细线。
- 纺织物、网格、栅栏。
- 树枝、头发、文字。
- 接近传感器采样频率的重复纹理。

原因是 CFA 对 R/G/B 的采样位置不同，高频亮度纹理会被算法误解释成颜色差异。

Zipper artifact 指边缘上出现拉链状锯齿，尤其在斜线、文字边缘、高反差边界上明显。它常来自：

- 插值方向判断错误。
- 绿色通道重建不连续。
- R/B 通道和 G 通道边缘没有对齐。
- 前端坏点、噪声或过强锐化影响了梯度判断。

一个排查直觉：

```text
彩色纹理异常：优先看 false color。
黑白边缘一格一格跳：优先看 zipper。
整体颜色错：先查 CFA pattern 和白平衡，不要急着怪 demosaic。
边缘局部彩边：检查 demosaic、镜头像差、色差校正和锐化顺序。
```

## 8. Malvar-He-Cutler 为什么经典

Malvar-He-Cutler，常简称 MHC，是非常经典的 Bayer demosaic 方法。IPOL 对它有清晰介绍：它是一种基于 5x5 线性滤波器的高质量线性插值方法，源自 Malvar、He、Cutler 2004 年提出的 “High-Quality Linear Interpolation for Demosaicing of Bayer-Patterned Color Images”。

MHC 的重要性在于它给初学者展示了一个中间路线：

```text
比双线性聪明：加入跨通道校正，质量更好。
比复杂优化方法简单：仍然是固定线性滤波，适合实现和验证。
```

它的核心直觉可以这样理解：

1. 先用邻域同色信息做一个基础估计。
2. 再用其他颜色通道的局部二阶变化进行修正。
3. 这个修正项帮助边缘和颜色结构更一致。

为什么用 5x5？因为 3x3 能看到的信息有限，5x5 可以覆盖更充分的同色采样和局部结构；但窗口再大，硬件缓存和计算成本也会上升。

学习 MHC 时，不必一开始死背所有卷积核。更重要的是理解它为什么比双线性好：

- 双线性只做局部平均。
- MHC 通过拉普拉斯校正利用跨通道相关性。
- 它仍是线性滤波，因此易于做软件 golden model 和硬件实现对齐。

## 9. 频域、优化和学习型方法放在哪里理解

本章后面会讲频域方法、迭代优化、残差最小化等内容。初学者不用一上来就被公式压住，可以先按问题层级理解。

频域方法关心的是：Bayer 采样会把亮度和色度信息混到不同频率位置，demosaic 可以被看成一种分离和重建问题。它适合理解为什么高频纹理会变成伪色。

优化方法关心的是：在满足已知 RAW 采样值不变的前提下，找一张最合理的 RGB 图像。所谓“合理”，可能包括颜色差平滑、边缘一致、残差最小、正则化约束等。

学习型方法通常把 demosaic 和 denoise、super-resolution、HDR、deblur 联合起来考虑。原因是实际 RAW 中噪声和缺失颜色是耦合的：如果先用传统方法把 noisy RAW demosaic 成 RGB，噪声和伪色可能已经扩散；如果网络直接在 RAW 域学习重建，有机会联合解决多个问题。但学习型方法也有代价：需要数据、算力、泛化验证和更复杂的失败分析。

可以用这张表建立位置感：

| 方法类型 | 适合理解的问题 | 工程特点 |
|---|---|---|
| 最近邻 | CFA 结构和最小补色 | 质量差，教学好 |
| 双线性 | baseline 和低成本实现 | 快，但边缘糊、伪色多 |
| 边缘感知 | 为什么要看梯度方向 | 质量更好，参数更多 |
| MHC | 线性高质量插值和跨通道校正 | 经典、可实现、可验证 |
| 频域方法 | 采样混叠和伪色来源 | 理论解释力强 |
| 优化方法 | 约束重建和残差最小化 | 质量高，实时性较难 |
| 学习型方法 | 联合 demosaic/denoise/enhance | 数据和泛化是核心风险 |

## 10. 去马赛克和前后模块的关系

去马赛克不是孤立模块。它吃进来的 RAW 质量，会直接决定输出 RGB 是否干净。

常见顺序可以理解为：

```text
RAW -> BLC -> BPC/DPC -> LSC -> RAW denoise -> AWB gain -> demosaic -> CCM -> tone/sharpen/YUV
```

不同 ISP 的顺序可能略有差异，但几个关系很重要：

- BPC 在 demosaic 前：坏点不修会扩散成彩点。
- RAW denoise 在 demosaic 前或与 demosaic 联合：噪声会影响梯度方向和颜色估计。
- LSC 在 demosaic 前：镜头阴影和 color shading 会影响不同通道的空间一致性。
- AWB gain 的位置要谨慎：增益会放大噪声，也会改变通道间比例。
- Sharpen 通常不能太早：如果先产生 zipper/false color，再锐化会把伪影变得更明显。

一个常见调试误区是：看到 RGB 图边缘彩色异常，就只调 demosaic。实际上问题可能来自前端坏点、CFA pattern 错、LSC 色彩阴影、RAW 去噪过强或锐化过强。正确做法是回到 RAW 和每个中间阶段逐步排查。

## 11. 硬件实现关注点

去马赛克在硬件 ISP 中通常是高吞吐流式模块。它需要在每个像素到来时输出完整 RGB，不能随便回头访问整幅图像。

硬件实现要重点考虑：

- 窗口大小：3x3、5x5、7x7 对 line buffer 和延迟要求不同。
- 边界处理：图像最外几行几列没有完整邻域，需要复制、镜像、裁剪或特殊分支。
- CFA 相位判断：行列奇偶决定当前位置是 R/G/B，crop 后相位要同步。
- 位宽：RAW 可能是 10/12/14/16 bit，插值中间值要防止溢出。
- 吞吐：4K60、8K30 等场景下，每秒像素数非常高。
- 乘法器和加法器：MHC 等固定滤波器可以用定点系数、移位和流水线优化。
- 与后续模块对齐：输出 RGB 的时序、延迟、valid 信号必须和后续 CCM/CSC 等模块匹配。

简单资源直觉：

```text
双线性：3x3 附近就够，成本最低。
MHC：常用 5x5 滤波器，质量和成本平衡较好。
更复杂边缘/优化方法：窗口更大，控制逻辑更多，硬件验证更难。
```

这也是为什么很多工程系统不会盲目追求论文指标最高的方法，而会在图像质量、实时性、功耗、面积、验证难度之间取平衡。

## 12. 最小可验证实验

实验 1：手工理解 Bayer 补色。

1. 写一个 4x4 或 6x6 的 RGGB 小矩阵。
2. 标出每个坐标是 R、Gr、Gb 还是 B。
3. 任选一个 R 位置，手算 G 和 B 应该参考哪些邻居。
4. 再任选一个 G 位置，手算 R/B 应该从水平、垂直还是对角方向取值。

实验 2：比较最近邻、双线性、MHC。

1. 找一张包含文字、斜线、网格、树枝或布料纹理的 RAW。
2. 用最近邻、双线性、MHC 三种方法输出 RGB。
3. 不只看整图，要裁剪 200x200 的局部区域放大查看。
4. 重点比较边缘锐度、false color、zipper、细节保留。

实验 3：验证 CFA pattern 错误。

1. 对同一张 RAW 分别用 RGGB、BGGR、GRBG、GBRG 解码。
2. 观察红蓝互换、整体偏色、边缘异常。
3. 记录“pattern 错”和“白平衡错”的视觉差异。

实验 4：观察前端坏点如何扩散。

1. 在 Bayer RAW 中人工注入几个 hot pixel。
2. 不做 BPC，直接 demosaic。
3. 再先做同色坏点修复，然后 demosaic。
4. 对比彩点扩散范围。

实验 5：观察噪声对方向判断的影响。

1. 给 RAW 加不同强度噪声。
2. 运行边缘感知 demosaic。
3. 查看高 ISO 场景下边缘方向是否更容易判断错误。
4. 比较先 RAW denoise 再 demosaic 和直接 demosaic 的差异。

## 13. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 红色和蓝色明显互换 | CFA pattern 用反 | 检查 RGGB/BGGR 和 RAW crop 起点 |
| 黑白细线出现彩色条纹 | 高频纹理混叠，false color | 比较 MHC/边缘感知方法，检查 OLPF/锐化 |
| 斜线边缘像拉链 | 绿色通道重建不连续，方向判断错 | 查看 zipper 区域的 RAW 和梯度 |
| 细节整体偏糊 | 插值过于平滑或 RAW 去噪过强 | 对比双线性/MHC/边缘方法，检查去噪强度 |
| 彩点从单个点扩散 | 前端坏点未修 | 回到 BPC/DPC 检查 |
| 高 ISO 下彩噪严重 | 噪声被 demosaic 扩散 | 检查 RAW denoise 和联合 demosaic/denoise |
| 画面边缘偏色 | LSC/color shading 或 demosaic 受影响 | 检查 LSC 与通道一致性 |
| 不同分辨率模式颜色不同 | crop/binning 后 CFA 相位错 | 检查 sensor mode 的起始坐标 |

## 14. 常见误区

- 误区 1：去马赛克就是普通插值。普通插值只在一个通道内补值，demosaic 要处理 CFA 欠采样和跨通道关系。
- 误区 2：只要 RGB 看起来有颜色，就说明 demosaic 对了。CFA pattern 错也可能生成彩色图，只是颜色和细节都不可靠。
- 误区 3：双线性太简单所以不用学。双线性是理解所有高级方法的 baseline。
- 误区 4：边缘越锐越好。过度追求锐边可能带来 false color、zipper 和振铃。
- 误区 5：PSNR 高就一定视觉好。伪色和局部边缘瑕疵可能在全局指标里不明显，但人眼很敏感。
- 误区 6：demosaic 后再修坏点也可以。很多坏点已经被扩散，后面更难定位。
- 误区 7：学习型方法可以自动解决所有问题。训练数据、传感器差异、CFA pattern、噪声模型和实时性都会限制它。

## 15. 学习优先级

必须掌握：

- Bayer CFA 的 2x2 结构和四种常见 pattern。
- demosaic 的输入输出和 pipeline 位置。
- 最近邻、双线性、边缘感知、MHC 的基本差异。
- false color、zipper artifact 的视觉表现和原因。
- 为什么坏点、噪声、CFA 相位会影响 demosaic。

了解即可：

- 频域解释中的采样混叠和亮色分离。
- 优化方法中的残差、正则化、迭代更新。
- 硬件中的 line buffer、定点系数、流水线延迟。
- 非 Bayer CFA、Quad Bayer、Nona Bayer 等新型排列。

后面再回看：

- 复杂残差插值、稀疏表示、图优化、深度学习 demosaic。
- demosaic 与 denoise、super-resolution、HDR 融合的端到端模型。
- 不同评价指标与主观视觉质量之间的差异。

## 16. 自测题

1. Bayer RAW 中一个 R 像素缺哪两个颜色？一个 G 像素又缺哪两个颜色？
2. 为什么 Bayer 中绿色像素数量通常是红色或蓝色的两倍？
3. CFA pattern 设置错时，可能出现哪些图像现象？
4. 双线性插值为什么容易让边缘变糊？
5. 什么是 false color？它通常出现在哪些图像区域？
6. 什么是 zipper artifact？它和边缘方向判断有什么关系？
7. 为什么 MHC 比双线性更好，但仍然适合工程实现？
8. 为什么去马赛克前的坏点和噪声会影响最终 RGB 质量？
9. 如果你要比较两个 demosaic 算法，为什么不能只看整图缩略图？
10. 如何设计一个实验区分“CFA pattern 错”和“白平衡错”？

## 17. 读完本章的验收标准

合格的学习结果应该是：

- 口头解释：能用 2 分钟讲清 Bayer RAW 到 RGB 的过程。
- 输入输出：能明确写出 demosaic 的输入是 Bayer RAW，输出是线性 RGB。
- 手算能力：能对一个小 RGGB patch 手算几个位置的双线性补值。
- 现象判断：能看到 false color、zipper、红蓝互换、细节糊化时提出合理原因。
- 工程判断：能说明为什么算法选择要平衡画质、窗口、缓存、吞吐和验证难度。
- 实验验证：能对同一 RAW 比较最近邻、双线性、MHC 或边缘感知方法，并用局部 crop 说明差异。

## 18. 推荐资料与进一步阅读

- [IPOL: Malvar-He-Cutler Linear Image Demosaicking](https://www.ipol.im/pub/art/2011/g_mhcd/)：对 MHC 5x5 线性滤波方法有清晰复现和解释。
- [Malvar, He, Cutler, High-Quality Linear Interpolation for Demosaicing of Bayer-Patterned Color Images](https://web.stanford.edu/class/ee367/reading/Demosaicing_ICASSP04.pdf)：经典 MHC 原论文，适合理解跨通道拉普拉斯校正。
- [Image Demosaicing: A Systematic Survey](https://www4.comp.polyu.edu.hk/~cslzhang/paper/conf/demosaicing_survey.pdf)：系统综述，适合建立算法谱系。
- [OpenCV Color Space Conversions](https://docs.opencv.org/3.4/d8/d01/group__imgproc__color__conversions.html)：查看不同 Bayer pattern 到 BGR/RGB 的转换接口。
- [Raspberry Pi Camera Algorithm and Tuning Guide](https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf)：理解真实相机调参中 demosaic 与前后模块的关系。
- [The Effect of the Color Filter Array Layout Choice on State-of-the-Art Demosaicing](https://pmc.ncbi.nlm.nih.gov/articles/PMC6679506/)：理解 CFA 排列选择如何影响 demosaic 难度和质量。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab03-去马赛克与伪影.md](../labs/lab03-去马赛克与伪影.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter07-第7章：去马赛克技术深度解析.md)
- 项目落点：
  - [Demosaic 实现](../../stage1_soft_isp/soft_isp/demosaic.py)
- [Demosaic 练习](../../stage1_soft_isp/exercises/week3_demosaic_todo.py)
- 原始资料：[原教程正文归档](../source_archive/chapter07-第7章：去马赛克技术深度解析.md)

导航：[上一章](./chapter06-第6章：ISP前端处理：像素级处理.md) · [下一章](./chapter08-第8章：ISP降噪技术全景.md) · [完整课程索引](../full_content_index.md)
