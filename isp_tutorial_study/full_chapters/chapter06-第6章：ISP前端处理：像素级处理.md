<!-- 来源：https://zsc.github.io/isp_tutorial/chapter6.html -->

# 第6章：ISP前端处理：像素级处理



### 1. 本章先解决什么问题

第 4 章和第 5 章主要处理“整幅图像或大范围区域”的偏差，例如黑电平、暗电流、平场、镜头阴影。第 6 章换到更细的一层：单个像素或一小簇像素坏了怎么办。

初学者可以先把图像传感器想成一张由几百万到上亿个小测量仪组成的表格。理想情况下，每个小测量仪都应该对光照有相似响应；现实中总会有少数像素因为制造缺陷、材料杂质、暗电流异常、老化、温度变化或辐射损伤而输出异常值。这些异常值就是本章说的 bad pixel、defect pixel、hot pixel、dead pixel、stuck pixel 等。

坏点处理必须放在 ISP 前端，原因很直接：RAW 里一个坏点还是一个采样点；一旦经过 demosaic、denoise、sharpen、tone mapping，它可能扩散成彩点、彩线、局部伪色、锐化光斑，甚至被后续算法当成真实纹理放大。越晚处理，越难判断它到底是传感器缺陷还是图像内容。

本章最小链路是：

```text
输入：BLC 后的线性 Bayer RAW + 可选坏点表 + 当前曝光/增益/温度信息
处理：静态坏点查表、动态坏点检测、同色邻域修复、簇状缺陷处理、坏点地图更新
输出：坏点已被替换的 Bayer RAW + 可选坏点统计/置信度/更新后的坏点表
```

读完本章，至少要能回答四个问题：

- 为什么坏点要尽量在 Bayer RAW 阶段修，而不是等到 RGB 图像阶段再修。
- hot、dead、stuck、blinking、cluster defect 分别是什么现象。
- 静态坏点表和动态坏点检测各自适合解决什么问题。
- 为什么“把坏点换成周围像素平均值”听起来简单，实际却容易破坏边缘、纹理和颜色。

### 2. 坏点到底坏在哪里

坏点不是一个单一概念，而是一组传感器异常。很多资料会把 bad pixel 和 defective pixel 混用，但工程上最好按“输出行为”分类，因为不同类型的检测和修复策略不一样。

| 类型 | 直觉现象 | RAW 中的表现 | 常见原因 | 处理重点 |
|---|---|---|---|---|
| Hot pixel | 黑暗中冒出来的亮点 | 暗场下明显高于同类邻域 | 暗电流异常、温度升高、长曝光 | 暗场标定、温度/曝光相关阈值 |
| Dead pixel | 怎么照都不亮 | 平场下明显低于同类邻域 | 光电二极管失效、读出链路异常 | 平场检测、同色插值替换 |
| Stuck-high | 总是接近满量程 | 多种光照下接近饱和 | ADC/读出电路或像素节点异常 | 饱和保护、静态表优先 |
| Stuck-low | 总是接近黑电平 | 多种光照下接近最低值 | 读出失败或像素无响应 | BLC 后检查低异常值 |
| Noisy pixel | 不一定偏亮偏暗，但抖动大 | 时间方差明显高 | 漏电、读出噪声异常 | 多帧统计，不能只看单帧 |
| Blinking pixel | 时好时坏 | 某些帧突然异常 | 亚稳态缺陷、温度/电压敏感 | 时域置信度更新 |
| Nonlinear pixel | 暗处正常，亮处异常 | 响应曲线斜率异常 | 满阱、电荷转移或读出非线性 | 多级灰度标定 |
| Cluster defect | 一片或一条坏点 | 相邻多个像素异常 | 制造缺陷、列/行读出链路问题 | 不能只用单点邻域平均 |

这里有一个很重要的学习点：坏点不一定永远是“白点”。很多初学者只把坏点理解成照片里的亮点，这是不够的。真实 ISP 里，坏点可以是过亮、过暗、响应斜率错误、噪声过大、间歇性异常，甚至是一整列读出不稳定。

### 3. 为什么必须理解 Bayer 同色邻域

大多数相机传感器不是每个像素同时记录 R、G、B 三个值，而是通过 CFA 让每个像素只记录一个颜色分量。最常见的 Bayer 排列里，一个 2x2 单元通常是：

```text
R  G
G  B
```

这意味着 RAW 中坐标 `(x, y)` 的一个像素只属于 R、Gr、Gb 或 B 中的一类。若一个 R 像素坏了，最自然的参考对象不是上下左右紧挨着的 G 或 B，而是距离它最近的其他 R 像素。因为 G/B 像素测量的是不同光谱通道，直接拿来平均会把颜色信息混进去，修出来的值可能在 demosaic 后变成彩色伪影。

一个简单例子：

```text
R 像素坏点 = 4095
周围最近的 G 像素大约 = 800
周围同色 R 像素大约 = 1200, 1180, 1220, 1190
```

如果直接用周围所有像素平均，结果会被 G/B 通道拉偏；如果用同色 R 邻域中值或方向插值，替换值大约在 1200 附近，更符合这个位置本来应该有的红色响应。

因此，BPC/DPC 的核心不是“图像上一个点坏了，随便补一下”，而是：

```text
先判断该坐标属于哪个 CFA 相位 -> 只在同色或同相位邻域中判断异常 -> 用同色结构估计替换值
```

### 4. 静态坏点表：工厂标定能解决什么

静态坏点表也叫 defect pixel map、defect table、static defect list。工业相机文档里经常能看到这类功能：相机内部保存一份缺陷像素列表，运行时根据坐标直接替换这些像素。Basler 等工业相机资料把它描述为用静态缺陷像素校正来减小单个传感器像素灵敏度差异的影响；AMD Vitis Vision 的 ISP pipeline 也把 BPC 放在前端 Bayer 流程中，说明坏点可能来自制造缺陷，也会受温度或曝光影响。

静态表的优势是稳定、便宜、实时性好。硬件只要检查当前像素坐标是否在坏点表里，命中就替换，不需要复杂判断。它适合处理出厂时已经发现的 dead pixel、stuck pixel、固定 hot pixel、部分响应异常像素。

典型标定流程可以这样理解：

1. 暗场采集：盖住镜头，在多个曝光时间、多个增益、多个温度条件下拍 RAW，找出暗场中过亮或方差异常的像素。
2. 平场采集：用积分球或均匀光源照明，在多个亮度下拍 RAW，找出响应过低、过高或 PRNU 异常的像素。
3. 多级灰度：改变照度，观察每个像素响应曲线是否接近线性，找出非线性响应像素。
4. 坐标压缩：把坏点坐标、坏点类型、置信度、适用 sensor mode 写成表。
5. 运行时查表：ISP 在逐像素流过时检查坐标，命中则执行修复。

静态表也有明显局限：

- 新产生的坏点无法自动进入表。
- hot pixel 会随温度、曝光时间变化，低温短曝光时可能看不出来。
- 不同 sensor mode 会改变读出区域、binning、skipping 或 crop，坏点坐标可能需要映射。
- 坏点表太大时，硬件查表和片上存储会变成成本问题。

所以实际系统通常不会只依赖静态表，而是静态表加动态检测组合使用。

### 5. 动态坏点检测：实时判断这个像素像不像异常值

动态检测的直觉是：真实图像虽然有边缘和纹理，但同一颜色通道的邻域通常不会只有一个像素离谱地跳出去。如果当前像素比同色邻域都亮很多或暗很多，它很可能是坏点。

一个最小的同色邻域检测可以写成：

```text
center = 当前 Bayer 像素
neighbors = 周围同色像素集合
median = neighbors 的中值
diff = abs(center - median)
若 diff > threshold，则认为 center 是候选坏点
```

关键变量解释：

- `center`：当前待检测像素，通常已经完成黑电平校正。
- `neighbors`：同色邻域，例如 5x5 窗口内与 center 同 CFA 相位的像素。
- `median`：邻域中值，比均值更不容易被另一个异常点带偏。
- `threshold`：检测阈值，可以是固定值，也可以随局部噪声、增益、亮度、温度变化。

一个数值例子：

```text
center = 3800
同色邻域 = [1180, 1195, 1210, 1205, 1170, 1220, 1190, 1215]
median ≈ 1200
diff = 2600
threshold = 300
结论：center 很可能是 hot/stuck-high 像素
```

再看一个容易误检的例子：

```text
center = 3800
同色邻域 = [900, 1100, 1500, 2300, 3000, 3500, 3900, 4000]
median ≈ 2650
diff = 1150
```

这不一定是坏点，可能是真实高光边缘或强纹理。只用中值阈值会有风险，所以动态 DPC 常加边缘保护、方向判断、饱和保护和局部结构分析。

