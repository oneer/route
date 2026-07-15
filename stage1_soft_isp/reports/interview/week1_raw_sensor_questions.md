# Week 1 面试题：RAW、DNG Metadata 与 Sensor 数据直觉

本周面试目标不是背 API 名称，而是证明自己能为陌生 DNG 建立可靠输入合同，并知道每项 metadata 会怎样影响后续 ISP。

## 1. RAW 和普通 RGB 图片的本质区别是什么？

### 核心回答

常见 Bayer RAW 是传感器读出后的二维采样阵列。每个像素只记录 R、G、B 中一种滤色片响应，数据通常仍接近线性光强，并带有 black level、饱和上限、坏点、镜头阴影和噪声等传感器特性。

普通 JPEG/PNG RGB 通常已经经过 Demosaic、AWB、CCM、Tone Mapping、Gamma/OETF、锐化和压缩。它的每个像素都有三个面向显示的颜色通道，已经不再是原始传感器数据域。

### 为什么这个区别重要

- RAW 的二维数值不能直接解释成灰度亮度，更不能复制三份当 RGB。
- RAW 域模块必须知道 CFA 位置、black/white level 和有效区域。
- RGB 域的颜色、亮度和图像质量指标不能不加说明地直接用于未处理 RAW。

### 做错后的表现

把 RAW 当 RGB 会造成马赛克纹理、整体偏色、亮度尺度错误；提前做 Gamma 或转成 8-bit 还会破坏后续 BLC、AWB 和 CCM 依赖的线性关系。

### 项目验证

打印 `raw_image_visible.shape`，它应是 `(H, W)`；Demosaic 后才变成 `(H, W, 3)`。同时比较 RAW histogram 和最终 preview，可以看到两者的数据域和分布完全不同。

## 2. 处理陌生 DNG 时，最先读取哪些信息？为什么？

### 核心回答

我会先建立 RAW 输入合同，而不是先看最终渲染：

| 顺序 | 信息 | 代表什么 | 为什么要读 | 错误后果 |
|---:|---|---|---|---|
| 1 | `raw_image_visible.shape/dtype/min/max` | 可见像素数组、存储类型和值域 | 决定数组尺寸、中间类型和基本数值检查 | mask 错位、无符号下溢、尺度判断错误 |
| 2 | active/visible area、margins | 完整传感器和有效图像的坐标关系 | 坏点表、LSC、ROI 必须使用一致坐标 | 所有空间标注固定平移 |
| 3 | `raw_pattern` + `color_desc` | CFA 索引及颜色含义 | 推断 RGGB/BGGR/GRBG/GBRG | Demosaic 串色，per-channel 校正作用错位 |
| 4 | `black_level_per_channel` | 无光时的读出基线 | BLC 和暗部统计的零点 | 欠扣发灰，过扣死黑并污染 AWB |
| 5 | `white_level` / per-channel white | 有效饱和上限 | clamp、归一化和 clipping 判断 | 高光误截或漏报饱和 |
| 6 | orientation / `sizes.flip` | 传感器坐标到显示方向的变换 | 对齐 preview、reference 和 ROI | 图像方向对了但框错位 |
| 7 | camera WB / color matrix | 白平衡和颜色空间参考 | 为 AWB/CCM 提供 baseline | 增益或矩阵约定错误导致系统性色偏 |

`uint16` 只表示存储容器，不等于传感器有 16 个有效 bit；`raw_pattern` 也必须结合 `color_desc` 才能解释为颜色。缺失字段应保留为 unknown，并显式记录 fallback。

### 项目验证

本项目用 metadata manifest 记录文件 hash、尺寸、Bayer、black/white level、方向、WB 和色彩矩阵。最小验证是检查字段形状、有限性、取值范围及不同字段之间是否自洽，而不是只确认 API 没报错。

### 常见追问

**为什么 camera white balance 不是 ground truth？** 它可能缺失、来自机内估计或只适用于拍摄时策略；可作参考，但仍需独立 AWB baseline 和中性 ROI 验证。

## 3. `raw_pattern` 和 `color_desc` 如何共同确定 Bayer pattern？

### 核心回答

`raw_pattern` 给出 2×2 周期中每个位置保存的通道索引，`color_desc` 给出索引对应的颜色字符。只有把索引映射成字符后，才能得到 RGGB、BGGR、GRBG 或 GBRG。

例如 `raw_pattern[0,0] == 0` 本身不够，只有确认 `color_desc[0] == 'R'`，才能说左上角是红色位置。对于两个绿色位置，还要保留空间身份 Gr/Gb，不能只看它们都叫 G 就丢掉行列关系。

### 为什么必须正确

BLC、DPC、LSC、RAW 域 WB 和 Demosaic 都按 Bayer 位置工作。pattern 错误不是局部误差，而是整条前端流水线的通道解释都错。

### 最小验证

在 4×4 小数组上打印位置标签，检查每个颜色 mask 是否覆盖预期行列；Demosaic 单元测试还要确认真实采样位置没有被插值覆盖。

## 4. black level 和 white level 分别是什么？

### 核心回答

