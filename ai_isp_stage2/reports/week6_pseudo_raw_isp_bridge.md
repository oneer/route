# Week 6：从 sRGB 去噪走向 RAW / ISP 直觉

Week6 的目标是把前面学到的 RGB 图像恢复，连接到 AI-ISP 里更核心的 RAW / Bayer / pack 概念。

前面 Week2-5 处理的是：

```text
noisy sRGB -> model -> clean sRGB
```

但真实手机 ISP / AI-ISP 经常面对的是：

```text
RAW Bayer -> pack / ISP / network -> RGB
```

所以 Week6 不急着训练 RAW 大模型，而是先用 SIDD 的 clean RGB 做一个 pseudo RAW 实验，理解数据形态怎么变。

## 1. 本周实现了什么

新增脚本：

```text
scripts/08_pseudo_raw_isp_bridge.py
```

它做的事情：

```text
读取一张 clean sRGB 图
  -> 模拟 RGGB Bayer mosaic
  -> pack 成 R / Gr / Gb / B 四通道
  -> 用最简单的 nearest demosaic 恢复 RGB
  -> 生成 error map
  -> 写出 roundtrip MSE / PSNR
```

运行命令：

```bash
python ai_isp_stage2/scripts/08_pseudo_raw_isp_bridge.py --input ai_isp_stage2/datasets/sidd_tiny/val/clean/pair_00001.png --output-dir ai_isp_stage2/reports/figures/week6_pseudo_raw_isp --crop-size 256
```

## 2. 结果图

![Pseudo RAW ISP bridge](figures/week6_pseudo_raw_isp/pseudo_raw_isp_bridge.png)

> 图说明：从左到右依次是 clean sRGB、模拟 RGGB Bayer mosaic、RAW pack 四通道、简单 demosaic、error map。重点看第 2 和第 3 栏：RAW 不是普通 RGB 图，而是单通道 Bayer 采样；pack 后才变成网络常见的 4 通道输入。

指标：

| input | crop size | roundtrip MSE | roundtrip PSNR |
|---|---:|---:|---:|
| `pair_00001.png` | 256 | 0.00029929 | 35.2391 |

这个 PSNR 不是模型成绩，而是说明：

```text
RGB -> Bayer -> pack -> simple demosaic
会损失一部分颜色和空间细节。
```

## 3. 关键概念

### 3.1 Bayer mosaic 是什么

普通 RGB 图每个像素有 3 个值：

```text
R, G, B
```

Bayer RAW 每个像素只有一个颜色采样。以 RGGB 为例：

```text
R G R G ...
G B G B ...
R G R G ...
G B G B ...
```

所以 RAW 看起来像一张单通道图，但每个位置代表不同颜色。

### 3.2 RAW pack 是什么

很多 RAW 网络不会直接输入单通道 Bayer，而是 pack 成 4 个通道：

```text
R  = raw[0::2, 0::2]
Gr = raw[0::2, 1::2]
Gb = raw[1::2, 0::2]
B  = raw[1::2, 1::2]
```

这样输入形状会从：

```text
[H, W]
```

变成：

```text
[4, H/2, W/2]
```

这就是很多 SID / RAW denoise 网络使用 4-channel RAW input 的原因。

### 3.3 Demosaic 是什么

Demosaic 是把 Bayer RAW 恢复成 RGB 图的过程。

直觉上：

```text
每个像素缺两个颜色通道；
demosaic 要从邻域插值补回来。
```

本周脚本用的是非常简单的 nearest 思路，所以 error map 还能看到细节误差。真实 ISP 会用更复杂的 demosaic 算法来减少彩色伪影、锯齿和纹理错误。

## 4. 为什么这对 AI-ISP 重要

RGB 去噪里，模型输入是：

```text
[B, 3, H, W]
```

RAW pack 网络里，模型输入可能是：

```text
[B, 4, H/2, W/2]
```

这会影响：

