# ISP 面试深度复盘笔记：Week1-Week4

这份笔记用于把基础 ISP pipeline 从“知道模块名”提升到“能解释顺序、假设、失败场景、调参和验证”的面试表达。

核心思路：

```text
入门回答：这个模块是什么
面试回答：为什么这样做、什么时候失效、怎么调、怎么验证
工程回答：数据域、性能、融合、画质风险和排查路径
```

## 1. RAW ISP Pipeline 顺序是什么？为什么这样排？

典型学习版 pipeline：

```text
RAW
-> BLC
-> DPC
-> LSC
-> Demosaic
-> AWB
-> CCM
-> Tone Mapping
-> Gamma
-> Preview / JPEG
```

每一步的数据域：

| 模块 | 输入 | 输出 | 数据域 |
|---|---|---|---|
| BLC | Bayer RAW | Bayer RAW | RAW 单通道，按 Bayer 位置区分 R/Gr/Gb/B |
| DPC | Bayer RAW | Bayer RAW | RAW 单通道，同色邻域 |
| LSC | Bayer RAW | Bayer RAW | RAW 单通道，空间 gain map |
| Demosaic | Bayer RAW | RGB | 从 Bayer 到三通道 RGB |
| AWB | RGB 或 RAW 统计 | RGB 或 RAW | 线性数据上的通道 gain |
| CCM | linear RGB | linear RGB | 三通道线性颜色空间 |
| Tone Mapping | linear RGB | 0..1 RGB | 动态范围压缩 |
| Gamma | 0..1 RGB | 非线性 RGB | 显示编码 |

面试表达：

```text
前端模块 BLC、DPC、LSC 主要在 Bayer RAW 域工作，因为它们处理的是 sensor/readout/lens 带来的原始问题。Demosaic 是数据域转换点，把 Bayer 变成 RGB。之后 AWB、CCM、Tone、Gamma 都在 RGB 或显示域工作，分别解决白平衡、颜色响应、动态范围和显示编码问题。
```

更深一层：

```text
顺序不是随便背的，而是由数据域和错误传播决定的。加性 offset 要先扣；坏点要在插值扩散前修；镜头位置相关 gain 要在 RAW 域按通道修；颜色矩阵和 tone/gamma 要在线性 RGB 或显示域做。
```

## 2. BLC 为什么要放在前面？Black level 错了会怎样？

BLC = Black Level Correction，黑电平校正。

Sensor/readout chain 会有 baseline offset。也就是说，即使没有光，RAW 值也可能不是 0，而是类似：

```text
真实有效信号：0..100
带 black level：20..120
```

BLC 做的是：

```text
raw_blc = raw - black_level
```

注意：BLC 减的是 offset，不是 gain。

Black level 的来源：

```text
1. DNG metadata，例如 raw.black_level_per_channel
2. 外部 tuning/config
3. sensor datasheet / dark frame calibration
4. 不同 gain、exposure、temperature 下的标定表
```

为什么要靠前：

```text
black level 是加性偏置。后面的 LSC、AWB、digital gain 等模块会乘 gain；如果不先减掉 offset，偏置会被当成真实光信号参与统计，甚至被后续 gain 一起放大。
```

错了会怎样：

| 问题 | 现象 |
|---|---|
| black level 扣少 | 暗部发灰，黑位不干净，动态范围变小 |
| black level 扣多 | 暗部 clip 到 0，阴影细节丢失 |
| 四通道 black level 不一致 | AWB/CCM 统计偏，暗部偏色 |
| BLC 放太晚 | LSC/AWB/Gamma 会放大 offset，后面更难补救 |

面试表达：

```text
BLC 要放前面，因为它修的是 sensor/readout 的加性基线偏置。后面很多模块默认输入代表真实光信号，如果不先扣 black level，暗部统计、AWB gain、DPC residual 和 tone/gamma 都会被污染，尤其乘法型模块还会把这个 offset 放大。
```

怎么验证 BLC：

```text
1. 看 dark frame 或黑场区域均值是否接近 0
2. 看暗部是否大量 clip
3. 看 R/Gr/Gb/B 四通道扣除后是否仍有明显 baseline 差异
4. 看 BLC 前后 histogram，黑位是否合理移动
```