### 6. 阈值为什么不能随便设

坏点检测最难的部分不是“找到异常点”，而是同时控制误检和漏检。

| 阈值设置 | 好处 | 风险 | 图像后果 |
|---|---|---|---|
| 阈值太低 | 能抓到更多弱坏点 | 容易把纹理、星点、文字边缘误判为坏点 | 细节被抹掉，边缘变软 |
| 阈值太高 | 不容易破坏真实内容 | 漏掉轻微坏点和温度相关 hot pixel | demosaic 后出现彩点和彩斑 |
| 固定阈值 | 实现简单 | 不适应增益、曝光、噪声变化 | 高 ISO 下误检或低 ISO 下漏检 |
| 自适应阈值 | 更贴近真实噪声 | 参数更多，验证更复杂 | 调不好会出现局部不一致 |

阈值至少应该考虑这些因素：

- 亮度：暗区噪声分布和亮区 shot noise 不一样。
- 增益：模拟/数字增益升高后，正常噪声也会变大。
- 曝光时间：长曝光下 hot pixel 更明显。
- 温度：暗电流通常随温度升高快速增加。
- CFA 相位：R、Gr、Gb、B 的响应和噪声可能不同。
- sensor mode：binning、HDR、crop、不同帧率会改变数据统计。

这也是为什么工业相机和硬件 ISP 往往提供 DPC 阈值、坏点表、校正开关、模式相关参数，而不是一个永远固定的魔法数字。

### 7. 坏点修复：不是所有平均都合理

检测出坏点之后，要把它替换成一个合理估计值。常见修复方法从简单到复杂大致如下。

| 方法 | 思路 | 优点 | 风险 |
|---|---|---|---|
| 同色中值 | 用同色邻域中值替换 | 鲁棒、硬件友好 | 边缘方向感弱 |
| 同色均值 | 用同色邻域平均 | 简单、平滑 | 容易被异常点影响 |
| 方向插值 | 沿最平滑方向估计 | 边缘保护更好 | 方向判断错误会拉出纹理 |
| 加权插值 | 按距离/梯度/置信度加权 | 质量更高 | 硬件成本更高 |
| 多帧修复 | 利用前后帧或时域统计 | 对 blinking/noisy pixel 有帮助 | 运动场景容易错配 |
| 图像修复/inpainting | 用更大范围结构补洞 | 适合较大缺陷 | 前端实时 ISP 中成本高 |

最常见的前端硬件实现仍然偏向小窗口同色中值或方向插值。原因不是它最“聪明”，而是它足够稳定、低延迟、可流水、容易验证。

一个方向插值的直觉例子：

```text
如果水平同色邻域差异小，垂直方向差异大：
优先用左右同色像素估计 center。

如果垂直同色邻域差异小，水平方向差异大：
优先用上下同色像素估计 center。
```

这样做的目的，是避免跨越边缘去平均。比如一条黑白边界上，左右可能属于同一物体表面，上下可能跨过边界；如果方向选错，坏点虽然被替换了，但边缘会被糊掉。

### 8. 簇状缺陷、行列缺陷为什么更麻烦

单个坏点比较容易修，因为它周围通常还有足够多的正常同色像素。Cluster defect、row defect、column defect 更难，因为局部参考也可能坏了。

常见情况包括：

- 2 个相邻坏点：简单中值还能处理，但方向选择要更小心。
- 3x3 或更大坏点块：中心像素附近可能没有可靠参考，需要更大窗口。
- 一整列异常：可能是列读出链路问题，不能按单点独立处理。
- 一整行异常：可能和行驱动或时序有关，可能需要行级补偿。
- CFA 相位相关缺陷：只影响某一类颜色相位，demosaic 后会表现成偏色纹理。

修复策略也会升级：

```text
单点坏点 -> 小窗口同色中值/方向插值
小簇坏点 -> 扩大窗口，避开已知坏点，按边缘方向补
行列坏点 -> 用左右/上下多行统计，必要时做行列级模型
大面积缺陷 -> 前端 BPC 只能减轻，可能需要后端修复或直接判定传感器不可用
```

初学者要记住一个边界：BPC 是“缺陷像素修补”，不是万能的图像修复。坏点数量太多、坏块太大、行列缺陷太严重时，算法可以掩盖一部分视觉问题，但无法凭空恢复真实细节。

### 9. 坏点处理和前后模块的关系

像素级处理在 pipeline 中的位置非常关键。一个常见顺序是：

```text
RAW 输入 -> 黑电平校正 BLC -> 坏点检测/校正 BPC/DPC -> 镜头阴影校正 LSC -> 去噪 -> demosaic -> 后续颜色与增强
```

为什么通常在 BLC 后面？因为黑电平偏置会影响异常判断。比如某个像素看起来偏亮，可能只是黑电平没有正确扣除。先做 BLC，可以让坏点检测看到更接近真实光电响应的数值。

为什么通常在 LSC、denoise、demosaic 前面？原因分别是：

- LSC 会对边缘区域施加较大增益，如果坏点没修，边缘 hot pixel 会被进一步放大。
- Denoise 可能把单个坏点当成局部结构或强噪声处理，既可能抹掉真实细节，也可能残留异常。
- Demosaic 会用邻域插值生成完整 RGB，坏点会从一个 Bayer 采样扩散到多个 RGB 像素。
- Sharpen 会增强局部高频，坏点漏检后可能变得更刺眼。

不过“BLC 后、LSC 前”不是永恒规则。某些系统会根据硬件架构、片上 ISP 顺序、坏点表坐标、HDR 合成位置来调整。学习时先掌握默认逻辑，再理解例外。

### 10. 硬件实现为什么特别关心窗口、缓存和吞吐

坏点处理听起来像一个小算法，但在 ISP 硬件里它是逐像素、逐帧、实时运行的模块。对 4K 60fps 或更高分辨率来说，每秒要处理几亿个像素，不能随意访问整幅图像。

硬件实现通常要考虑：

- 窗口大小：3x3 成本低但同色参考少；5x5/7x7 更稳但 line buffer 更多。
- line buffer：流式处理只能缓存有限行，窗口越大，片上 SRAM 越多。
- CFA 相位：不同坐标要选择不同同色邻居，边界处理要固定。
- 坏点表查找：坐标表可能需要排序、压缩、分块或 CAM/BRAM 查询。
- 阈值寄存器：不同颜色通道、不同亮度区间、不同模式可能有不同阈值。
- 位宽增长：BLC、LSC、HDR 之后数据位宽不同，比较和插值要防止溢出或截断。
- 延迟：BPC 增加的行缓存和流水延迟要能被后续模块接受。
- 可验证性：硬件输出要能和软件 golden model 做逐像素对齐。

一个简单资源直觉：

```text
3x3 窗口：需要缓存约 2 行历史数据，适合低成本单点检测。
5x5 窗口：需要缓存约 4 行历史数据，同色参考更多，检测更稳。
7x7 窗口：更适合复杂缺陷和边缘保护，但资源和延迟更高。
```

所以论文里很复杂的图像修复方法，不一定适合放进前端硬件 ISP。工程里常见的方案往往看起来朴素，但它们能稳定跑满吞吐、参数可控、故障模式清楚。

### 11. 最小可验证实验

建议用一个小 RAW Bayer 数组或真实 RAW crop 做实验。没有真实坏点也没关系，可以人工注入。

实验 1：观察坏点在 demosaic 后如何扩散。

1. 取一张干净 Bayer RAW。
2. 在 R、Gr、Gb、B 不同相位各注入几个值为满量程的 hot pixel。
3. 不做 BPC，直接 demosaic 成 RGB。
4. 观察坏点是否变成彩点、彩斑或小范围伪色。
5. 再在 demosaic 前用同色中值修复，比较结果。

实验 2：比较同色修复和普通均值修复。

1. 在一条高反差边缘附近注入 dead pixel。
2. 方法 A：用 3x3 所有邻居均值替换。
3. 方法 B：用 5x5 同色邻域中值替换。
4. 方法 C：用方向插值替换。
5. 对比边缘是否变软、是否产生偏色。

实验 3：调阈值看误检和漏检。

1. 在平坦区域、纹理区域、高光区域分别注入坏点。
2. 从低阈值到高阈值扫一遍。
3. 记录每组阈值下的 true positive、false positive、false negative。
4. 观察低阈值是否破坏纹理，高阈值是否漏掉弱 hot pixel。

实验 4：模拟 blinking pixel。

1. 连续 20 帧中，让某个坐标只在第 5、11、17 帧异常。
2. 单帧检测可能每次只看到孤立异常。
3. 加入时域计数或置信度后，观察它是否能被稳定加入候选坏点表。

