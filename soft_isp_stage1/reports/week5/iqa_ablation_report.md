# Week 5 IQA / 消融实验报告

## 1. 评价目标

Week5 的目标不是证明学习版 pipeline 超过 rawpy，而是把“看起来差不多”变成可量化、可复盘的差异。前面 Week1-4 已经把 Soft-ISP 主链路跑通：

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma
```

Week5 要回答三个问题：

1. 学习版 pipeline 和 rawpy reference 的整体差距有多大？
2. 去掉某个模块后，指标和视觉结果会发生什么变化？
3. 哪些差异来自算法模块本身，哪些差异只是因为 rawpy 的渲染策略和我们的学习版不一样？

这里用 rawpy 生成的 sRGB 图作为参考，计算 PSNR、SSIM 和平均绝对差，同时做模块消融。rawpy reference 不是唯一真值，它包含 LibRaw 的完整处理策略；本项目的学习版模块只用于建立 ISP 链路直觉，所以这些指标用于观察趋势，不作为产品画质结论。

## 2. 评价对象和数据流

评价脚本是 `scripts/15_evaluate_pipeline.py`。它对每张 DNG 做两类输出：

```text
学习版输出：当前 Soft-ISP pipeline 生成 preview
参考输出：rawpy 生成的 sRGB reference
```

随后把两张图对齐到同一尺寸，归一化到 `0..1`，计算全图指标。每个样张还会生成一张 ablation grid，用来并排观察 `full`、关键消融变体和 rawpy reference。

## 3. 指标含义

| 指标 | 含义 | 越大/越小 | 适合观察 | 不适合判断 |
|---|---|---|---|---|
| PSNR | 像素级均方误差换算成分贝 | 越大越接近参考图 | 全局亮度、颜色、曲线差异 | 主观画质、局部伪影、颜色准确性 |
| SSIM | 结构相似性 | 越大越接近参考图 | 结构、对比度、纹理保持 | 色偏是否正确、风格是否好看 |
| Mean Abs Diff | 平均绝对像素差 | 越小越接近参考图 | 整体差异大小 | 差异来自哪个模块 |

这里要特别注意：PSNR/SSIM 高，只表示更像 rawpy reference，不等于更像真实世界，也不等于主观更好。比如 rawpy 的 tone curve、gamma、颜色矩阵和高光处理都比学习版复杂，指标差异可能只是渲染风格差异。

## 4. 消融设计

消融实验的思路是：固定输入样张和大部分 pipeline，只关闭一个关键模块，看输出和指标如何变化。

| 变体 | 含义 | 主要观察点 |
|---|---|---|
| full | BLC + DPC + LSC + Demosaic + AWB + CCM + Tone + Gamma | 学习版完整链路 |
| no_lsc | 去掉 LSC | 边缘亮度、边缘噪声、AWB 是否被边缘影响 |
| no_dpc | 去掉 DPC | 坏点是否扩散进 Demosaic 后的 RGB |
| no_awb | 去掉 AWB | 全局色偏、R/G/B 比例是否偏离 |
| no_ccm | 去掉 CCM | 相机 RGB 和目标显示 RGB 的颜色差异 |
| gamma_only | 去掉 Reinhard tone，只做分位归一化 + Gamma | 判断当前 tone curve 是否更接近 rawpy |

这个设计不是为了证明“某个模块一定让指标变好”。ISP 模块经常是 tradeoff：LSC 可能补亮边缘，也可能放大噪声；Tone Mapping 可能保护高光，也可能让全图更不像 rawpy。

## 5. 代码流程拆解

脚本里的核心流程可以概括为：

```text
1. 读取 DNG，拿到 raw_image_visible、black level、white level、Bayer pattern、orientation、color matrix。
2. 对每个 variant 执行同一条 pipeline。
3. 根据 variant 开关决定是否执行 DPC、LSC、AWB、CCM、Tone。
4. Demosaic 后生成 RGB，再做 Gamma 和 uint8 preview。
5. 读取 rawpy reference。
6. 计算 PSNR、SSIM、Mean Abs Diff。
7. 保存 ablation 对比图和 JSON。
8. 写入 Markdown 报告。
```

对应到代码，`VARIANTS` 定义消融开关，`run_variant()` 执行单个 pipeline，`compute_metrics()` 计算指标，`evaluate_one()` 生成单张样张的所有变体和对比图，`write_report()` 汇总 Markdown。

## 6. 平均指标

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 19.4310 | 0.8384 | 0.0892 |
| no_lsc | 19.5224 | 0.8396 | 0.0881 |
| no_dpc | 19.4353 | 0.8398 | 0.0892 |
| no_awb | 15.6467 | 0.7129 | 0.1291 |
| no_ccm | 19.2934 | 0.8365 | 0.0915 |
| gamma_only | 21.3387 | 0.8502 | 0.0809 |

## 7. 逐样张指标和消融图

### T01

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 18.8141 | 0.9090 | 0.0870 |
| no_lsc | 19.2019 | 0.9111 | 0.0815 |
| no_dpc | 18.8142 | 0.9091 | 0.0870 |
| no_awb | 9.0378 | 0.6157 | 0.2449 |
| no_ccm | 19.2991 | 0.8996 | 0.0843 |
| gamma_only | 27.6054 | 0.9393 | 0.0332 |

![T01 ablation](../figures/T01_a0006-IMG_2787_week5_ablation.png)

### T02

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 19.7389 | 0.8585 | 0.0872 |
| no_lsc | 19.6320 | 0.8580 | 0.0882 |
| no_dpc | 19.7389 | 0.8585 | 0.0872 |
| no_awb | 17.5923 | 0.8436 | 0.1024 |
| no_ccm | 19.6503 | 0.8603 | 0.0896 |
| gamma_only | 16.4300 | 0.8505 | 0.1278 |

![T02 ablation](../figures/T02_a0008-WP_CRW_3959_week5_ablation.png)

### T03

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 23.6889 | 0.8782 | 0.0484 |
| no_lsc | 23.7473 | 0.8790 | 0.0478 |
| no_dpc | 23.6889 | 0.8782 | 0.0484 |
| no_awb | 13.8758 | 0.6815 | 0.1398 |
| no_ccm | 23.5981 | 0.8756 | 0.0496 |
| gamma_only | 26.0908 | 0.8815 | 0.0424 |

![T03 ablation](../figures/T03_a0010-jmac_MG_4807_week5_ablation.png)

### T04

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 20.5457 | 0.8569 | 0.0790 |
| no_lsc | 20.5427 | 0.8578 | 0.0795 |
| no_dpc | 20.5519 | 0.8571 | 0.0789 |
| no_awb | 13.4418 | 0.6650 | 0.1375 |
| no_ccm | 20.4638 | 0.8595 | 0.0798 |
| gamma_only | 21.5551 | 0.8644 | 0.0785 |

![T04 ablation](../figures/T04_a0012-kme_143_week5_ablation.png)

### T05

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 23.6848 | 0.9067 | 0.0514 |
| no_lsc | 23.9521 | 0.9074 | 0.0484 |
| no_dpc | 23.6848 | 0.9067 | 0.0514 |
| no_awb | 16.5175 | 0.7465 | 0.1048 |
| no_ccm | 23.6983 | 0.9121 | 0.0510 |
| gamma_only | 24.3017 | 0.9195 | 0.0579 |

![T05 ablation](../figures/T05_a0014-WP_CRW_6320_week5_ablation.png)

### T06

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 18.5900 | 0.8909 | 0.0924 |
| no_lsc | 18.7522 | 0.8911 | 0.0909 |
| no_dpc | 18.5900 | 0.8909 | 0.0924 |
| no_awb | 12.1866 | 0.7650 | 0.1765 |
| no_ccm | 18.9143 | 0.8922 | 0.0894 |
| gamma_only | 25.6868 | 0.9241 | 0.0445 |

![T06 ablation](../figures/T06_a0018-kme_234_week5_ablation.png)

### T07

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 19.9705 | 0.8415 | 0.0793 |
| no_lsc | 19.9755 | 0.8453 | 0.0773 |
| no_dpc | 19.9709 | 0.8416 | 0.0793 |
| no_awb | 12.4225 | 0.6153 | 0.1526 |
| no_ccm | 19.7383 | 0.8486 | 0.0820 |
| gamma_only | 23.5972 | 0.8499 | 0.0592 |

![T07 ablation](../figures/T07_a0020-jmac_MG_6225_week5_ablation.png)

### T08

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 17.2934 | 0.7787 | 0.1115 |
| no_lsc | 17.1970 | 0.7772 | 0.1138 |
| no_dpc | 17.1647 | 0.7807 | 0.1134 |
| no_awb | 10.4134 | 0.5345 | 0.2362 |
| no_ccm | 17.7792 | 0.7440 | 0.1076 |
| gamma_only | 20.6938 | 0.8354 | 0.0774 |

![T08 ablation](../figures/T08_a0022-IMG_2380_week5_ablation.png)

### T09

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 21.4085 | 0.8415 | 0.0761 |
| no_lsc | 21.8008 | 0.8462 | 0.0722 |
| no_dpc | 21.4085 | 0.8415 | 0.0761 |
| no_awb | 18.9353 | 0.7769 | 0.0898 |
| no_ccm | 20.4890 | 0.8428 | 0.0870 |
| gamma_only | 20.1706 | 0.8330 | 0.0927 |

![T09 ablation](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week5_ablation.png)

### T10

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 12.8952 | 0.7014 | 0.1822 |
| no_lsc | 12.9059 | 0.7012 | 0.1827 |
| no_dpc | 12.8993 | 0.7016 | 0.1821 |
| no_awb | 20.1328 | 0.6447 | 0.0827 |
| no_ccm | 12.9262 | 0.7104 | 0.1818 |
| gamma_only | 11.6383 | 0.6814 | 0.2018 |

![T10 ablation](../figures/T10_a0026-kme_391_week5_ablation.png)

### T11

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 19.0988 | 0.8669 | 0.0822 |
| no_lsc | 19.1546 | 0.8683 | 0.0816 |
| no_dpc | 19.0988 | 0.8669 | 0.0822 |
| no_awb | 19.8367 | 0.8733 | 0.0760 |
| no_ccm | 19.1558 | 0.8708 | 0.0815 |
| gamma_only | 20.3862 | 0.8774 | 0.0758 |

![T11 ablation](../figures/T11_a0033-KE_-2590_week5_ablation.png)

### T12

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 18.4959 | 0.6741 | 0.0940 |
| no_lsc | 18.5056 | 0.6750 | 0.0937 |
| no_dpc | 18.4982 | 0.6743 | 0.0940 |
| no_awb | 17.7403 | 0.5998 | 0.0900 |
| no_ccm | 17.7781 | 0.6822 | 0.1036 |
| gamma_only | 18.2036 | 0.6907 | 0.0927 |

![T12 ablation](../figures/T12_a0034-LSYD4O2202_week5_ablation.png)

### T13

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 18.6800 | 0.8628 | 0.0850 |
| no_lsc | 18.6014 | 0.8636 | 0.0849 |
| no_dpc | 18.8342 | 0.8766 | 0.0840 |
| no_awb | 18.3918 | 0.8621 | 0.0840 |
| no_ccm | 17.9419 | 0.8449 | 0.0975 |
| gamma_only | 22.9578 | 0.8803 | 0.0560 |

![T13 ablation](../figures/T13_a0035-dgw_048_week5_ablation.png)

### T14

| 变体 | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ |
|---|---:|---:|---:|
| full | 19.1288 | 0.8709 | 0.0931 |
| no_lsc | 19.3449 | 0.8737 | 0.0904 |
| no_dpc | 19.1512 | 0.8736 | 0.0929 |
| no_awb | 18.5286 | 0.7567 | 0.0900 |
| no_ccm | 18.6754 | 0.8682 | 0.0956 |
| gamma_only | 19.4245 | 0.8751 | 0.0925 |

![T14 ablation](../figures/T14_a0040-_DSC5693_week5_ablation.png)

## 8. 结果分析

从平均指标看，`gamma_only` 的 PSNR/SSIM 最高，`full` 反而不是最高。这不是说 Tone Mapping 没用，而是说明当前学习版 Reinhard tone 和 rawpy 默认渲染曲线不一样。rawpy reference 更可能接近“分位归一化 + 显示编码 + LibRaw 自己的曲线策略”，所以 `gamma_only` 在像素级指标上更接近它。

`no_awb` 的平均指标下降最明显，说明 AWB 对全局颜色和亮度分布影响很大。去掉 AWB 后，很多样张会出现明显色偏，PSNR/SSIM 也会同步下降。不过 T10、T11 这类样张中 `no_awb` 并不一定最差，说明 Gray World AWB 本身也会失败：如果画面平均颜色并不接近灰色，自动估计出来的 gain 可能反而让输出远离 rawpy。

`no_dpc` 和 `full` 的平均指标非常接近。原因是 DPC 主要处理稀疏坏点，坏点在全图像素里占比很小，所以全图 PSNR/SSIM 不敏感。DPC 的评价更应该看局部 crop、坏点 mask 和修复前后差异，而不是只看全图平均指标。

`no_lsc` 有时比 `full` 指标还略好。这说明当前 LSC 是学习用径向模型，不是由 flat-field 标定得到的真实镜头校正。没有标定图时，LSC 可能把真实场景亮度变化当成暗角补偿，或者放大边缘噪声，所以不能用“指标是否提升”简单判断 LSC 是否正确。

`no_ccm` 的影响介于 AWB 和 DPC 之间。CCM 会改变颜色空间和通道混合，指标变化不一定总是巨大，但它对肤色、绿色、红色饱和度等主观色彩非常关键。真正评价 CCM，后续应该使用色卡和 DeltaE，而不是只和 rawpy 全图做像素距离。

## 9. 指标局限

这次 Week5 的指标有明确边界：

1. rawpy reference 不是 ground truth。它只是一个成熟 ISP 参考输出，不代表真实世界标准答案。
2. PSNR/SSIM 是全图像素指标，对稀疏坏点、局部假彩、边缘拉链、锐化 halo 不够敏感。
3. Mean Abs Diff 能说明平均差异，但不能告诉我们差异来自色偏、亮度、对比度还是局部结构。
4. 指标在 sRGB/显示图上计算，已经混入 tone curve、gamma 和 rawpy 渲染风格，不再是单模块纯评价。
5. 颜色准确性不能只靠 rawpy 对齐，应使用色卡 ROI、标准光源、Lab 空间和 DeltaE。
6. 主观画质还需要局部 crop 和人工观察，尤其是纹理、肤色、天空、暗部噪声和高光区域。

## 10. 下一阶段怎么改

如果继续从学习版 Soft-ISP 往更完整的 ISP 走，Week5 之后优先做这些升级：

1. **把 Demosaic 从 Bilinear 升级到 Malvar/AHD 对比。** 重点看高频纹理、斜边、树枝、文字区域的 false color 和 zipper。
2. **加入 RAW 域 AAF/BNF/CNF 消融。** 参考 OpenISP，把 Demosaic 前的抗混叠和降噪纳入评价。
3. **用 flat-field 做标定版 LSC。** 当前径向 LSC 只能说明概念，不能代表真实镜头 shading 校正。
4. **改进 AWB。** 从 Gray World 进阶到灰点检测、ROI 统计、色温估计，减少大面积单色场景失败。
5. **用色卡拟合 CCM。** 引入 Lab 和 DeltaE，评价颜色准确性，而不是只和 rawpy reference 做像素差。
6. **把 Gamma/Tone 改成 sRGB OETF + LUT 曲线。** 对比 `pow gamma`、sRGB OETF、Reinhard、S-curve 和 LUT。
7. **增加局部评价。** 对坏点、假彩、边缘、暗部噪声、高光区域建立固定 crop，而不是只看全图平均。

## 11. 本周小结

Week5 的核心价值是建立“评价意识”：ISP 不是跑出一张图就结束，而是要能解释每个模块带来的收益、副作用和失败场景。PSNR/SSIM/Mean Abs Diff 可以帮助定位趋势，但不能替代主观观察、局部 crop、色卡 DeltaE 和模块级分析。当前学习版 pipeline 已经完成从 RAW 到可显示图的闭环；下一阶段要做的是把评价从“全图像素接近 rawpy”升级到“针对具体 ISP 问题做针对性验证”。
