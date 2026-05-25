# Week 4-3 Tone Mapping 学习报告

Tone Mapping 解决的是动态范围压缩问题。RAW/线性 RGB 里可能有很亮的高光，如果直接线性压到 `0..1`，暗部和中间调很容易被压得不好看。

这一节要区分两个概念：归一化和 Tone Mapping。归一化只是选一个白点把数值缩到 `0..1`；Tone Mapping 是设计一条曲线，让暗部、中间调和高光以更合适的方式进入显示范围。

## 背景：为什么需要动态范围压缩

RAW 能记录的亮度范围通常比普通 `8-bit` 显示图更宽。线性 RGB 里可能同时有很暗的阴影和很亮的天空、高光、灯光。如果只用一个固定比例缩放，有两个常见问题：

1. 为了保住高光，整体会被压暗，暗部和中间调不容易看清。
2. 为了让主体正常，高光会很容易被 clip 成一片白，失去层次。

Tone Mapping 的目标是在这两者之间折中：尽量让主体、中间调、暗部可读，同时让亮部不要过早死白。

## 本周实现的两个简单版本

第一种是 percentile clip：

```text
display_white = percentile(rgb, 99.5)
rgb_norm = clip(rgb / display_white, 0, 1)
```

这里的 `display_white` 不是相机传感器的 `white_level`，而是为了显示选择的白点。使用 `99.5%` 分位点的意思是：让最亮的 0.5% 像素允许被压到白色附近，避免极少数异常高光把整张图压暗。

第二种是全局 Reinhard 曲线：

```text
rgb_tone = rgb_norm / (1 + rgb_norm)
```

Reinhard 的特点是输入越大，压缩越强。几个例子：

```text
0.25 -> 0.25 / 1.25 = 0.200
1.00 -> 1.00 / 2.00 = 0.500
4.00 -> 4.00 / 5.00 = 0.800
```

可以看到，大亮度值不会直接爆成无限大，而是逐渐接近 1。这就是它能更柔和压高光的原因。但代价是整体可能变灰、对比度下降，需要后续再配合对比度曲线或局部 tone mapping。

这两个都不是最终产品级 tone mapping，但很适合作为第一版学习闭环。

## 本周的计算过程

本周 tone mapping 的输入是 CCM 后的线性 RGB。两条分支分别是：

```text
方案 A: rgb_ccm -> percentile normalize -> gamma -> preview
方案 B: rgb_ccm -> percentile normalize -> Reinhard -> gamma -> preview
```

注意 gamma 放在 tone mapping 后面。原因是 tone mapping 的输入应尽量保持线性亮度关系；如果先做 gamma，曲线处理的就不是物理线性光强，后续亮度压缩会变得更难解释。

## 和 OpenISP 后端模块的对照

OpenISP 里没有一个直接叫 `tone_mapping.py` 的模块。它把显示后端拆成多个更具体的 IQ 控制模块，例如：

| OpenISP 模块 | 作用 | 和 Tone Mapping 的关系 |
|---|---|---|
| `bcc.py` | Brightness / Contrast Control | 控制整体亮度和对比度，可视为 tone 曲线之后的风格调节 |
| `hsc.py` | Hue / Saturation Control | 控制色相和饱和度，不解决动态范围，但影响最终观感 |
| `eeh.py` | Edge Enhancement | 提升边缘锐度，常与 tone/contrast 一起影响“清晰感” |
| `fcs.py` | False Color Suppression | 抑制强边缘假彩，避免 demosaic 后彩边过重 |
| `gac.py` | Gamma LUT | 承担显示编码，也可能承载一部分曲线调节 |

这说明当前项目的 Tone Mapping 报告还比较“全局曲线化”：percentile clip 和 Reinhard 都是一条全局曲线。OpenISP 的后端更接近传统 ISP tuning：动态范围、对比度、锐度、假彩、饱和度会拆成多个模块分别调。

两者对比如下：