### 12. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 暗处有固定亮点 | hot pixel 漏检，长曝光阈值不够 | 暗场 RAW、曝光时间、温度相关阈值 |
| demosaic 后有彩色小点 | Bayer 阶段未修或修复相位错误 | 检查 BPC 是否在 demosaic 前，CFA pattern 是否正确 |
| 纹理变糊 | 阈值太低，真实细节被当坏点 | 查看 false positive，增加边缘保护 |
| 高光边缘被打碎 | 饱和点被误判为坏点 | 加饱和保护和局部结构判断 |
| 画面边缘坏点更明显 | LSC 放大了未修坏点 | 检查 BPC 与 LSC 顺序、边缘阈值 |
| 某一列持续异常 | 不是单点坏点，而是列缺陷 | 做列统计，检查读出链路或列级补偿 |
| 不同分辨率模式下修错位置 | 坏点表坐标未随 crop/binning 映射 | 检查 sensor mode 坐标转换 |
| 高温下坏点突然变多 | 暗电流和 hot pixel 增加 | 建立温度分档或动态检测策略 |

### 13. 常见误区

- 误区 1：坏点就是亮点。实际上 dead、stuck-low、noisy、nonlinear、blinking 都属于缺陷像素问题。
- 误区 2：RGB 阶段修也一样。Bayer 阶段不修，demosaic 会把一个异常采样扩散到多个颜色通道。
- 误区 3：邻域平均最简单所以最可靠。平均会跨颜色、跨边缘、受异常邻居影响；同色中值和方向插值通常更稳。
- 误区 4：静态坏点表一次标定就永远够用。温度、曝光、老化、辐射和 sensor mode 都会改变坏点表现。
- 误区 5：阈值越低越好。阈值太低会把真实纹理和星点当成坏点，画面会失去细节。
- 误区 6：BPC 可以修复任何坏块。大面积缺陷和行列级故障已经超出普通单点 BPC 的能力边界。
- 误区 7：只看最终 RGB 图就能调好。很多问题必须回到 RAW、CFA 相位和模块顺序上定位。

### 14. 学习优先级

必须掌握：

- 坏点类型及其 RAW 表现。
- BPC/DPC 的输入、输出和 pipeline 位置。
- Bayer 同色邻域修复的原因。
- 静态坏点表和动态检测的区别。
- 阈值过高、过低分别会造成什么后果。

了解即可：

- 多温度、多曝光、多灰阶工厂标定流程。
- 坏点表压缩、硬件查找和寄存器配置。
- 时域置信度更新、blinking pixel 追踪。
- cluster defect、行列缺陷的更复杂修复。

后面再回看：

- 论文中的稀疏建模、图像修复、多帧光流补偿等复杂方法。
- 高吞吐硬件中的 line buffer、BRAM、流水线延迟和 golden model 对齐。
- HDR、binning、多摄同步场景下的坏点坐标映射。

### 15. 自测题

1. 为什么同一个 hot pixel 在 RAW 里只是一个点，到了 RGB 图里可能变成彩色伪影？
2. 一个 R 像素坏了，为什么不能直接用上下左右最近的像素平均替换？
3. 静态坏点表能解决哪些问题？它不能解决哪些问题？
4. 动态检测阈值太低和太高分别会造成什么画质后果？
5. 为什么 BPC 通常放在 BLC 后、LSC 和 demosaic 前？
6. 如果高温长曝光下突然出现很多亮点，你会优先检查哪些参数和输入数据？
7. 如何设计一个最小实验，证明“demosaic 前修坏点”优于“demosaic 后修坏点”？
8. 如果某一整列像素异常，为什么不能只把它当成很多独立单点坏点处理？

### 16. 读完本章的验收标准

合格的学习结果不是“知道 BPC 这个缩写”，而是能做到：

- 口头解释：能用 2 分钟讲清 bad pixel 从传感器异常到 RGB 伪影的传播路径。
- 输入输出：能写出 BPC/DPC 的输入、处理、输出，不把它和 RGB 去噪混在一起。
- 图像判断：看到亮点、暗点、彩点、列缺陷、纹理变糊时，能提出合理排查方向。
- 算法理解：能写出一个同色中值检测和修复的最小伪代码。
- 参数判断：能说出阈值、窗口、CFA pattern、sensor mode、温度和曝光为什么会影响结果。
- 实验验证：能人工注入坏点，对比不修、普通均值修、同色中值修、方向修复的差异。

### 17. 推荐资料与进一步阅读