black level 是无光时传感器、模拟前端和 ADC 仍然输出的基线码值。它不是“场景中的黑色亮度”，而是读出系统的零点偏置。

white level 是相机定义的有效信号上限，接近饱和或可靠码值上界。它不一定等于 dtype 最大值，例如数组是 `uint16`，有效 white level 仍可能只有 4095 或 16000。

BLC 后每个位置的有效范围近似为：

```text
signal = clip(raw - black, 0, white - black)
```

### 为什么要同时读取

black 决定零点，white 决定上限，两者共同定义可用信号跨度。只减 black 不更新有效 white，会让归一化和 clipping 统计使用错误尺度。

### 错误后果与验证

- black 欠扣：暗部发灰、通道偏置残留、AWB 统计偏移。
- black 过扣：暗部大量归零、纹理不可逆丢失。
- white 太小：高光被过早截断；white 太大：归一化偏暗并漏报饱和。
- 验证时分别统计 black 附近、0 附近和 white 附近像素比例，并按 Bayer 位置检查，而不是只看全图均值。

## 5. 为什么 R、Gr、Gb、B 四个 Bayer 平面的均值通常不同？

### 核心回答

原因包括场景光谱、光源色温、传感器滤色片透过率、镜头与像素角度响应，以及尚未执行 BLC、AWB 和 CCM。绿色采样数量更多是空间采样设计，不等于绿色平面的单像素响应必然更高，但实际相机中 G 响应常与 R/B 不同。

Gr 和 Gb 都是绿色滤色片，但位于不同空间位置。它们应该在大范围统计上相对接近；若差异异常，要检查 Bayer offset、行列读出差异、镜头阴影和场景结构。

### 面试中不能说什么

不能仅凭 R/G/B 全图均值不同就断言“图像偏色”或“AWB 一定有问题”。全图均值混合了场景内容和传感器响应，需要中性 ROI 或标准目标才能评价颜色中性。

### 项目验证

先按 Bayer 位置分别统计 mean、std、p01、p50、p99，再比较多个场景。Gr/Gb 的一致性可作为 pattern 和读取位置的 sanity check，但不是严格传感器一致性标定。

## 6. RAW Histogram 能回答哪些问题，不能回答哪些问题？

### 能回答

- 像素是否大量靠近 black level，暗部是否可能在 BLC 后被截断。
- 像素是否堆积在 white level，高光是否存在 clipping 风险。
- 四个 Bayer 平面的分布是否明显分离，是否存在通道基线或响应差异。
- 参数或模块前后分布怎样移动，例如 BLC 是否把暗部基线移向 0。

### 不能单独回答

Histogram 丢失空间位置，不能说明饱和发生在灯光、天空还是皮肤，也不能直接证明噪声、清晰度、颜色准确性或主观画质。

### 正确验证方式

Histogram 必须和 ROI、clipping 比例及图像位置对应。若看到高端堆积，要回到高光 ROI 检查通道是否同时饱和；若暗部 std 大，要确认那是噪声还是纹理。

## 7. 为什么需要 ROI，而不能只看全图统计？

### 核心回答

全图统计会被场景占比主导。大面积天空会影响 B 通道，大面积草地会影响 G 通道；这不等于算法失败。ROI 用来把统计绑定到具有明确语义或画质目标的局部区域。

| ROI | 主要检查 | 可能误判 |
|---|---|---|
| 暗部 | black level、噪声、暗部 clipping | 把真实黑纹理当噪声 |
| 中性区域 | AWB、通道比例、暗部偏色 | 区域并非真正灰色 |
| 高光 | 饱和通道和高光颜色 | 只看亮度而忽略单通道 clip |
| 边缘/纹理 | Demosaic zipper、false color、锐度 | crop 位置和方向不一致 |
| 角落 | LSC 和边缘噪声 | 把真实光照渐变当镜头阴影 |

ROI 必须记录坐标系、选择依据和失败条件。自动 ROI 是可复现 baseline，但语义 ROI 通常需要人工确认。

## 8. 给你一张从未见过的 DNG，你会怎样判断它能否进入 Pipeline？

### 回答框架

1. 检查文件能否解码、hash 和来源是否明确。
2. 建立数组合同：二维 shape、dtype、min/max、有限性。
3. 建立几何合同：visible area、margins、orientation。
4. 建立 CFA 合同：pattern、color description 和四平面坐标。
5. 建立数值合同：black/white level、低端/高端 clipping。
6. 记录 WB 和 color matrix，但把缺失或不可靠值标为 unknown。
7. 先运行小数组测试和单样张中间结果，再运行完整链路。

### 面试加分点

我不会因为最终 preview 看起来正常就认为输入合同正确。成熟库可能掩盖 metadata 错误；必须保存中间结果，并能解释每一步的 shape、dtype、range 和坐标系。

## Week 1 一分钟复述

Week 1 的核心不是做 ISP 增强，而是定义输入。RAW 是带 CFA、数值基线和传感器特性的二维线性采样；metadata 决定像素的位置、颜色、零点、上限和方向。我用四通道统计、Histogram 和 ROI 检查输入是否自洽，并明确区分全图统计、局部证据和标准标定结论。