| 项目 | RGB 去噪 | RAW / AI-ISP |
|---|---|---|
| 输入域 | sRGB，已经过 ISP | RAW，线性传感器数据 |
| 通道 | 3 通道 RGB | 4 通道 RGGB pack |
| 噪声 | 经过 ISP 后的复杂噪声 | 更接近 sensor noise |
| 颜色 | 已有白平衡和颜色矩阵 | 需要 ISP 处理 |
| 模型目标 | clean RGB | denoise RAW / enhanced RGB |

所以 Week6 是一个桥：从“会训练 RGB 模型”过渡到“理解 RAW 网络输入为什么长这样”。

## 5. 面试题和参考回答

**Q1：RAW 和 RGB 最大区别是什么？**

RAW 是传感器原始采样，通常是 Bayer mosaic，每个像素只有一个颜色值，而且是线性光数据。RGB/sRGB 已经过 demosaic、白平衡、颜色校正、gamma 等 ISP 处理，每个像素有完整 RGB 三通道。

**Q2：为什么 RAW 网络常把 RGGB pack 成 4 通道？**

因为 Bayer 相邻像素颜色不同，直接把单通道 RAW 当普通灰度卷积会混淆颜色位置。pack 成 R/Gr/Gb/B 后，每个通道都是同一种采样位置，网络更容易学习颜色和噪声规律。

**Q3：为什么 pack 后空间尺寸减半？**

一个 2x2 RGGB block 被拆成 4 个通道，所以空间尺寸从 HxW 变成 H/2 x W/2，颜色采样位置进入通道维度。

**Q4：Demosaic 为什么会产生伪影？**

因为每个像素缺少两个颜色通道，需要从邻域估计。边缘和高频纹理处插值容易猜错，就会出现彩色边缘、锯齿或纹理错误。

**Q5：AI-ISP 为什么不能只把 RAW 当 RGB 训练？**

因为 RAW 的数值域、颜色排列、噪声模型和 ISP 状态都和 RGB 不同。直接当 RGB 处理会破坏 Bayer 结构，也会混淆传感器噪声和颜色处理问题。

## 6. 本周通过标准

学完 Week6 后，你应该能说清：

1. Bayer mosaic 为什么不是普通灰度图；
2. RGGB pack 如何从 `[H, W]` 变成 `[4, H/2, W/2]`；
3. demosaic 在补什么；
4. RGB 去噪和 RAW 恢复的输入输出差异；
5. 为什么 Week6 是从 SIDD sRGB 走向 SID / RAW low-light 的准备。

## 7. Week 6 升级：pseudo RGGB 可训练 baseline

新版阶段二路线要求 Week 6 不只停留在 `RGB -> Bayer -> pack -> preview` 的可视化，还要证明 RAW-like 4 通道路径真的能进入训练闭环。

因此本周补充了三件事：

```text
1. pseudo RGGB dataset preview
2. 4-channel DnCNN training run
3. RGB vs pseudo RGGB 对比表
```

### 7.1 pseudo RGGB dataset preview

运行命令：

```bash
python ai_isp_stage2/scripts/12_preview_pseudo_raw_dataset.py
```

输出文件：

```text
ai_isp_stage2/reports/figures/week10_pseudo_raw_dataset/pseudo_raw_preview.png
```

这张图用于确认：

- 原始 RGB 图可以转换成 RGGB pack；
- pack 后的 preview 仍然保留大致颜色和结构；
- 每个样本的 pack shape 是 `[4, H/2, W/2]`；
- 这条路径适合接入 4-channel 模型。

### 7.2 4-channel DnCNN 训练

训练配置：

```text
ai_isp_stage2/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
```

关键设置：

| 项目 | 设置 |
|---|---|
| dataset | `paired_pseudo_raw` |
| input channels | 4 |
| output channels | 4 |
| source data | SIDD tiny paired RGB |
| patch size | 128 RGB crop -> 64x64 RGGB pack |
| model | DnCNN residual |
| loss | MSE / L2 |
| steps | 300 |