## 3. DPC 为什么必须在 Demosaic 前？怎么区分坏点和真实纹理？

DPC = Defect Pixel Correction，坏点校正。

它处理的是：

```text
hot pixel：异常偏亮
dead pixel：异常偏暗
stuck pixel：卡在固定值
```

DPC 放在 Demosaic 前的原因：

```text
DPC 在 RAW 域看到的是孤立异常点；如果先 Demosaic，坏点会参与邻域插值，扩散到多个 RGB 像素和多个颜色通道，形成彩点、彩色纹路或局部伪影。
```

Bayer RAW 里相邻像素颜色不同：

```text
R  G  R  G
G  B  G  B
R  G  R  G
G  B  G  B
```

所以 DPC 不能直接拿上下左右比较，而必须按同色邻域判断：

```text
R 只和附近 R 比
Gr 只和附近 Gr 比
Gb 只和附近 Gb 比
B 只和附近 B 比
```

当前学习版算法：

```text
local_median = median(same_color_3x3_neighbors)
residual = abs(pixel - local_median)
threshold = max(min_delta, residual_median + mad_k * MAD(residual))

if residual > threshold:
    out = local_median
else:
    out = pixel
```

为什么用 median：

```text
median 对孤立异常值更稳健，不容易被单个 hot pixel 拉偏。mean 会被极端值影响。
```

怎么区分坏点和真实纹理/星点：

严格说不能百分百区分，只能靠假设和工程约束降低误检。

核心假设：

```text
坏点通常是孤立异常点。
真实纹理、边缘、星点、高光可能也很亮，但通常有空间结构、方向连续性或场景语义。
```

工程上会结合：

```text
1. 静态坏点表：出厂标定的固定坏点
2. 动态坏点检测：运行时检测 hot/dead pixel
3. ISO / exposure / temperature 自适应阈值
4. 同色邻域一致性判断
5. gradient repair：沿变化最小方向修复，避免抹边
6. 局部 crop 和 mask 可视化验证
```

参数影响：

| 参数 | 太低 | 太高 |
|---|---|---|
| min_delta / threshold | 误杀纹理、星点、高光边缘，图像变糊 | 漏掉坏点，后续 demosaic/锐化放大彩点 |
| mad_k | 检测更激进，误检风险高 | 检测更保守，漏检风险高 |
| repair_mode=median | 稳健但可能抹边 | 不适用 |
| repair_mode=gradient | 更保护边缘，但方向判断错误会引入结构伪影 | 不适用 |

面试表达：

```text
DPC 不可能完美区分坏点和所有真实细节，所以工程上会把它设计成保守检测。核心是按同色邻域找孤立异常点，再结合阈值、坏点表、ISO/温度和方向修复策略。DPC 的风险是误杀纹理和漏掉坏点，所以必须看 mask 数量、局部 crop、Demosaic 后彩点是否减少，以及纹理是否被抹。
```

## 4. LSC gain map 是什么？怎么标定？

LSC = Lens Shading Correction，镜头阴影校正。

它修的是：

```text
1. 亮度暗角：中心亮，边缘/四角暗
2. 色彩暗角：边缘不同颜色通道衰减不同，导致边缘偏色
```

gain map 是什么：

```text
一张随图像位置变化的增益表。每个位置都有一个应该乘的 gain。
```

简单例子：

```text
1.6  1.4  1.3  1.4  1.6
1.4  1.2  1.1  1.2  1.4
1.3  1.1  1.0  1.1  1.3
1.4  1.2  1.1  1.2  1.4
1.6  1.4  1.3  1.4  1.6
```

处理公式：

```text
raw_lsc(y, x) = raw_blc(y, x) * gain_map(y, x)
```

中心通常 gain 接近 1，边缘和四角 gain 更大。

LSC gain map 来源：

```text
1. 产品级：通过平场标定得到，写入 tuning/config/calibration table
2. 学习版：用径向模型生成，例如离中心越远 gain 越大
3. 某些离线 RAW：可能从 DNG metadata 或厂商私有数据读取
```

标定方法：

```text
1. 拍均匀平场图：积分球、均匀光源、漫反射白板/灰板
2. 先做 BLC，扣掉 black level
3. 按 Bayer 位置拆成 R/Gr/Gb/B 四个通道
4. 统计中心区域亮度和各网格区域亮度
5. gain(y, x) = center_mean / local_mean(y, x)
6. 对 gain table 平滑、降采样、限制最大 gain
7. 写入外部 tuning/config
```

