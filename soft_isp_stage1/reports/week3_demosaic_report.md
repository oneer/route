# Week 3-1 Demosaic 学习报告

本次实现最基础的 bilinear demosaic：先在 Bayer RAW 上保留已有采样点，再用周围同色像素的加权平均补齐缺失的 R/G/B 通道。

## 为什么需要 Demosaic

Bayer RAW 的每个像素只记录一种颜色，无法直接显示为 RGB 图像。Demosaic 的任务是把单通道马赛克 RAW 转换成三通道 linear RGB，为后续 AWB、CCM、Gamma/Tone 做准备。

## 本次算法

```text
RAW -> BLC -> DPC -> Bilinear Demosaic -> linear RGB

R/B 缺失值：用附近同色 R/B 像素按 bilinear kernel 插值
G 缺失值：用附近 Gr/Gb 像素按 bilinear kernel 插值
已有 Bayer 采样点：保留原始值，不被插值覆盖
```

Bilinear 的优点是简单、稳定、容易解释；缺点是不会判断边缘方向，所以在斜边、高频纹理和细线附近容易出现模糊、zipper artifact 和 false color。

## 结果总表

| 样张 | Bayer | DPC 候选数 | RGB min | RGB p50 | RGB p99 | OpenCV diff mean | OpenCV diff p99 |
|---|---|---:|---:|---:|---:|---:|---:|
| S01 | BGGR | 371 | 2.00 | 493.00 | 1927.50 | 183.45 | 724.50 |
| S03 | RGGB | 14125 | 0.0000 | 497.00 | 12577.00 | 713.44 | 8639.00 |
| S05 | RGGB | 580 | 0.0000 | 20.00 | 3271.00 | 107.07 | 1400.00 |

## 预览图

### S01 bilinear

![S01 bilinear RGB](figures/S01_a0001-jmac_DSC1459_bilinear_rgb.png)

![S01 OpenCV RGB](figures/S01_a0001-jmac_DSC1459_opencv_rgb.png)

### S03 bilinear

![S03 bilinear RGB](figures/S03_a0003-NKIM_MG_8178_bilinear_rgb.png)

![S03 OpenCV RGB](figures/S03_a0003-NKIM_MG_8178_opencv_rgb.png)

### S05 bilinear

![S05 bilinear RGB](figures/S05_a0005-jn_2007_05_10__564_bilinear_rgb.png)

![S05 OpenCV RGB](figures/S05_a0005-jn_2007_05_10__564_opencv_rgb.png)

## 今天要记住的结论

1. Demosaic 是从 Bayer RAW 进入 RGB 图像的第一步，输出仍然是 linear RGB，不是最终 sRGB 成片。
2. Bayer pattern 必须正确；模式选错会导致颜色通道错位和明显偏色。
3. Bilinear 只做局部平均，不理解边缘方向，所以高频纹理和斜边附近会有伪彩、拉链状边缘和模糊。
4. DPC 的价值会在 Demosaic 后更明显：坏点如果不先修，会被插值扩散到多个 RGB 像素。

## 下一步

在 bilinear RGB 输出稳定后，下一步做 gray-world AWB，让 RGB 通道比例更接近可观看的颜色。
