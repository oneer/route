# Week 1 学习总结：RAW / Sensor 数据直觉

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

## 和后续模块的关系

```text
Week1 metadata -> 决定 BLC 扣多少
Week1 Bayer pattern -> 决定 DPC / Demosaic 怎么按位置处理
Week1 histogram -> 判断 clipping、黑位、动态范围
Week1 ROI -> 后续做模块前后对比
```

一句话总结：Week1 是在建立 RAW 数据坐标系。没有这个坐标系，后面写出来的 ISP 可能能跑，但很难判断对不对。