为什么不是拍全黑：

```text
全黑图适合做 dark frame、black level、dark current 标定。LSC 需要有效光照下的空间衰减信息，所以应该拍均匀亮场，不是全黑。
```

为什么要四通道 R/Gr/Gb/B：

```text
镜头、微透镜、CRA 和 sensor color filter 对不同波段响应不同。边缘不仅会暗，还可能偏色，所以 R/G/B 的 shading 不一样。Bayer 里 G 又分 Gr/Gb 两个采样位置，工程上常常四通道分别建表。
```

LSC 修太强会怎样：

```text
1. 四角过亮，出现反向暗角
2. 边缘噪声被放大
3. 边缘颜色偏移被过度校正
4. 真实场景里的边缘阴影被误当成镜头暗角修掉
```

验证 LSC：

```text
1. 平场图中心/四角亮度 ratio 是否更接近 1
2. R/Gr/Gb/B 四通道边缘响应是否更一致
3. gain map 是否平滑，没有突变
4. 普通场景边缘是否过亮或噪声明显放大
```

## 5. Demosaic 为什么会偏绿？为什么不在 Demosaic 里修颜色？

Demosaic 的任务：

```text
Bayer 单通道 -> RGB 三通道
```

它做的是缺失颜色插值，不负责白平衡、颜色校正或显示映射。

Demosaic 后偏绿很常见，原因包括：

```text
1. Bayer 中绿色采样最多：RGGB 中 G 有两个，R/B 各一个
2. Demosaic 输出是 linear camera RGB，不是 sRGB
3. 还没有 AWB，光源和传感器通道比例没有校正
4. 还没有 CCM，camera RGB 没有映射到目标颜色空间
5. 简单 normalize preview 会让未完成 ISP 的颜色观感更怪
```

为什么不在 Demosaic 里修偏绿：

```text
算法职责要分清。Demosaic 负责空间插值，AWB 负责白点，CCM 负责颜色响应。如果在 Demosaic 里偷偷做 AWB/CCM，就很难判断图像变化到底来自插值算法、白平衡还是颜色矩阵，调试和验证都会混乱。
```

工程补充：

```text
工程实现里可以融合模块，例如 Demosaic 输出时顺手乘 AWB gain，或者硬件流水线里连续做 CFA + AWB + CCM。但算法意义上仍要区分模块职责。
```

Demosaic 常见伪影：

| 伪影 | 说明 |
|---|---|
| zipper | 边缘出现拉链状结构 |
| false color | 高频纹理处出现假彩色 |
| moire | 周期纹理出现摩尔纹 |
| blur | 插值导致细节变糊 |
| edge artifact | 斜边或强边缘处颜色错位 |

面试表达：

```text
Demosaic 后偏绿不一定是 Demosaic 错，而是因为它输出的是未完成 ISP 的 linear camera RGB。颜色是否准确应在 AWB、CCM、Tone/Gamma 后评价。Demosaic 本身主要看边缘、细节、false color、zipper 和 moire。
```

## 6. AWB 和 CCM 有什么区别？

AWB = Auto White Balance。

目标：

```text
修光源色偏，让中性物体更接近中性。
```

公式：

```text
R' = R * r_gain
G' = G * g_gain
B' = B * b_gain
```

它是通道独立缩放，可以写成对角矩阵，但不混合通道。

CCM = Color Correction Matrix。

目标：

```text
修相机传感器颜色响应，把 camera RGB 映射到目标颜色空间。
```

公式：

```text
R' = m00*R + m01*G + m02*B
G' = m10*R + m11*G + m12*B
B' = m20*R + m21*G + m22*B
```

它是 3x3 线性通道混合。

区别：

| 模块 | 解决问题 | 数学形式 | 是否混合通道 | 数据域 |
|---|---|---|---|---|
| AWB | 光源色偏，白点不白 | per-channel gain | 不混合 | 线性 RAW 或 RGB |
| CCM | 相机 RGB 与目标 RGB 不一致 | 3x3 matrix | 混合 | linear RGB |

为什么 AWB 不能替代 CCM：