| 维度 | 当前项目 Tone Mapping | OpenISP 后端 IQ 模块 | 学习结论 |
|---|---|---|---|
| 目标 | 把线性高动态范围压到显示范围 | 分别控制亮度、对比度、锐度、假彩、饱和度 | 完整后端不止一条 tone curve |
| 实现 | percentile clip / Reinhard | BCC/HSC/EE/FCS/Gamma LUT | OpenISP 更像 tuning 模块集合 |
| 数据域 | float RGB | 多为 8-bit RGB/YUV 风格 | 后端常在显示域或 YUV 域工作 |
| 风险 | 高光压缩过度、整体偏灰 | halo、过锐、假彩、过饱和 | 主观 IQ 需要多模块平衡 |
| 验证 | rawpy 对比、亮暗观察 | crop、边缘图、UV 变化、主观评价 | 后端评价不能只靠 PSNR |

因此，当前 Tone Mapping 是“显示输出的第一条曲线”；OpenISP 提醒我们，后续还要把最终 IQ 拆成更细问题：高光、对比度、锐度、假彩、饱和度分别怎么调。

## Tone Mapping 对比

左边是 percentile clip + gamma，中间是 Reinhard + gamma，右边是 rawpy 参考。重点看亮部压缩和整体观感的差异。

读图时建议这样看：

1. 如果 percentile 版本更亮、更有冲击力，但亮部容易白掉，说明简单 clip 的高光保护不足。
2. 如果 Reinhard 版本高光更柔和，但整体偏灰或偏暗，说明它压缩亮部的同时也牺牲了局部对比。
3. rawpy reference 通常看起来更自然，因为它内部不只是一个全局 Reinhard，还可能包含相机 profile、曲线、色彩空间转换、曝光补偿和更复杂的高光处理。

### T01

![T01 tone compare](../figures/T01_a0006-IMG_2787_tone_mapping_compare.png)

### T02

![T02 tone compare](../figures/T02_a0008-WP_CRW_3959_tone_mapping_compare.png)

### T03

![T03 tone compare](../figures/T03_a0010-jmac_MG_4807_tone_mapping_compare.png)

### T04

![T04 tone compare](../figures/T04_a0012-kme_143_tone_mapping_compare.png)

### T05

![T05 tone compare](../figures/T05_a0014-WP_CRW_6320_tone_mapping_compare.png)

### T06

![T06 tone compare](../figures/T06_a0018-kme_234_tone_mapping_compare.png)

### T07

![T07 tone compare](../figures/T07_a0020-jmac_MG_6225_tone_mapping_compare.png)

### T08

![T08 tone compare](../figures/T08_a0022-IMG_2380_tone_mapping_compare.png)

### T09

![T09 tone compare](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_tone_mapping_compare.png)

### T10

![T10 tone compare](../figures/T10_a0026-kme_391_tone_mapping_compare.png)

### T11

![T11 tone compare](../figures/T11_a0033-KE_-2590_tone_mapping_compare.png)

### T12

![T12 tone compare](../figures/T12_a0034-LSYD4O2202_tone_mapping_compare.png)

### T13

![T13 tone compare](../figures/T13_a0035-dgw_048_tone_mapping_compare.png)

### T14

![T14 tone compare](../figures/T14_a0040-_DSC5693_tone_mapping_compare.png)

## 今天要记住的结论

1. Tone Mapping 负责把线性高动态范围压到显示范围。
2. percentile clip 简单直接，但可能丢高光层次。
3. Reinhard 曲线会更柔和地压亮部，但整体可能偏灰或偏暗。
4. Gamma 和 Tone Mapping 经常一起出现在显示输出阶段，但它们解决的问题不同。
5. 一个好的 tone curve 通常要同时考虑高光保护、中间调亮度、暗部可见性和整体对比度。
6. 对照 OpenISP 后要记住：最终观感不是 Tone Mapping 单独决定的，还会被 BCC、HSC、EE、FCS、Gamma LUT 等后端 IQ 模块共同影响。