训练命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
```

训练日志摘要：

```text
step=0100 val psnr=27.7834 ssim=0.54807
step=0200 val psnr=30.8699 ssim=0.66208
step=0300 val psnr=31.7157 ssim=0.77400
```

训练产物：

```text
ai_isp_stage2/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/metrics.csv
ai_isp_stage2/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/checkpoints/best_psnr.pth
ai_isp_stage2/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/checkpoints/last.pth
ai_isp_stage2/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/vis/step_0100.png
ai_isp_stage2/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/vis/step_0200.png
ai_isp_stage2/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/vis/step_0300.png
```

这说明 Week 6 的 RAW-like 路径已经不只是“图像展示”，而是可以生成 metrics、checkpoint 和可视化结果的训练路径。

### 7.3 RGB vs pseudo RGGB 对比

新增汇总脚本：

```text
ai_isp_stage2/scripts/18_export_week6_pseudo_raw_summary.py
```

运行命令：

```bash
python ai_isp_stage2/scripts/18_export_week6_pseudo_raw_summary.py
```

输出文件：

```text
ai_isp_stage2/reports/figures/week6_pseudo_raw_training/week6_pseudo_raw_summary.csv
ai_isp_stage2/reports/figures/week6_pseudo_raw_training/week6_pseudo_raw_summary.md
```

对比结果：

| Label | Run | Dataset | Channels | Effective spatial | Params | Input PSNR / SSIM | Best PSNR | Best SSIM | Gain PSNR / SSIM |
|---|---|---|---:|---|---:|---:|---:|---:|---:|
| RGB 300 | `paired_rgb_sidd_tiny_dncnn_l2_300` | `paired_image` | 3 | 128x128 | 29507 | 26.7302 / 0.52412 | 32.7717@250 | 0.77100@300 | 6.0415 / 0.24688 |
| pseudo RGGB 300 | `pseudo_raw_sidd_tiny_dncnn_l2_300` | `paired_pseudo_raw` | 4 | 64x64 pack from 128x128 RGB crop | 30084 | 26.6785 / 0.50447 | 31.7157@300 | 0.77400@300 | 5.0372 / 0.26953 |

### 7.4 怎么解释这个结果

第一，pseudo RGGB 已经超过自己的 input baseline：

```text
input: 26.6785 PSNR / 0.50447 SSIM
best:  31.7157 PSNR / 0.77400 SSIM
gain:  +5.0372 PSNR / +0.26953 SSIM
```

这说明 RAW-like 4-channel path 是可训练的。

第二，RGB 和 pseudo RGGB 的 PSNR 不要做绝对公平比较。

原因是：

```text
RGB path:        [3, 128, 128]
pseudo RGGB path:[4, 64, 64] pack from 128x128 RGB crop
```

它们的数据形态、通道数和空间分辨率不同。这里的对比重点不是证明 RGGB 比 RGB 强，而是证明：

```text
同一套训练框架可以从 RGB 3-channel 扩展到 RAW-like 4-channel。
```

第三，pseudo RGGB 的参数量略高：

```text
RGB DnCNN:        29507 params
pseudo RGGB DnCNN:30084 params
```

这是因为输入/输出通道从 3 变成 4，首尾卷积参数随之增加。

### 7.5 当前 Week 6 是否达标

按新版学习路线，Week 6 现在已经满足主要要求：

| 要求 | 当前状态 |
|---|---|
| RGGB pack / preview | 已完成 |
| paired pseudo RAW dataset | 已实现 |
| 4-channel DnCNN training | 已完成 |
| metrics.csv | 已生成 |
| best_psnr.pth / last.pth | 已生成 |
| RGB vs RGGB 对比表 | 已生成 |
| 明确 RAW-like 边界 | 已说明，不冒充真实 sensor RAW |

下一步进入 Week 7 时，可以继续保留这个边界：

```text
Week 6 是 RAW-like 输入形态训练；
不是完整真实 RAW sensor pipeline；
后续如果要更接近真实 RAW，需要引入 black level、white balance、CCM、noise model 和真实 RAW 数据。
```