```text
AWB 只能独立缩放 R/G/B，无法处理传感器滤光片响应与标准 RGB 之间的串扰。比如白墙已经白了，但肤色偏黄、草地过绿、蓝天偏青，这类颜色关系问题需要 CCM 通过通道混合修正。
```

为什么 CCM 要在线性 RGB 上做：

```text
CCM 是颜色空间的线性变换。只有在线性光强空间里，矩阵混合才有物理和颜色学意义。如果先做 Gamma，RGB 数值已经非线性，矩阵变换会破坏颜色关系。
```

CCM 后出现负值或超过 white level 怎么办：

```text
1. 后续 clip 到有效范围
2. 配合 tone mapping 压缩高亮
3. 调整 CCM，避免过强矩阵导致大量 out-of-gamut
4. 产品中用色卡拟合并加约束，例如保持中性灰、控制饱和度和肤色误差
```

CCM 会不会破坏中性灰：

```text
会，所以工程上要约束。常见约束是让每行和接近 1，使 [x, x, x] 输入后仍接近 [x, x, x]，也就是中性灰不明显偏色。
```

## 7. Gray World AWB 为什么会失败？怎么改进？

Gray World 假设：

```text
整张图平均颜色应该接近灰色，即 mean_R ≈ mean_G ≈ mean_B。
```

失败场景：

```text
1. 大面积草地：平均本来就偏绿
2. 大面积蓝天/海水：平均本来就偏蓝
3. 大面积红色物体：平均本来就偏红
4. 舞台灯/霓虹灯：光源本身带强色彩
5. 混合光源：全局一个 gain 无法同时修多个区域
6. 缺少灰白中性物体：没有可靠白点参考
```

怎么避免被高饱和区域骗：

```text
1. gray pixel selection：只选低饱和、亮度适中、未 clip 的像素
2. 排除大面积高饱和草地/蓝天/红花
3. 肤色、天空、植被场景识别
4. 使用 ROI 或中性区域
5. 融合 DNG/camera metadata 的白平衡
6. 限制 AWB gain 范围，避免估计过激
```

AWB gain 为什么要限制范围：

```text
极端 gain 会放大噪声、造成通道 clip 或把真实场景颜色强行拉偏。产品里通常会按色温范围、sensor 特性和场景类型限制 R/B gain，G gain 通常固定或接近 1。
```

AWB 和 AE/LSC/CCM 的耦合：

```text
AE 影响曝光和 clip，clip 区域不能可靠用于 AWB。
LSC 不准会让边缘颜色/亮度偏，污染全图 AWB 统计。
CCM 通常依赖 AWB 后的白点稳定，否则颜色矩阵的效果也会偏。
```

验证 AWB：

```text
1. 灰白 ROI 的 R/G/B 是否更接近
2. AWB gain 是否在合理范围
3. 大面积单色场景是否被过度拉偏
4. 和 rawpy/camera JPEG 的白平衡趋势是否一致
```

## 8. Gamma 和 Tone Mapping 有什么区别？

Tone Mapping 解决：

```text
动态范围太大，显示器装不下。
```

RAW/linear RGB 可能有很亮的高光。如果直接线性压到 0..1，会遇到：

```text
保高光 -> 中间调太暗
保主体 -> 高光死白
```

Tone Mapping 决定：

```text
暗部、中间调、高光如何压进显示范围。
```

例如 Reinhard：

```text
y = x / (1 + x)
```

当 x 很大时，y 会逐渐接近 1，从而柔和压高光。

Gamma 解决：

```text
线性亮度不适合直接显示，也不符合常见显示编码和人眼感知。
```

常见近似：

```text
y = x^(1/2.2)
```

它会抬高中间调，让线性图看起来不那么暗。

区别：

| 模块 | 解决问题 | 典型输入 | 典型输出 |
|---|---|---|---|
| Tone Mapping | 动态范围压缩，高光/暗部/中间调取舍 | linear RGB / HDR-like RGB | 0..1 display range |
| Gamma | 显示编码，感知亮度映射 | 0..1 linear/display RGB | 非线性 RGB |

顺序：

```text
linear RGB -> Tone Mapping -> Gamma -> uint8 preview
```

为什么 Tone Mapping 要在 Gamma 前：

