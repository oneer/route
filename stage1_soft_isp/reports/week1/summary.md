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

要正确处理 RAW，至少要知道：

- `shape`：可见 RAW 图像尺寸
- `dtype`：像素存储类型
- `black_level_per_channel`：黑电平
- `white_level`：白电平 / 饱和上限
- `raw_pattern` / `color_desc`：Bayer 排列

没有这些信息，后面的 BLC、Demosaic、AWB 都可能走错。

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