- [AMD Vitis Vision ISP pipeline 文档](https://docs.amd.com/r/2023.1-English/Vitis_Libraries/vision/overview.html_3_8)：把 BPC 放在 Bayer ISP 前端，并说明坏点可能来自制造缺陷、温度和曝光相关变化。
- [Basler Defect Pixel Correction 文档](https://docs.baslerweb.com/defect-pixel-correction)：工业相机中静态缺陷像素校正的工程语境，可帮助理解坏点表和相机固件功能。
- [Infinite-ISP 开源项目](https://github.com/10x-Engineers/Infinite-ISP)：可参考硬件 ISP 中前端模块、Bayer 流和可综合实现方式。
- [openISP 开源项目](https://github.com/cruxopen/openISP)：可作为学习 RAW pipeline、模块顺序和软件 ISP 实验的参考。
- [Adaptive pixel defect correction](https://www.researchgate.net/publication/228575028_Adaptive_pixel_defect_correction)：围绕 CFA/RAW 缺陷像素补偿的论文资料，可重点关注同色采样点和插值思想。
- [Robust defect pixel detection and correction for Bayer imaging systems](https://library.imaging.org/ei/articles/29/15/art00008)：Bayer 成像系统中缺陷像素检测与修复的论文资料，可用于理解误检、修复质量和边缘保护问题。



在图像传感器的制造和使用过程中，由于工艺缺陷、材料杂质、宇宙射线撞击以及器件老化等因素，不可避免地会产生缺陷像素。这些缺陷像素如果不加以处理，会在最终图像中形成明显的亮点、暗点或彩色噪点，严重影响图像质量。本章将深入探讨ISP中像素级处理的核心技术，包括缺陷像素的检测、分类、修复以及动态管理策略。我们将从物理机理出发，结合自动驾驶和具身智能场景的特殊需求，系统阐述各种算法的原理、实现和优化方法。


## 6.1 Bad Pixel Detection算法：静态与动态检测


### 6.1.1 坏点的物理成因与表现形式


缺陷像素的产生源于多种物理机制。在制造阶段，硅晶圆中的晶格缺陷、金属杂质污染以及光刻工艺偏差都可能导致像素功能异常。使用过程中，宇宙射线撞击会在硅材料中产生电子-空穴对，造成瞬时或永久性损伤；器件老化则表现为暗电流增加和量子效率下降。


从信号特性角度，缺陷像素可分为以下几类：


**固定型缺陷**：输出值恒定或严重偏离正常范围


- Stuck-high像素：始终输出最大值或接近最大值
- Stuck-low像素：始终输出最小值或接近最小值
- 固定模式噪声（FPN）：输出值偏离正常但保持相对稳定


**响应异常型缺陷**：光电转换特性异常


- 灵敏度异常：量子效率显著偏离正常值
- 非线性响应：光电转换曲线严重失真
- 串扰缺陷：与相邻像素存在异常耦合


**时变型缺陷**：缺陷特性随时间或环境变化


- 闪烁像素（Blinking Pixel）：间歇性失效
- 温度敏感像素：高温下表现为热像素
- 渐变退化像素：性能逐渐恶化


### 6.1.2 静态检测方法：工厂标定与离线检测


静态检测通常在受控环境下进行，能够获得高精度的缺陷像素位置图。工厂标定是最可靠的检测方法，通过多种测试条件全面评估每个像素的性能。


**暗场检测**用于识别热像素和暗电流异常：


1. 在完全黑暗环境下，传感器进行多次曝光
2. 统计每个像素的输出均值 $\mu_i$ 和方差 $\sigma_i^2$
3. 检测准则： \(P_{hot} = \{i : \mu_i > \mu_{global} + k_1 \cdot \sigma_{global}\}\) 其中 $k_1$ 典型值为5-7，取决于误检容忍度


**均匀光场检测**评估像素的光响应一致性：


1. 使用积分球提供均匀照明
2. 在多个光强下测量响应
3. 计算光响应非均匀性（PRNU）： \(PRNU_i = \frac{|R_i - \bar{R}|}{\bar{R}} \times 100\%\)
4. 标记PRNU超过阈值（典型5-10%）的像素


**多级灰度检测**通过完整的光响应曲线识别非线性缺陷：
\(DNL_i = \max_{j} \left| \frac{dR_i}{dL}|_{L_j} - \frac{d\bar{R}}{dL}|_{L_j} \right|\)
其中 $L_j$ 表示不同的照度级别。


### 6.1.3 动态检测算法：实时统计分析


动态检测在ISP运行时实时进行，能够发现新产生的缺陷并适应环境变化。核心思想是通过局部统计分析识别异常像素。


**基于邻域统计的检测**是最常用的方法。对于待检测像素 $p(x,y)$，定义其邻域窗口 $\Omega_{x,y}$（通常为5×5或7×7），计算局部统计量：


<table>
  <tbody>
    <tr>
      <td>均值：$\mu_{local} = \frac{1}{</td>
      <td>\Omega</td>
      <td>} \sum_{(i,j) \in \Omega, (i,j) \neq (x,y)} p(i,j)$</td>
    </tr>
  </tbody>
</table>


中值：$m_{local} = \text{median}{p(i,j) : (i,j) \in \Omega, (i,j) \neq (x,y)}$


<table>
  <tbody>
    <tr>
      <td>标准差：$\sigma_{local} = \sqrt{\frac{1}{</td>
      <td>\Omega</td>
      <td>-1} \sum_{(i,j) \in \Omega, (i,j) \neq (x,y)} (p(i,j) - \mu_{local})^2}$</td>
    </tr>
  </tbody>
</table>


检测准则结合多个统计量：
\(\text{Defect}(x,y) = \begin{cases}
1, & \text{if } |p(x,y) - m_{local}| > k_2 \cdot \sigma_{local} \\
& \text{and } |p(x,y) - \mu_{local}| > k_3 \cdot \sigma_{local} \\
0, & \text{otherwise}
\end{cases}\)


**方向性检测**考虑图像的局部结构，避免将边缘误判为缺陷：


1. 计算四个方向的梯度：

<table>
          <tbody>
            <tr>
              <td>水平：$G_h =</td>
              <td>p(x-1,y) - p(x+1,y)</td>
              <td>$</td>
            </tr>
          </tbody>
        </table>


2.

<table>
          <tbody>
            <tr>
              <td>垂直：$G_v =</td>
              <td>p(x,y-1) - p(x,y+1)</td>
              <td>$</td>
            </tr>
          </tbody>
        </table>


3.

<table>
          <tbody>
            <tr>
              <td>对角：$G_{d1} =</td>
              <td>p(x-1,y-1) - p(x+1,y+1)</td>
              <td>$</td>
            </tr>
          </tbody>
        </table>


4.

<table>
          <tbody>
            <tr>
              <td>反对角：$G_{d2} =</td>
              <td>p(x-1,y+1) - p(x+1,y-1)</td>
              <td>$</td>
            </tr>
          </tbody>
        </table>


5. 选择梯度最小的方向进行插值预测： \(\hat{p}(x,y) = \text{Interp}_{dir_{min}}(\Omega_{x,y})\)
6. 基于预测误差判定： \(\text{Defect}(x,y) = \mathbb{1}\{|p(x,y) - \hat{p}(x,y)| > T_{adaptive}\}\)


### 6.1.4 检测阈值的自适应调整


固定阈值在不同场景下表现差异很大。自适应阈值根据图像内容和噪声水平动态调整，提高检测鲁棒性。


**基于噪声模型的阈值自适应**：
传感器噪声通常遵循泊松-高斯模型：
\(\sigma^2_{total} = \sigma^2_{read} + g \cdot p\)
其中 $\sigma^2_{read}$ 是读出噪声，$g$ 是增益系数，$p$ 是信号强度。


自适应阈值：
\(T_{adaptive} = k_4 \cdot \sqrt{\sigma^2_{read} + g \cdot \mu_{local}}\)


**基于场景复杂度的调整**：


1. 计算局部纹理复杂度： \(C_{texture} = \frac{1}{|\Omega|} \sum_{(i,j) \in \Omega} |\nabla p(i,j)|\)
2. 调整检测阈值： \(T_{final} = T_{base} \cdot (1 + \alpha \cdot \tanh(\beta \cdot C_{texture}))\) 其中 $\alpha$ 控制调整幅度，$\beta$ 控制响应曲线陡度。


### 6.1.5 误检与漏检的权衡


缺陷检测面临典型的二分类问题：需要在误检率（False Positive Rate, FPR）和漏检率（False Negative Rate, FNR）之间权衡。


**ROC曲线分析**：
通过调整检测阈值 $T$，可以得到不同的工作点：


- 真阳性率（TPR）：$TPR(T) = \frac{TP}{TP + FN}$
- 假阳性率（FPR）：$FPR(T) = \frac{FP}{FP + TN}$


**应用场景的权衡策略**：


自动驾驶场景更关注漏检的危害：


- 采用较低的检测阈值（$k_2 = 3-4$）
- 宁可误修复正常像素，也要确保缺陷被处理
- 重点关注可能影响目标检测的缺陷类型


消费电子场景平衡考虑：


- 中等检测阈值（$k_2 = 4-5$）
- 避免过度修复导致细节损失
- 结合用户反馈动态调整


医疗成像等高精度场景：


- 多级检测策略，不同置信度采用不同处理
- 保留原始数据用于后处理验证
- 记录所有检测和修复操作日志


## 6.2 Bad Pixel Correction策略：中值、方向插值


缺陷像素检测完成后，需要通过适当的算法修复这些异常值。修复策略的选择直接影响图像质量、计算复杂度和硬件资源消耗。本节将详细介绍主流的修复算法及其优化实现。


### 6.2.1 中值滤波器的设计与实现


中值滤波器是最经典的缺陷像素修复方法，具有良好的鲁棒性和相对简单的硬件实现。其核心思想是用邻域像素的中值替换缺陷像素。


**基础中值滤波**：
对于Bayer格式的RAW数据，必须考虑颜色通道的一致性。设缺陷像素位于 $(x,y)$，颜色通道为 $c \in {R, G_r, G_b, B}$，则：


\[p_{corrected}(x,y) = \text{median}\{p(i,j) : (i,j) \in \Omega_{x,y}, color(i,j) = c\}\]


对于绿色像素，典型的5×5邻域包含12个同色像素：


```
     G  B  G  B  G
     R  G  R  G  R
     G  B [G] B  G  <- 中心缺陷像素
     R  G  R  G  R
     G  B  G  B  G
```


**加权中值滤波**考虑距离权重：
\(p_{corrected}(x,y) = \text{weighted\_median}\{(p(i,j), w_{i,j}) : (i,j) \in \Omega\}\)


其中权重 $w_{i,j} = \exp(-\frac{d_{i,j}^2}{2\sigma_d^2})$，$d_{i,j}$ 是像素间的空间距离。


**快速中值算法**用于硬件实现：


1. **部分排序网络**：对于固定大小的输入（如9个像素），使用比较器网络实现： 第一层：并行比较相邻元素
2. 中间层：交叉比较和交换
3. 最后提取中位数
4. **直方图方法**：适用于位深较小的场景 统计邻域像素值分布
5. 累积直方图找到中位数
6. 适合8-10bit数据，需要 $2^{bit_depth}$ 大小的计数器阵列
7. **近似中值**：降低复杂度的工程化方法 \(p_{approx} = \text{median}_3(\text{max}_3(a,b,c), \text{mid}_3(d,e,f), \text{min}_3(g,h,i))\) 仅需19次比较，误差通常可接受


### 6.2.2 方向性插值算法


方向性插值利用图像的局部结构信息，沿着边缘方向进行插值，避免跨越边缘造成的模糊。


**梯度导向插值**：


1. 计算多个方向的梯度： \(G_{\theta} = \sum_{(i,j) \in L_{\theta}} |p(i,j) - p(i',j')|\) 其中 $L_{\theta}$ 是方向 $\theta$ 上的像素对
2. 选择最小梯度方向： \(\theta_{opt} = \arg\min_{\theta} G_{\theta}\)
3. 沿最优方向插值： \(p_{corrected}(x,y) = \frac{1}{|L_{\theta_{opt}}|} \sum_{(i,j) \in L_{\theta_{opt}}} p(i,j)\)


**自适应方向插值**（Adaptive Directional Interpolation, ADI）：


定义四个基本方向的插值核：


- 水平：$K_h = [0.5, 0, 0.5]$
- 垂直：$K_v = [0.5; 0; 0.5]$
- 主对角：$K_{d1} = \begin{bmatrix}0.5 & 0 & 0\0 & 0 & 0\0 & 0 & 0.5\end{bmatrix}$
- 副对角：$K_{d2} = \begin{bmatrix}0 & 0 & 0.5\0 & 0 & 0\0.5 & 0 & 0\end{bmatrix}$


权重计算基于方向一致性：
\(w_{\theta} = \frac{1}{1 + (G_{\theta}/G_{min})^p}\)
其中 $p$ 控制方向选择的锐度（典型值2-4）。


最终插值结果：
\(p_{corrected} = \sum_{\theta} w_{\theta} \cdot p_{\theta} / \sum_{\theta} w_{\theta}\)


### 6.2.3 混合修复策略


实际系统中，单一修复方法难以应对所有场景。混合策略根据图像内容自适应选择或组合多种方法。


**基于置信度的混合**：


定义检测置信度 $C_{detect} \in [0,1]$：
\(C_{detect} = \tanh\left(\frac{|p(x,y) - \hat{p}(x,y)|}{T_{detect}} - 1\right)\)


修复强度自适应：
\(p_{final} = (1 - C_{detect}) \cdot p_{original} + C_{detect} \cdot p_{corrected}\)


**多级修复流水线**：


1. **第一级**：简单中值滤波 处理明显的stuck像素
2. 低延迟，适合实时处理
3. **第二级**：方向性插值 处理边缘附近的缺陷
4. 保持图像锐度
5. **第三级**：迭代优化 处理簇状缺陷
6. 可选的离线处理


**场景自适应选择**：


基于局部特征选择修复策略：


```
if (variance_local < T_flat):
    使用均值滤波  # 平坦区域
elif (gradient_max > T_edge):
    使用方向插值  # 边缘区域
else:
    使用中值滤波  # 纹理区域
```


### 6.2.4 边缘感知的修复方法


边缘是图像中的重要视觉特征，修复算法必须避免破坏边缘结构。


**双边滤波修复**：


结合空间距离和像素相似度：
\(p_{corrected} = \frac{\sum_{(i,j) \in \Omega} p(i,j) \cdot w_s(i,j) \cdot w_r(i,j)}{\sum_{(i,j) \in \Omega} w_s(i,j) \cdot w_r(i,j)}\)


其中：


- 空间权重：$w_s(i,j) = \exp(-\frac{(i-x)^2+(j-y)^2}{2\sigma_s^2})$
- 范围权重：$w_r(i,j) = \exp(-\frac{(p(i,j)-\mu_{local})^2}{2\sigma_r^2})$


**结构张量引导**：


计算局部结构张量：
\(T = \begin{bmatrix}
\sum I_x^2 & \sum I_x I_y \\
\sum I_x I_y & \sum I_y^2
\end{bmatrix}\)


特征值分解得到主方向：
\(T \cdot v_1 = \lambda_1 \cdot v_1\)


沿主方向（边缘方向）插值，垂直方向保持锐度。


### 6.2.5 硬件实现的资源权衡


ISP中的缺陷修复模块需要在性能、面积和功耗之间权衡。


**流水线架构设计**：


```
输入缓冲 -> 检测单元 -> 修复单元 -> 输出缓冲
     |          |            |           |
   Line        Detection   Correction  Line
   Buffer      Memory      LUT        Buffer
```


**资源估算**：


1. **Line Buffer需求**： 5×5窗口需要4行缓冲
2. 每行：$Width \times BitDepth$ bits
3. 总计：$4 \times 4K \times 12bit = 192Kb$（4K分辨率）
4. **计算单元**： 中值滤波：~50个比较器
5. 方向插值：4个MAC单元
6. 控制逻辑：~5K门
7. **功耗优化**： 条件处理：仅对检测到的缺陷像素启动修复
8. 时钟门控：空闲模块关闭时钟
9. 电压调节：根据帧率需求调整工作电压


**定点化设计**：


浮点到定点转换：


```
float: weight = exp(-d²/2σ²)
fixed: weight_fixed = LUT[d²] >> shift_amount
```


精度分析：


- 像素值：10-12 bits
- 权重：8 bits（256级量化）
- 中间结果：16 bits（防止溢出）
- 输出：原始位深


**并行化策略**：


1. **像素级并行**：多个修复单元处理不同像素
2. **方向并行**：同时计算多个方向的插值
3. **流水线并行**：检测和修复重叠执行


吞吐量计算：
\(Throughput = \frac{PixelClock \times ParallelUnits}{CyclesPerPixel}\)


对于120fps的4K视频：


- 像素率：4096×2160×120 = 1.06 Gpixels/s
- 单周期处理需要：1.06 GHz时钟
- 4并行单元：265 MHz时钟（更实际）


## 6.3 Hot Pixel与Dead Pixel处理


Hot Pixel和Dead Pixel是两类最常见的缺陷像素，它们的成因、表现和处理方法各有特点。深入理解这两类缺陷的物理机制，对于设计有效的检测和修复算法至关重要。


### 6.3.1 Hot Pixel的成因与特征


Hot Pixel（热像素）是指在没有光照或弱光条件下仍产生异常高输出的像素。其主要成因包括：


**物理机制**：


1. **暗电流异常**：晶格缺陷或杂质能级导致热激发电子增加 \(I_{dark} = I_0 \exp\left(-\frac{E_g}{2kT}\right) + I_{defect}\) 其中 $E_g$ 是带隙能量，$I_{defect}$ 是缺陷贡献
2. **漏电流**：PN结隔离不良或表面态引起的漏电 \(I_{leak} = A \cdot J_s \left[\exp\left(\frac{qV}{nkT}\right) - 1\right]\)
3. **电荷注入**：复位不完全或寄生电容耦合


**温度依赖特性**：
热像素数量随温度呈指数增长：
\(N_{hot}(T) = N_0 \cdot \exp\left(\frac{T - T_0}{T_c}\right)\)
其中 $T_c$ 约为8-10°C（每升高10°C，热像素数量翻倍）。


**时间演化特征**：


- 短期稳定性：在固定温度下，输出值相对稳定
- 长期退化：辐射损伤和器件老化导致热像素增多
- 随机激活：某些像素在特定条件下突然变为热像素


### 6.3.2 Dead Pixel的识别方法


Dead Pixel（死像素）完全或部分失去光电响应能力。


**分类与特征**：


1. **完全死点**：零响应或固定低值输出 \(R_{dead}

```
for multiple_illumination_levels:
    响应斜率 = ΔOutput / ΔLight
    if 响应斜率 < threshold_min:
        标记为dead pixel
```


**动态范围检测**：
\(DR_{pixel} = 20\log_{10}\left(\frac{V_{sat} - V_{dark}}{σ_{noise}}\right)\)
死像素的动态范围显著低于正常值。


**相对响应分析**：
\(RR_i = \frac{R_i}{\text{median}(R_{neighbors})}\)
当 $RR_i < 0.2$ 时判定为死像素。


### 6.3.3 温度依赖性分析


温度对缺陷像素的影响需要在ISP设计中充分考虑。


**温度补偿模型**：


1. **暗电流温度模型**： \(I_{dark}(T) = I_{dark}(T_{ref}) \cdot 2^{(T-T_{ref})/T_{double}}\) 其中 $T_{double} \approx 8°C$
2. **阈值自适应**： \(T_{hot}(T) = T_{hot}(25°C) \cdot \left[1 + \alpha(T - 25)\right]\) $\alpha \approx 0.02/°C$


**实时温度监控**：


```
温度传感器读数 -> 查找补偿表 -> 更新检测阈值
                 -> 更新坏点地图
                 -> 调整修复强度
```


**车载应用的特殊考虑**：


- 工作温度范围：-40°C到+125°C
- 快速温变：隧道进出、阳光直射
- 需要多温度点标定： \(Map_{defect}(T) = \bigcup_{i} Map_{calibrated}(T_i) \cdot w_i(T)\)


### 6.3.4 暗帧校准技术


暗帧校准是处理热像素的有效方法，通过减去暗电流模板来消除固定模式噪声。


**基础暗帧减法**：
\(I_{corrected} = I_{raw} - I_{dark}(t_{exp}, T, ISO)\)


**多暗帧平均**：
降低暗帧本身的随机噪声：
\(I_{dark,avg} = \frac{1}{N} \sum_{i=1}^{N} I_{dark,i}\)
典型 $N = 16-32$


**自适应暗帧库**：


```
暗帧数据库结构：
- 曝光时间: [1/1000s, ..., 30s]
- 温度: [-20°C, ..., 60°C]，步进5°C
- ISO: [100, 200, 400, ..., 12800]
```


插值生成当前条件的暗帧：
\(I_{dark}(t, T, ISO) = \text{TrilinearInterp}(DB, t, T, ISO)\)


**增量更新策略**：
\(I_{dark,new} = (1-\alpha) \cdot I_{dark,old} + \alpha \cdot I_{dark,current}\)
$\alpha = 0.01-0.1$，平衡稳定性和适应性。


### 6.3.5 长曝光场景的特殊处理


长曝光（>1秒）会显著放大热像素问题，需要专门的处理策略。


**分段曝光合成**：
将长曝光分解为多个短曝光：
\(I_{long} = \sum_{i=1}^{N} I_{short,i} - (N-1) \cdot I_{dark,short}\)


优势：


- 减少单次曝光的热噪声累积
- 可实时检测和剔除瞬态热像素
- 支持运动物体检测和去除


**Sigma裁剪算法**：


```
<span class="k">for</span> <span class="n">each</span> <span class="n">pixel</span><span class="p">:</span>
    <span class="n">values</span> <span class="o">=</span> <span class="p">[</span><span class="n">frame1</span><span class="p">[</span><span class="n">x</span><span class="p">,</span><span class="n">y</span><span class="p">],</span> <span class="n">frame2</span><span class="p">[</span><span class="n">x</span><span class="p">,</span><span class="n">y</span><span class="p">],</span> <span class="p">...,</span> <span class="n">frameN</span><span class="p">[</span><span class="n">x</span><span class="p">,</span><span class="n">y</span><span class="p">]]</span>
    <span class="n">mean</span> <span class="o">=</span> <span class="n">average</span><span class="p">(</span><span class="n">values</span><span class="p">)</span>
    <span class="n">std</span> <span class="o">=</span> <span class="n">stddev</span><span class="p">(</span><span class="n">values</span><span class="p">)</span>
    <span class="c1"># 剔除离群值
</span>    <span class="n">filtered</span> <span class="o">=</span> <span class="p">[</span><span class="n">v</span> <span class="k">for</span> <span class="n">v</span> <span class="ow">in</span> <span class="n">values</span> <span class="k">if</span> <span class="o">|</span><span class="n">v</span><span class="o">-</span><span class="n">mean</span><span class="o">|</span> <span class="o"><</span> <span class="n">k</span><span class="o">*</span><span class="n">std</span><span class="p">]</span>
    <span class="n">output</span><span class="p">[</span><span class="n">x</span><span class="p">,</span><span class="n">y</span><span class="p">]</span> <span class="o">=</span> <span class="n">average</span><span class="p">(</span><span class="n">filtered</span><span class="p">)</span>
```


**热像素增长预测**：
基于Arrhenius方程建模：
\(R_{growth} = A \cdot \exp\left(-\frac{E_a}{kT}\right) \cdot t_{exp}\)


用于预警和动态调整处理策略。


**实时监控与修正**：


```
每隔ΔT时间：
1. 采集暗帧样本
2. 更新热像素地图
3. 计算增长率
4. 若增长率 > 阈值：
   - 降低传感器温度（如果可控）
   - 切换到更激进的修复模式
   - 警告用户图像质量可能下降
```


**天文摄影模式优化**：


- 预曝光：拍摄前进行传感器预热稳定
- 抖动叠加：通过微小位移区分热像素和真实星点
- 冷却系统：主动制冷降低暗电流
- 参考帧减法： \(I_{final} = I_{light} - I_{dark} - I_{bias} + I_{flat}\)


## 6.4 Cluster缺陷检测与修复


簇状缺陷是指多个相邻的缺陷像素形成的连续区域，其修复比单个缺陷像素更具挑战性。这类缺陷可能源于局部制造工艺问题、物理损伤或电路故障。


### 6.4.1 簇状缺陷的定义与分类


**空间分布特征**：


1. **小簇（2-4像素）**： 线状：水平、垂直或对角排列
2. L型、T型：转角分布
3. 方块：2×2像素块
4. **中等簇（5-25像素）**： 不规则形状
5. 可能跨越多个颜色通道
6. 影响局部图像统计特性
7. **大面积缺陷（>25像素）**： 行/列缺陷：整行或整列失效
8. 块状缺陷：矩形或不规则大块
9. 渐变缺陷：边界模糊的渐变区域


**成因分析**：


- 制造缺陷：光刻对准误差、局部污染
- 物理损伤：静电放电（ESD）、机械应力
- 电路故障：行/列驱动器失效、局部短路
- 辐射损伤：高能粒子撞击形成的损伤簇


### 6.4.2 连通域分析算法


连通域分析是检测和量化簇状缺陷的核心技术。


**二值化预处理**：
首先将缺陷检测结果二值化：
\(B(x,y) = \begin{cases}
1, & \text{if pixel}(x,y) \text{ is defective} \\
0, & \text{otherwise}
\end{cases}\)


**8连通标记算法**：


```
初始化：label = 0, equivalence_table = []
第一遍扫描：
for each pixel (x,y):
    if B(x,y) == 1:
        neighbors = get_8_neighbors(x,y)
        labeled_neighbors = [n for n in neighbors if label[n] > 0]

        if len(labeled_neighbors) == 0:
            label++
            assign_label(x,y, label)
        else:
            min_label = min(labeled_neighbors)
            assign_label(x,y, min_label)
            update_equivalence(labeled_neighbors)

第二遍扫描：
解析等价表，统一标签
```


**簇特征提取**：
对每个连通域计算：


- 面积：$A = \sum_{(x,y) \in C} 1$
- 周长：$P = \sum_{(x,y) \in \partial C} 1$
- 紧致度：$\Psi = \frac{4\pi A}{P^2}$
- 矩形度：$R = \frac{A}{W_{bbox} \times H_{bbox}}$
- 质心：$(\bar{x}, \bar{y}) = \frac{1}{A}\sum_{(x,y) \in C}(x,y)$


**形状分类**：
基于特征进行簇分类：
\(\text{ClusterType} = \begin{cases}
\text{点状}, & A \leq 1 \\
\text{线状}, & A > 1 \text{ and } \Psi < 0.2 \\
\text{块状}, & A > 4 \text{ and } \Psi > 0.5 \\
\text{不规则}, & \text{otherwise}
\end{cases}\)


### 6.4.3 大面积缺陷的修复策略


大面积缺陷无法通过简单的邻域插值修复，需要更复杂的策略。


**多尺度修复框架**：


1. **由粗到细的策略**：

```
for scale in [1/8, 1/4, 1/2, 1]:
    downsample_image(scale)
    detect_and_repair_defects()
    upsample_result()
    refine_boundaries()
```


2. **金字塔混合**： \(I_{repaired} = \sum_{l=0}^{L} w_l \cdot \text{Repair}_l(I)\) 其中 $w_l$ 是各尺度的权重


**基于样例的修复**（Exemplar-based Inpainting）：


1. **块匹配**： 对于缺陷边界上的块 $\Psi_p$： \(\Psi_{\hat{q}} = \arg\min_{\Psi_q \in \Phi} d(\Psi_p, \Psi_q)\) 其中 $\Phi$ 是源区域，$d$ 是距离度量
2. **优先级计算**： \(P(p) = C(p) \cdot D(p)\)

<table>
          <tbody>
            <tr>
              <td>置信度：$C(p) = \frac{\sum_{q \in \Psi_p \cap \Omega} C(q)}{</td>
              <td>\Psi_p</td>
              <td>}$</td>
            </tr>
          </tbody>
        </table>


3.

<table>
          <tbody>
            <tr>
              <td>数据项：$D(p) = \frac{</td>
              <td>\nabla I_p^{\perp} \cdot n_p</td>
              <td>}{\alpha}$</td>
            </tr>
          </tbody>
        </table>


4. **迭代填充**：

```
while 存在未修复区域:
    计算边界像素优先级
    选择最高优先级块
    搜索最佳匹配块
    复制并更新置信度
```


**稀疏表示方法**：
\(\min_{\alpha} \|\Psi_p - D\alpha\|_2^2 + \lambda\|\alpha\|_1\)
其中 $D$ 是字典，$\alpha$ 是稀疏系数。


### 6.4.4 纹理合成技术


纹理合成用于修复具有重复模式的区域。


**Markov随机场模型**：
\(P(p|N(p)) = \frac{1}{Z} \exp\left(-\frac{E(p,N(p))}{T}\right)\)


能量函数：
\(E(p,N(p)) = \sum_{q \in N(p)} \omega_q \|I(p) - I(q)\|^2\)


**块拼接算法**：


1. **重叠区域最小化**： \(E_{overlap} = \sum_{(i,j) \in overlap} (B_1(i,j) - B_2(i,j))^2\)
2. **最优缝合线**（Minimum Error Boundary Cut）： 使用动态规划找到误差最小的拼接路径
3. **泊松混合**： \(\min_f \iint_{\Omega} |\nabla f - \nabla g|^2\) 边界条件：$f|*{\partial\Omega} = f^*|*{\partial\Omega}$


**基于CNN的纹理生成**：
利用预训练的特征提取器：
\(\mathcal{L}_{texture} = \sum_l \|G^l(I_{synth}) - G^l(I_{ref})\|_F^2\)
其中 $G^l$ 是第 $l$ 层的Gram矩阵。


### 6.4.5 修复质量评估


评估修复效果对于算法优化和质量控制至关重要。


**客观评价指标**：


1. **结构相似度（SSIM）**： \(SSIM = \frac{(2\mu_x\mu_y + C_1)(2\sigma_{xy} + C_2)}{(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)}\)
2. **边缘保持指数（EPI）**： \(EPI = \frac{\sum |G_{repaired} \cap G_{original}|}{\sum |G_{original}|}\)
3. **纹理一致性**： \(TC = 1 - \frac{\|H_{patch} - H_{neighbor}\|_1}{2}\) 其中 $H$ 是归一化直方图


**感知质量评估**：


1. **自然图像统计**： 检查修复区域的统计分布是否符合自然图像
2. 使用广义高斯分布拟合： \(p(x) = \frac{\beta}{2\alpha\Gamma(1/\beta)} \exp\left(-\left(\frac{|x|}{\alpha}\right)^{\beta}\right)\)
3. **局部连续性**： \(C_{local} = \exp\left(-\frac{\sum_{e \in \partial\Omega} |\nabla I(e)|^2}{|\partial\Omega|}\right)\)


**硬件性能指标**：


1. **计算复杂度**： 每像素操作数（Operations Per Pixel）
2. 内存访问模式和带宽需求
3. **延迟分析**： \(Latency = N_{stages} \times T_{clock} + T_{memory}\)
4. **资源利用率**： DSP/ALU利用率
5. 内存带宽利用率
6. 功耗效率（mW/Mpixel）


## 6.5 时域坏点追踪与更新


随着传感器老化和环境变化，缺陷像素的分布和特性会动态变化。时域追踪机制能够自适应地更新缺陷像素地图，提高检测准确性并优化修复效果。


### 6.5.1 坏点地图的动态维护


**分层存储架构**：


1. **静态层**：工厂标定的永久缺陷 存储在非易失性存储器（NVM）
2. 压缩存储格式：行程编码（RLE）或坐标列表
3. **动态层**：运行时检测的缺陷 存储在SRAM/DRAM中
4. 包含时间戳和置信度信息
5. **临时层**：当前帧检测结果 用于验证和更新动态层


**地图更新策略**：
\(Map_{t+1} = Map_{static} \cup Update(Map_{dynamic,t}, Detection_t)\)


更新规则：


```
if pixel in Map_static:
    保持不变（永久缺陷）
elif pixel in Detection_t:
    if pixel in Map_dynamic:
        增加置信度
    else:
        添加到候选列表
elif pixel in Map_dynamic:
    降低置信度
    if 置信度 < 阈值:
        从地图中移除
```


**压缩存储格式**：


1. **坐标列表**：

```
结构：[(x1,y1), (x2,y2), ..., (xn,yn)]
存储需求：2 × log2(W×H) × N bits
适用：稀疏缺陷（<0.1%）
```


2. **位图压缩**： 分块位图：将图像分成tiles，只存储包含缺陷的tiles
3. 层次位图：多分辨率表示，快速查询
4. **混合编码**：

```
if 缺陷密度 < 0.01%:
    使用坐标列表
elif 缺陷呈簇状分布:
    使用RLE编码
else:
    使用压缩位图
```


### 6.5.2 时间序列分析


通过分析像素值的时间序列，可以预测和识别潜在缺陷。


**滑动窗口统计**：
维护最近N帧的统计信息：
\(\mu_t(x,y) = \frac{1}{N} \sum_{i=t-N+1}^{t} p_i(x,y)\)
\(\sigma_t^2(x,y) = \frac{1}{N-1} \sum_{i=t-N+1}^{t} (p_i(x,y) - \mu_t(x,y))^2\)


**异常检测**：
使用Z-score检测异常：
\(Z_t(x,y) = \frac{|p_t(x,y) - \mu_{t-1}(x,y)|}{\sigma_{t-1}(x,y)}\)


当 $Z_t > Z_{threshold}$ 时标记为潜在缺陷。


**趋势分析**：
线性趋势估计：
\(p(t) = \alpha + \beta \cdot t + \epsilon\)


使用最小二乘法估计参数：
\(\beta = \frac{\sum_{i}(t_i - \bar{t})(p_i - \bar{p})}{\sum_{i}(t_i - \bar{t})^2}\)


<table>
  <tbody>
    <tr>
      <td>退化预警：当 $</td>
      <td>\beta</td>
      <td>&gt; \beta_{critical}$ 时发出警告。</td>
    </tr>
  </tbody>
</table>


### 6.5.3 概率模型与置信度更新


**贝叶斯更新框架**：


定义缺陷概率：
\(P(D_t|O_{1:t}) = \frac{P(O_t|D_t) \cdot P(D_t|O_{1:t-1})}{P(O_t|O_{1:t-1})}\)


其中：


- $D_t$：时刻t像素为缺陷的事件
- $O_t$：时刻t的观测（检测结果）


**置信度演化模型**：
\(C_{t+1} = \begin{cases}
\min(C_t + \Delta_+, 1), & \text{if detected as defect} \\
\max(C_t - \Delta_-, 0), & \text{otherwise}
\end{cases}\)


自适应步长：
\(\Delta_+ = \alpha \cdot (1 - C_t)\)
\(\Delta_- = \beta \cdot C_t\)


**马尔可夫链模型**：
状态转移概率：
\(P = \begin{bmatrix}
p_{nn} & p_{nd} \\
p_{dn} & p_{dd}
\end{bmatrix}\)


其中：


- $p_{nn}$：正常→正常
- $p_{nd}$：正常→缺陷
- $p_{dn}$：缺陷→正常（恢复）
- $p_{dd}$：缺陷→缺陷


稳态分布：
\(\pi_d = \frac{p_{nd}}{p_{nd} + p_{dn}}\)


### 6.5.4 存储优化策略


**分级缓存机制**：


```
L1 Cache (最近访问的tiles)
    ↓
L2 Cache (当前图像区域)
    ↓
Main Memory (完整地图)
    ↓
NVM (永久存储)
```


**预取策略**：
基于扫描模式预取下一个tile：


```
当前tile: (x, y)
预取tiles: [(x+1,y), (x,y+1), (x+1,y+1)]
```


**增量更新**：
只传输和存储变化部分：
\(\Delta Map_t = Map_t \oplus Map_{t-1}\)


使用差分编码减少带宽：


```
Header: [timestamp, num_changes]
Changes: [(x1,y1,op1), (x2,y2,op2), ...]
其中op ∈ {ADD, REMOVE, UPDATE_CONFIDENCE}
```


### 6.5.5 自学习机制


**在线学习框架**：


1. **特征提取**： 局部统计特征：均值、方差、梯度
2. 时间特征：变化率、周期性
3. 空间特征：邻域缺陷密度
4. **分类器更新**： 使用轻量级在线学习算法： \(w_{t+1} = w_t + \eta \cdot (y_t - \hat{y}_t) \cdot x_t\)
5. **自适应阈值**： 基于历史性能调整： \(T_{t+1} = T_t \cdot \exp(\gamma \cdot (FPR_t - FPR_{target}))\)


**强化学习优化**：


状态空间：$S = {缺陷密度, 场景类型, 光照条件}$
动作空间：$A = {检测阈值, 修复强度}$
奖励函数：$R = -\alpha \cdot FPR - \beta \cdot FNR - \gamma \cdot 计算成本$


使用Q-learning更新策略：
\(Q(s,a) \leftarrow Q(s,a) + \alpha[r + \gamma \max_{a'} Q(s',a') - Q(s,a)]\)


**自校准机制**：


周期性自检：


```
每N帧或检测到场景切换时：
1. 采集均匀区域样本
2. 计算像素一致性
3. 识别新出现的异常像素
4. 验证已知缺陷是否仍然存在
5. 更新缺陷地图和参数
```


**协同学习**：
多传感器系统中的信息共享：
\(Map_{fused} = \bigcap_{i} Map_i^{high\_conf} \cup \bigcup_{i} Map_i^{verified}\)


## 6.6 边缘保护的缺陷修复算法


边缘和细节是图像中的关键视觉信息，缺陷修复必须避免破坏这些结构。边缘保护算法通过识别和利用局部图像结构，实现高质量的缺陷修复。


### 6.6.1 边缘检测与分类


**多尺度边缘检测**：


使用Sobel算子计算梯度：
\(G_x = \begin{bmatrix}-1 & 0 & 1\\-2 & 0 & 2\\-1 & 0 & 1\end{bmatrix} * I\)
\(G_y = \begin{bmatrix}-1 & -2 & -1\\0 & 0 & 0\\1 & 2 & 1\end{bmatrix} * I\)


梯度幅值和方向：
\(M = \sqrt{G_x^2 + G_y^2}\)
\(\theta = \arctan2(G_y, G_x)\)


**边缘分类**：


1. **阶跃边缘**：亮度突变 \(f(x) = A \cdot u(x - x_0) + B\)
2. **斜坡边缘**：渐变过渡 \(f(x) = A \cdot \tanh\left(\frac{x - x_0}{\sigma}\right) + B\)
3. **屋顶边缘**：细线结构 \(f(x) = A \cdot \exp\left(-\frac{(x - x_0)^2}{2\sigma^2}\right) + B\)


**边缘强度评估**：
\(E_{strength} = \frac{M}{\sigma_{noise} + \epsilon}\)


其中 $\sigma_{noise}$ 是局部噪声水平估计。


### 6.6.2 方向性权重计算


**各向异性权重核**：


基于边缘方向构建权重：
\(w(i,j) = \exp\left(-\frac{d_{\perp}^2}{2\sigma_{\perp}^2} - \frac{d_{\parallel}^2}{2\sigma_{\parallel}^2}\right)\)


其中：


- $d_{\perp}$：垂直于边缘方向的距离
- $d_{\parallel}$：平行于边缘方向的距离
- $\sigma_{\perp}

```
R  G  R  G  R
G  B  G  B  G
R  G [?] G  R
G  B  G  B  G
R  G  R  G  R
```


(a) 有多少个同色邻域像素可用于中值计算？
(b) 若这些像素值为[120, 125, 118, 130, 122, 128, 115, 127, 124, 126, 119, 121]，中值是多少？


<details>
<summary>答案</summary>

(a) 12个绿色像素（不包括中心缺陷像素）

(b) 排序：[115, 118, 119, 120, 121, 122, 124, 125, 126, 127, 128, 130]
   - 12个数的中值 = (第6个 + 第7个) / 2 = (122 + 124) / 2 = 123
</details>


**练习6.3** 检测阈值计算
某区域的局部统计：均值μ=128，标准差σ=8，中心像素值p=155。
使用检测准则：$|p - μ| > k·σ$
(a) k=3时，该像素是否为缺陷？
(b) 要检测出该像素，k的最大值是多少？


<details>
<summary>答案</summary>

(a) $|155 - 128| = 27$，$3 \times 8 = 24$
   - 因为 27 &gt; 24，所以检测为缺陷

(b) $k_{max} = |p - μ| / σ = 27 / 8 = 3.375$
</details>


### 挑战题（深度思考）


**练习6.4** 簇状缺陷修复优化
一个3×3的簇状缺陷位于图像边缘附近，左侧是暗区域（平均值50），右侧是亮区域（平均值200），边缘呈垂直方向。设计一个修复策略，要求：
(a) 保持边缘锐度
(b) 最小化修复痕迹
(c) 计算复杂度O(n)


*Hint: 考虑方向性插值和边缘检测的结合*


<details>
<summary>答案</summary>

修复策略：
1. 检测边缘方向（垂直）
2. 对每个缺陷像素：
   - 若在边缘左侧：从左侧采样（值≈50）
   - 若在边缘右侧：从右侧采样（值≈200）
   - 若跨越边缘：使用垂直方向插值
3. 使用一维高斯核沿边缘方向平滑
4. 复杂度：边缘检测O(9) + 插值O(9) + 平滑O(9) = O(n)
</details>


**练习6.5** 动态阈值自适应
设计一个基于场景的自适应阈值算法，考虑：


- 平坦区域（天空）：噪声低，纹理少
- 纹理区域（树叶）：噪声中等，细节丰富
- 边缘区域（建筑轮廓）：需要保护


给出阈值调整公式和参数建议。


<details>
<summary>答案</summary>

自适应阈值公式：
$T_{adaptive} = T_{base} \cdot f_{scene} \cdot f_{noise} \cdot f_{edge}$

其中：
- $f_{scene} = 1 + 0.5 \cdot \tanh(2(C_{texture} - 0.5))$，纹理复杂度因子
- $f_{noise} = \sqrt{1 + \sigma_{local}^2/\sigma_{ref}^2}$，噪声适应因子
- $f_{edge} = \begin{cases} 0.7, &amp; \text{边缘区} \\ 1.0, &amp; \text{其他} \end{cases}$，边缘保护因子

参数建议：
- 平坦区：$T_{base} = 3\sigma$
- 纹理区：$T_{base} = 5\sigma$
- 边缘区：$T_{base} = 4\sigma$，但降低修复强度
</details>


**练习6.6** 存储优化计算
4K图像（4096×2160），缺陷率0.1%，设计存储方案：
(a) 计算坐标列表、RLE、位图三种方式的存储需求
(b) 若缺陷呈行列分布（10条完整坏行+20条坏列），哪种方式最优？
(c) 设计一个混合编码策略


<details>
<summary>答案</summary>

(a) 总像素：4096×2160 = 8,847,360
   缺陷像素：8,847 个

   - 坐标列表：8,847 × 2 × 24 bits = 424,656 bits = 53 KB
   - 位图：8,847,360 bits = 1,106 KB
   - RLE（假设平均游程100）：88 × 2 × 24 bits = 4,224 bits = 0.53 KB

(b) 行列缺陷：
   - 坏行：10 × 4096 = 40,960 像素
   - 坏列：20 × 2160 = 43,200 像素
   - 总计：84,160 像素

   RLE最优：30条线 × (起始坐标24bit + 长度12bit) = 1,080 bits = 0.14 KB

(c) 混合策略：
   ```
   if 连续缺陷 &gt; 100像素:
       使用RLE编码
   elif 缺陷率 &lt; 0.01%:
       使用坐标列表
   else:
       使用分块位图（32×32 tiles）
   ```
</details>


**练习6.7** 边缘保护修复的能量优化
给定能量函数：
\(E = \|p_{corrected} - p_{predicted}\|^2 + \lambda\|\nabla p_{corrected} - \nabla p_{reference}\|^2\)


(a) 推导梯度下降更新公式
(b) 分析λ对修复结果的影响
(c) 设计自适应λ策略


<details>
<summary>答案</summary>

(a) 梯度：
   $\frac{\partial E}{\partial p} = 2(p_{corrected} - p_{predicted}) + 2\lambda\nabla^T(\nabla p_{corrected} - \nabla p_{reference})$

   更新公式：
   $p^{(n+1)} = p^{(n)} - \eta[p^{(n)} - p_{predicted} + \lambda\nabla^2(p^{(n)} - p_{reference})]$

(b) λ的影响：
   - λ=0：纯数据项，可能过平滑
   - λ小：数据拟合为主，边缘可能模糊
   - λ大：梯度保持为主，可能产生振铃
   - λ→∞：完全保持原始梯度

(c) 自适应策略：
   $\lambda_{adaptive} = \lambda_0 \cdot \exp(-\|\nabla p\|^2/\sigma_{grad}^2)$
   - 边缘处（梯度大）：λ小，允许梯度变化
   - 平坦处（梯度小）：λ大，保持平滑
</details>


## 常见陷阱与错误 (Gotchas)


### 1. 检测阈值设置不当


**问题**：固定阈值在不同ISO或光照下表现差异巨大
**症状**：高ISO下大量误检，低光下漏检增加
**解决**：实现基于噪声模型的自适应阈值


### 2. 忽视颜色通道一致性


**问题**：在Bayer数据上直接使用所有邻域像素
**症状**：颜色串扰，错误的颜色artifacts
**解决**：严格按颜色通道分离处理


### 3. 边界处理疏忽


**问题**：图像边界附近的缺陷检测失效
**症状**：边界出现未修复的亮点/暗点
**解决**：实现边界填充或特殊边界处理逻辑


### 4. 过度修复


**问题**：将正常的高对比度细节误判为缺陷
**症状**：星空变成模糊，细节丢失
**解决**：多级置信度判定，保守修复策略


### 5. 时域信息利用不当


**问题**：历史信息权重设置不合理
**症状**：响应过慢或震荡
**解决**：实现自适应遗忘因子


### 6. 硬件资源估算错误


**问题**：Line Buffer深度计算错误
**症状**：处理窗口数据不完整
**解决**：考虑最坏情况，预留余量


## 最佳实践检查清单


### 设计阶段


- 明确目标应用场景和质量要求
- 分析传感器特性和缺陷分布统计
- 制定静态标定和动态检测结合策略
- 设计分级修复流水线
- 预留调试和标定接口


### 算法实现


- 实现颜色通道分离处理
- 添加边界特殊处理
- 实现多种修复算法并支持切换
- 加入置信度机制
- 优化内存访问模式


### 参数调优


- 基于场景的参数集
- 温度补偿表
- ISO相关的噪声模型
- 边缘保护强度控制
- 时域滤波系数


### 验证测试


- 标准测试图像集（包含各类缺陷）
- 温度循环测试
- 长时间稳定性测试
- 边界条件测试
- 性能基准测试


### 生产部署


- 工厂标定流程
- 现场更新机制
- 诊断日志记录
- 降级处理策略
- 用户可配置选项


---