```text
Tone Mapping 应该处理线性光强，这样压高光和保中间调的曲线含义清楚。如果先做 Gamma，数值已经非线性，再做 tone curve 就不再对应真实亮度关系。
```

Gamma 和 sRGB OETF 是不是一回事：

```text
不完全是。简单 gamma 1/2.2 是近似；sRGB OETF 是分段曲线，暗部有线性段，高亮部分接近幂函数。学习项目里常用 gamma 近似，产品/标准输出应使用标准 sRGB OETF。
```

Reinhard 曲线的问题：

```text
1. 高光压缩柔和，但整体可能偏灰
2. 局部对比不足
3. 不一定接近相机 JPEG/rawpy 的 tone curve
4. 复杂场景需要局部 tone mapping 或更精细曲线
```

PSNR 高但主观看起来差，为什么：

```text
PSNR/SSIM 对像素级差异敏感，但 tone/color 的主观偏好不一定和逐像素误差一致。一个图 PSNR 高可能只是亮度曲线接近 reference，但颜色、局部对比或高光观感未必最好。
```

## 9. 画质问题怎么按 pipeline 排查？

### 9.1 画面整体偏绿

排查路径：

```text
1. BLC：四通道 black level 是否正确，暗部是否某通道 baseline 偏高
2. Demosaic：输出是否只是未校正的 camera RGB，偏绿是否正常
3. AWB：gray/white ROI 是否中性，gain 是否估错
4. LSC：边缘或全图绿色通道 gain 是否异常
5. CCM：camera RGB 是否正确映射到目标 RGB
6. Tone/Gamma/Preview：显示映射是否放大绿感
```

面试表达：

```text
我不会直接说是 AWB 的锅，会先看数据域。Demosaic 后偏绿可能只是 camera RGB 未校正；AWB 后灰白仍偏绿才说明白平衡有问题；如果灰白正常但肤色/草地不准，更多要看 CCM。
```

### 9.2 四角偏暗或偏色

优先看：

```text
1. LSC gain map 是否正确
2. R/Gr/Gb/B 四通道 shading 是否分别校正
3. 标定光源和当前镜头/焦距/色温是否匹配
4. 边缘是否过度放大噪声
```

验证：

```text
中心/四角亮度 ratio
四通道 gain map
平场图前后对比
普通场景边缘是否反向过亮
```

### 9.3 暗部发灰

可能原因：

```text
1. BLC 扣少，black level 残留
2. LSC/AWB/digital gain 放大了 offset
3. Tone/Gamma 曲线抬暗部过强
4. 黑位 clip/level 设置不合理
```

### 9.4 图像有小亮点，Demosaic 后更明显

可能原因：

```text
DPC 漏检 hot pixel。坏点在 RAW 中是单点，但 Demosaic 插值后会扩散到多个 RGB 像素和颜色通道，后续锐化还会进一步放大。
```

### 9.5 边缘有彩边/假彩

可能原因：

```text
1. Demosaic 算法太简单，例如 bilinear 跨边缘插值
2. DPC/denoise 误伤边缘
3. LSC/AWB/CCM 放大通道差异
4. 后续 sharpening 或 false color suppression 不足
```

## 10. 哪些模块可以融合？工程上为什么要融合？

教学上拆模块：

```text
BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone -> Gamma
```

工程上可以融合：

```text
RAW 前端 block：BLC + DPC + LSC
CFA/RGB block：Demosaic + AWB gain
Color block：CCM + LUT/Gamma/Tone
```

融合的目的：

```text
1. 减少内存读写
2. 减少延迟
3. 复用 line buffer
4. 减少中间结果存储
5. 更适合硬件 ISP、GPU shader 或 SIMD pipeline
```

但融合有前提：

```text
1. 数据域兼容
2. 数学等价或画质可接受
3. 参数仍然可调
4. 问题仍然可定位
5. 融合前后结果可验证
```

适合融合的：

```text
1. 加性 offset：BLC
2. 逐像素乘法：digital gain、AWB gain、LSC gain
3. 通道线性变换：CCM
4. 某些 LUT/curve：Gamma、tone curve
```

不适合随便融合的：

```text
1. 需要邻域判断的 DPC
2. 需要邻域插值的 Demosaic
3. 需要全局统计的 AWB estimation
4. 需要复杂局部决策的 local tone mapping
```

