# Week 1 学习总结：RAW / Sensor 数据直觉

## 本周学习闭环

| 项目 | 要求 |
|---|---|
| 目标 | 说清陌生 DNG 的 shape、dtype、Bayer pattern、black/white level、曝光风险和 ROI 证据 |
| 前置 | 完成 `materials/prerequisites.md` 前四题；知道 `uint16` 减法和 NumPy 切片风险 |
| 运行前预测 | 先写下哪个 Bayer 通道均值最高、暗部/高光 ROI 可能在哪里、是否存在 clipping |
| 最小实验 | 只分析 T01；全量 T01–T14 结果作为附录查证 |
| 验收 | 输出一份 JSON、两张 ROI/直方图，并写一条“现有数据不能确认”的判断 |

从 `stage1_soft_isp/` 运行，输出写入未跟踪的教程目录：

```powershell
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
python scripts/05_analyze_raw_roi.py data/raw/T01_a0006-IMG_2787.dng `
  --out-dir outputs/tutorial/week1 `
  --report outputs/tutorial/week1/roi_analysis.md
```

随后完成[陌生 DNG 输入合同](../../exercises/week1_raw_contract.md)，再阅读本报告中的现成结论。规范和 API 来源见[参考文献](../references.md#week-1rawdng-与数据集)。

Week1 的核心目标不是做图像增强，而是建立 RAW 数据直觉：知道一张 DNG 里有哪些 metadata，Bayer RAW 为什么是单通道，四个 Bayer 通道为什么统计值不同，以及 histogram / ROI 能告诉我们什么。

## 本周 Pipeline 位置

```text
DNG / RAW metadata
  -> raw_image_visible
  -> Bayer pattern 推断
  -> R / Gr / Gb / B 四通道拆分
  -> histogram / ROI / 统计分析
```

Week1 还没有做真正的 ISP 校正，只是在理解输入数据。这个阶段越扎实，后面的 BLC、Demosaic、AWB 越不容易做错。

## 已完成交付物

| 内容 | 文件 |
|---|---|
| RAW metadata 和四通道统计 | `scripts/01_inspect_raw.py`、`reports/raw_stats/S01-S05.json` |
| rawpy 参考图 | `scripts/02_generate_rawpy_references.py`、`data/references/*_rawpy_srgb.png` |
| metadata 汇总 | `scripts/03_dump_raw_metadata_table.py`、`materials/raw_sample_manifest.md` |
| RAW 直方图 | `scripts/04_plot_raw_histogram.py`、`reports/figures/*_histogram.png` |
| ROI 分析 | `scripts/05_analyze_raw_roi.py`、`reports/week1/roi_analysis.md` |
| Week1 详细报告 | `reports/week1/raw_statistics.md` |

## 本周学到的核心概念

### 1. RAW 不是普通 RGB 图片

RAW 是传感器采样值，通常仍然是 Bayer 马赛克排列。每个像素只记录一种颜色响应，不是完整的 R/G/B 三通道。

### 2. metadata 是处理 RAW 的入口

RAW 像素本身只是一组数字，metadata 决定这些数字应怎样解释。第一次读取陌生 DNG 时，建议建立下面的输入合同：

| 信息 | 代表什么 | 为什么后续需要 | 典型错误表现 |
|---|---|---|---|
| `raw_image_visible.shape` | 可见 RAW 的 `(H, W)` | 决定 Bayer mask、LSC gain map 和 ROI 尺寸 | mask、ROI 或 reference 固定错位 |
| `dtype`、min/max | 存储类型和实际码值范围 | 决定中间计算类型、clip 和归一化 | 无符号下溢、溢出或整体亮度尺度错误 |
| `raw_pattern` + `color_desc` | CFA 位置索引及其颜色含义 | BLC、DPC、Demosaic、RAW 域 WB 都按 Bayer 位置工作 | 整图串色，R/B 对调，Gr/Gb 位置错误 |
| `black_level_per_channel` | 无光时的读出基线 | BLC 要先扣掉它，暗部和 AWB 统计才可信 | 暗部发灰、死黑或偏色 |
| `white_level` / per-channel white | 有效饱和上限 | 用于 clamp、归一化和 clipping 判断 | 高光被误截或饱和风险被漏判 |
| active/visible area 与 margins | 完整传感器区域和有效成像区域的坐标关系 | 坏点表、LSC、ROI 和输出必须使用同一坐标系 | 所有空间标注出现固定平移 |
| orientation / `sizes.flip` | 传感器坐标到显示方向的变换 | 数值结果、预览和 ROI 要同步旋转/翻转 | 图像方向对了，但框和参考图对不上 |
| WB gain / color matrix | 白平衡参考和颜色空间转换信息 | 为 AWB/CCM 提供参考或初始值 | 系统性色偏、矩阵方向错误、大量 clipping |

读取顺序应是：先确认数组和几何区域，再解释 CFA，然后确定 black/white 数值尺度，最后读取方向与颜色信息。这样一旦失败，可以判断问题来自“像素内容”还是“解释像素的 metadata”。

还要注意：`uint16` 是存储容器，不等于 16-bit 有效信号；`raw_pattern` 必须结合 `color_desc`；相机白平衡和 color matrix 是参考信息，不自动等于当前场景的 ground truth。缺失字段应记录为 unknown，不做猜测。

### 3. 四个 Bayer 通道均值不同是正常的

R、Gr、Gb、B 的均值不同，不等价于“最终图片颜色偏差”。它首先反映的是：

- 场景光源光谱
- 传感器 R/G/B 滤色片响应
- Bayer 中绿色采样更多
- 尚未做 BLC、AWB、CCM、Gamma

Gr 和 Gb 理论上应比较接近。如果 Gr/Gb 差异明显，可能要检查 Bayer pattern、行列偏移、镜头阴影或局部场景结构。

### 4. Histogram 是观察曝光和动态范围的第一工具

直方图不是在看图像“好不好看”，而是在看像素值分布：

- 靠近 black level：暗部细节少，BLC 后可能大量变 0
- 靠近 white level：高光可能饱和，后续 tone mapping 也救不回真实细节
- 四通道曲线分离：说明 RGB 响应未被白平衡和颜色校正统一

### 5. ROI 用来建立局部判断

全图统计会被大面积背景影响，所以 Week1 还做了暗部、中间调、高光 ROI：

- 暗部 ROI：观察黑电平、噪声、暗部压缩
- 中间调 ROI：后续比较 BLC / AWB / Demosaic 的稳定区域
- 高光 ROI：观察 clipping 和高光恢复风险

## 本周验证标准

1. 能从 DNG 读出 RAW 可见区域和 metadata。
2. 能自动推断 Bayer pattern。
3. 能正确拆分 R / Gr / Gb / B。
4. 能解释四通道均值不同的原因。
5. 能根据 histogram 判断暗部、高光、动态范围风险。
6. 能用 ROI 把全图结论落到局部区域。

## 本周局限

1. Week1 只分析，不校正。
2. 统计值不能直接代表最终照片颜色。
3. Histogram 只能说明数值分布，不能单独判断图像质量。
4. ROI 是自动选择的，仍需要人工检查是否落在合理区域。

## 深度补强：从统计值走向 Sensor 分析

现有 Week1 已经能回答“RAW 里有什么”，但如果要让报告更接近工程分析，还需要把 metadata、噪声和动态范围连接起来。

### 1. Sensor 差异不能被平均掉

T01-T14 来自不同相机和不同场景。不同 sensor 的 black level、white level、ISO、CFA 响应和 ADC 位深可能不同，所以四通道均值不能简单横向比较。

下面是需要额外 EXIF/设备审计才能完成的学习者模板，不属于当前实测结论。未知字段必须保留 unknown，不能从文件名或画面猜测：

| 样张 | 相机/机型 | ISO | black level | white level | Bayer pattern | 分析备注 |
|---|---|---:|---:|---:|---|---|
| T01 | 待从 DNG metadata 读取 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |

这张表的作用不是追求 metadata 好看，而是提醒自己：

```text
RAW 统计首先属于某个 sensor + 某次曝光条件，不是脱离设备的绝对图像质量分数。
```

### 2. 噪声分析要从 mean/std 继续往前走

当前报告主要记录均值和标准差。更深入时，应区分三类噪声：

| 噪声 | 来源 | 可用现有数据怎么近似观察 |
|---|---|---|
| read noise | 读出电路和 ADC 底噪 | 暗部 ROI 的标准差 |
| shot noise | 光子计数随机性 | 不同亮度 ROI 的 mean/std 关系 |
| quantization noise | ADC 量化 | 结合 bit depth 估计理论下限 |

一个可落地的分析方式是按亮度分桶：

```text
把 RAW 像素按亮度分成多个 bin
  -> 统计每个 bin 的 mean 和 std
  -> 如果 std 随 mean 增大，说明噪声具有 signal-dependent 特征
```

这比只看全图标准差更有意义，因为全图 std 同时混入了场景纹理、曝光差异和真实噪声。

### 3. 动态范围要结合 noise floor

学习版可用动态范围可以先用近似公式：

```text
usable_signal = white_level - black_level
noise_floor ≈ dark_roi_std
DR_dB = 20 * log10(usable_signal / noise_floor)
```

注意这个 DR 不是厂商标定值。没有专门 dark frame 时，暗部 ROI 仍可能包含真实纹理和压暗细节，所以它只能作为“当前样张可用动态范围”的估计。

### 4. ROI 选择要写清楚选择标准

自动 ROI 需要说明它的选择依据和失败条件：

| ROI | 推荐选择标准 | 需要人工检查什么 |
|---|---|---|
| dark | 低亮度、非饱和、尽量低纹理 | 是否误选到黑色物体纹理 |
| midtone | 中间亮度、结构稳定 | 是否代表主体区域 |
| highlight | 高亮但未饱和 | 是否已经 clipping |
| texture | 梯度较高但不过曝 | 是否适合看 demosaic 伪影 |

后续每次引用 ROI 指标时，都应该配一张 ROI preview。否则 ROI 指标可能看起来客观，实际选区却不代表想分析的问题。

## 结合 OpenISP 后的补充理解

OpenISP 的模块不是从“读 RAW”开始讲，而是默认你已经知道 RAW 的 Bayer pattern、clip 范围、黑电平、通道位置和后续模块顺序。这反过来说明 Week1 的意义：它不是可有可无的准备工作，而是所有传统 ISP 模块的坐标系。

对照 OpenISP，可以把 Week1 的输出理解成后续模块的输入合同：

| Week1 观察项 | OpenISP 中会影响的模块 | 为什么重要 |
|---|---|---|
| Bayer pattern | `blc.py`、`awb.py`、`cfa.py`、`cnf.py` | 所有按 R/Gr/Gb/B 位置处理的模块都依赖正确 Bayer 排列 |
| black / white level | `blc.py`、`dpc.py`、`bnf.py` | 决定扣黑、clip、阈值和归一化范围 |
| 四通道统计 | `awb.py`、`cnf.py` | 判断通道响应、白平衡 gain 和色噪风险 |
| histogram / p99 | `gac.py`、`bcc.py`、Tone Mapping | 判断曝光、显示白点和高光压缩压力 |
| ROI | `dpc.py`、`cfa.py`、`eeh.py`、`fcs.py` | 观察坏点、边缘、假彩、锐化 halo 不能只看全图均值 |

因此 Week1 的报告可以补一句关键结论：**没有 Week1 的 metadata 和统计表，OpenISP 那些模块就只是一堆参数；有了 Week1 的坐标系，才知道每个参数该作用在哪个数据域。**

## 和后续模块的关系

```text
Week1 metadata -> 决定 BLC 扣多少
Week1 Bayer pattern -> 决定 DPC / Demosaic 怎么按位置处理
Week1 histogram -> 判断 clipping、黑位、动态范围
Week1 ROI -> 后续做模块前后对比
```

一句话总结：Week1 是在建立 RAW 数据坐标系。没有这个坐标系，后面写出来的 ISP 可能能跑，但很难判断对不对。

## 关键词与参数验收表

| 关键词/参数 | 含义与量纲 | 为什么重要 | 错误症状或验证方法 |
|---|---|---|---|
| `raw_image_visible` | 有效成像区域的二维 Bayer 数组 | 后续 mask、ROI 和空间校正必须使用同一坐标系 | 与完整 RAW/margin 混用会产生固定偏移 |
| `dtype` / bit depth | 存储容器类型 / 有效信号位数 | `uint16` 不代表有效信号一定是 16 bit | 对照 white level；减法前转有符号或浮点 |
| `raw_pattern` + `color_desc` | 2×2 CFA 索引及颜色映射 | 共同决定 RGGB/BGGR/GRBG/GBRG | 在 4×4 小数组打印位置标签 |
| black / white level | 无光基线 / 有效饱和上限，单位为 RAW code value | 定义零点、可用信号跨度和归一化尺度 | 检查 black/white 附近像素比例 |
| ROI | 固定坐标系中的局部评价区域 | 避免全图内容比例掩盖局部问题 | 保存带框预览并人工确认语义 |
| clipping fraction | 接近黑位或白位的像素比例 | 量化欠曝和不可恢复饱和风险 | 分 Bayer 通道和 ROI 统计，不能只看全图 |

## 从输入到结论：可复现教程

### 输入输出合同

| 项目 | 输入 | 输出 | 不能混淆的边界 |
|---|---|---|---|
| 数据 | `data/raw/*.dng` 中的 visible Bayer RAW | metadata JSON、四平面统计、histogram、带框 ROI 预览 | DNG 容器不是 sRGB；`uint16` 只是存储类型 |
| shape/layout | `(H,W)`，单平面 CFA | 统计值为标量/字典，预览为 `(H,W,3)` `uint8` | 预览 RGB 只为观察坐标，不是 Week1 的算法输出 |
| 数值域 | RAW code value，零点在 black level、饱和点在 white level | 统计继续保留 RAW code value；展示图才缩放到 `0..255` | 不同 Sensor 未归一化的码值不能直接横比 |
| 坐标 | visible sensor coordinates | ROI JSON/框必须使用同一坐标；显示时同步 orientation | sensor 坐标和旋正后的 display 坐标不可直接互换 |

核心量的定义如下。设某 ROI 中第 `i` 个 RAW 样本为 `x_i`，样本数为 `N`：

```text
mean = (1/N) * sum(x_i)
std  = sqrt((1/N) * sum((x_i - mean)^2))
clipping_high = count(x_i >= white_level - margin) / N
```

`mean/std` 的单位都是 RAW code value；这里使用总体标准差表达直觉，具体库函数的自由度参数必须随报告记录。`margin` 必须按有效位深声明，不能把一个 14-bit 数据上的固定码值无条件搬到 10-bit Sensor。直方图 `bins` 越多，码值分布更细但单 bin 样本更少；ROI 越大，统计更稳定但越容易混入不同语义区域。

### 参数选择、耦合和失败现象

| 参数 | 当前默认/单位 | 增大时 | 减小时 | 与什么耦合 | 选择与失败检查 |
|---|---:|---|---|---|---|
| `roi_size` | 256 pixel | 统计方差更稳、语义更易混合 | 更局部、也更受噪声/纹理影响 | 分辨率、目标物尺寸 | 默认适合快速审计；框跨越明暗边界时应缩小 |
| `stride` | 128 pixel | 搜索更快但可能漏掉最佳区域 | 定位更细但计算量增加 | `roi_size` | 通常不应大于 ROI 尺寸；保存带框预览核验 |
| histogram `bins` | 由脚本参数决定 | 分辨率提高、曲线更抖 | 趋势更稳、细节被合并 | white-black 有效跨度 | 跨 Sensor 比较前统一为归一化横轴 |
| black/white override | 默认 `null`，RAW code value | 错误上调 black 会夸大欠曝 | 错误下调 white 会夸大饱和 | CFA 通道、bit depth | 常规读取 metadata；只在故障注入时覆盖并留记录 |

### 故障注入、调试和取舍

| 现象 | 第一检查点 | 原因验证 | 不要先做什么 |
|---|---|---|---|
| R/B 位置对调 | `raw_pattern + color_desc` | 打印 4×4 位置标签并对照 metadata | 先调 AWB gain 掩盖 CFA 错误 |
| ROI 框与内容错位 | visible area、orientation | 同一角点在 sensor/display 坐标间往返 | 手工移动框直到“看起来对” |
| `std` 很大就判断噪声高 | ROI 纹理 | 换平坦 ROI 或按亮度分桶 | 用全图 std 当 read noise |
| 高光占比异常 | white level、有效位深 | 分 Bayer 通道统计并看 histogram 尾部 | 用 Tone Mapping 恢复已经饱和的信息 |

取舍要写入结论：大 ROI 提升统计稳定性但降低局部解释力；更多 histogram bins 提高分辨率但降低单 bin 稳定性；自动 ROI 提高批处理一致性，但不如人工语义 ROI 可靠。遇到冲突时，先保证坐标与数据域正确，再讨论参数优化。

### 证据等级与本周连接

| 内容 | 证据等级 | 能证明 | 不能证明 |
|---|---|---|---|
| T01–T14 DNG metadata/统计 | `verified_public` | 脚本能读取公开真实 DNG 并建立输入合同 | 自有手机 Sensor 的噪声/动态范围 |
| 自动 ROI、自然图暗部 std/DR | `verified_proxy` | 同一协议下的诊断趋势 | 实验室 read noise、shot noise、厂商 DR |
| dark frame、PTC、标准灰阶 | `not_run` | 当前无证据 | 不能在报告中补写为真实标定 |

Week1 输出的 CFA、范围、方向和 ROI 合同交给 Week2；任一字段错误都会在 BLC/DPC/LSC 中成为系统性错误，而不是后端“调色”可以可靠修复的问题。

### 动手练习与验收

1. 代码练习：对 T01 打印 4×4 CFA 标签，证明 `raw_pattern` 与 `color_desc` 的联合解释。
2. 参数实验：固定 T01，比较 `roi_size=128/256/512`，解释 mean/std 为什么变化。
3. 故障注入：交换 R/B 标签但不改像素，预测 Week3 的显示现象。
4. 闭卷复述：从 DNG 到 Week2 输入，用一分钟说清 shape、dtype、范围、线性状态和坐标系。

- [ ] 能从零执行两条最小命令并找到 JSON/图片产物
- [ ] 能解释公式中 `x_i`、`N`、`margin` 的含义和单位
- [ ] 能指出一个代理指标与真实实验室指标的差别
- [ ] 能在未知字段处写 `unknown`，而不是依画面猜测
- [ ] 能预测一个参数变化，并用固定输入验证预测

## 本周面试闭环

完整参考答案见[Week 1：RAW 与 Sensor 面试题](../interview/week1_raw_sensor_questions.md)。回答时应使用“结论 → metadata/物理原因 → 本项目检查 → 证据边界”的结构。

1. **概念题：** RAW 与 sRGB 的数据域差异是什么，为什么不能直接互换？
2. **原理题：** `raw_pattern` 为什么必须结合 `color_desc` 才能解释？
3. **参数题：** black level、white level、dtype 最大值和 histogram bins 分别控制什么？
4. **调试题：** Histogram 出现高端堆积时，为什么还必须回到 ROI 和单通道检查？
5. **系统题：** 如何为陌生 DNG 建立输入合同，并把未知信息和证据边界传给后续团队？