面试表达：

```text
算法理解上应该拆模块，工程部署上可以融合实现。融合不是把概念混在一起，而是在保证数据域一致、数学等价、调参可控和画质不变的前提下，减少内存带宽和延迟。
```

## 11. 八个高频问题的面试版回答

### 11.1 RAW ISP pipeline 顺序和每一步作用？

```text
典型流程是 RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma。BLC 扣 sensor baseline，DPC 修 RAW 域坏点，LSC 修镜头暗角和边缘色偏，Demosaic 把 Bayer 转 RGB，AWB 修光源白点，CCM 修 camera RGB 到目标 RGB 的颜色响应，Tone 压动态范围，Gamma 做显示编码。
```

### 11.2 BLC 为什么要先做？black level 错了会怎样？

```text
BLC 修的是加性 offset，必须在乘法型和统计型模块前做。如果 black level 扣少，暗部发灰、AWB/DPC 统计偏；扣多会 clip 阴影细节；四通道 black level 不一致会造成暗部偏色。因为后续 LSC、AWB、digital gain 会放大 offset，所以 BLC 要靠前。
```

### 11.3 DPC 为什么按同色邻域判断？

```text
Bayer 相邻像素颜色不同，R 和 G 数值不同不代表异常。DPC 判断的是当前像素相对同色邻居是否孤立异常，所以必须按 R/Gr/Gb/B 同色网格比较。这样能在 Demosaic 扩散前修掉 hot/dead pixel。
```

### 11.4 LSC gain map 是什么，怎么标定？

```text
LSC gain map 是随空间位置变化的增益表，用来补偿中心亮、边缘暗以及边缘偏色。标定时拍均匀平场，BLC 后按 R/Gr/Gb/B 分通道统计中心和各区域亮度，用 center_mean/local_mean 得到 gain，再平滑降采样写入 tuning。
```

### 11.5 Demosaic 后为什么会偏绿，为什么不在 Demosaic 里修？

```text
Demosaic 后是 linear camera RGB，不是最终 sRGB。Bayer 里绿色采样多，且还没 AWB/CCM，所以偏绿常见。Demosaic 负责插值，不负责白平衡和颜色空间转换；工程上可以融合实现，但算法职责要分开，否则很难调试和验证。
```

### 11.6 AWB 和 CCM 的区别？

```text
AWB 是通道 gain，修光源色偏，让中性物体更中性；CCM 是 3x3 线性矩阵，修相机颜色响应，把 camera RGB 映射到目标 RGB。AWB 不混合通道，CCM 会混合通道。白墙白了但肤色不准时，通常需要 CCM 而不是继续调 AWB。
```

### 11.7 Gamma 和 Tone Mapping 的区别？

```text
Tone Mapping 压动态范围，决定高光、暗部和中间调怎么进入显示范围；Gamma 做显示编码，让 0..1 线性亮度变成适合显示/感知的非线性值。通常 linear RGB 先 tone mapping，再 gamma。
```

### 11.8 如果画面偏绿、四角暗、有彩点，怎么排查？

```text
偏绿：先看 BLC baseline，再看 AWB gray ROI，再看 CCM 和 preview。四角暗/偏色：查 LSC gain map、四通道 shading 和标定匹配。有彩点：优先看 DPC 是否漏检，Demosaic 是否把坏点扩散，后续 sharpening 是否放大。
```

## 12. 最终压缩记忆版

```text
BLC：减 offset，越早越好，因为后面 gain 会放大 offset。
DPC：找孤立坏点，必须按同色邻域，在 Demosaic 前做。
LSC：乘空间 gain map，修中心到边缘的亮度/颜色不一致。
Demosaic：Bayer 插值成 RGB，重点看 zipper、false color、moire。
AWB：通道 gain，修光源白点，Gray World 会被大面积单色骗。
CCM：3x3 线性通道混合，修 camera RGB 到目标 RGB。
Tone Mapping：压动态范围，处理高光/暗部/中间调。
Gamma：显示编码，把线性亮度变成非线性显示值。
```

面试答题框架：

```text
这个模块解决什么问题？
它依赖什么假设？
它什么时候会失败？
失败后怎么调参和验证？
工程上能不能融合，代价是什么？
```
