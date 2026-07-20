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

> 范围先钉死：这里的源图已经是相机 ISP 渲染后的 sRGB。当前实现只做
> `sRGB -> Bayer 采样/pack` 的 shape bridge，没有恢复真实线性辐照度，也没有反演
> tone mapping、CCM、white balance、black level 或 sensor gain。因此本文统一称
> **pseudo RAW / RAW-like**，不能称为真实 sensor RAW 或完整 unprocessing。

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
python stage2_ai_isp/scripts/08_pseudo_raw_isp_bridge.py --input stage2_ai_isp/datasets/sidd_tiny/val/clean/pair_00001.png --output-dir stage2_ai_isp/reports/figures/week6_pseudo_raw_isp --crop-size 256
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

### 3.4 数值域、black level 和 white level

真实 RAW 常先按下面方式归一化：

```text
raw_norm = clip((raw_code - black_level) / (white_level - black_level), 0, 1)
```

`black_level` 是无光时仍存在的偏置，`white_level` 是传感器编码上限。当前 pseudo
RAW 输入直接来自 `[0,1]` sRGB，既没有真实 code value，也没有相机 metadata，
所以不能套用或声称完成了这一步。

### 3.5 从阶段一 ISP 到完整 unprocessing

阶段一正向链路与理想反向建模的对应关系如下：

| 阶段一正向 ISP | 更完整的反向建模 | 当前实现 |
|---|---|---|
| OETF/gamma | inverse OETF，回到近似线性域 | 未实现 |
| tone mapping | inverse tone mapping | 未实现 |
| CCM | inverse CCM，sRGB 到 camera RGB | 未实现 |
| white balance | inverse WB/gain | 未实现 |
| demosaic | mosaic | 仅做固定 RGGB 采样 |
| sensor noise reduction | shot/read noise synthesis | pseudo RAW 路径未实现 |

因此，本周证明的是 4-channel 数据接口和训练闭环，不是物理可信的 RAW 合成。

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
python stage2_ai_isp/scripts/12_preview_pseudo_raw_dataset.py
```

输出文件：

```text
stage2_ai_isp/reports/figures/week10_pseudo_raw_dataset/pseudo_raw_preview.png
```

这张图用于确认：

- 原始 RGB 图可以转换成 RGGB pack；
- pack 后的 preview 仍然保留大致颜色和结构；
- 每个样本的 pack shape 是 `[4, H/2, W/2]`；
- 这条路径适合接入 4-channel 模型。

### 7.2 4-channel DnCNN 训练

训练配置：

```text
stage2_ai_isp/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
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
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
```

训练日志摘要：

```text
step=0100 val psnr=27.7834 ssim=0.54807
step=0200 val psnr=30.8699 ssim=0.66208
step=0300 val psnr=31.7157 ssim=0.77400
```

训练产物：

```text
stage2_ai_isp/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/metrics.csv
stage2_ai_isp/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/checkpoints/best_psnr.pth
stage2_ai_isp/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/checkpoints/last.pth
stage2_ai_isp/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/vis/step_0100.png
stage2_ai_isp/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/vis/step_0200.png
stage2_ai_isp/runs/pseudo_raw_sidd_tiny_dncnn_l2_300/vis/step_0300.png
```

这说明 Week 6 的 RAW-like 路径已经不只是“图像展示”，而是可以生成 metrics、checkpoint 和可视化结果的训练路径。

### 7.3 RGB vs pseudo RGGB 对比

新增汇总脚本：

```text
stage2_ai_isp/scripts/18_export_week6_pseudo_raw_summary.py
```

运行命令：

```bash
python stage2_ai_isp/scripts/18_export_week6_pseudo_raw_summary.py
```

输出文件：

```text
stage2_ai_isp/reports/figures/week6_pseudo_raw_training/week6_pseudo_raw_summary.csv
stage2_ai_isp/reports/figures/week6_pseudo_raw_training/week6_pseudo_raw_summary.md
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

### 7.6 本周练习与掌握标准

1. 手算一个 `4x4` RGGB mosaic pack 后四个 `2x2` 通道的位置。
2. 打印一个 batch，确认 RGB crop `[B,3,128,128]` 变成
   `[B,4,64,64]`，target 使用同一几何区域。
3. 只取 1～5 对图片 overfit；若 loss 不下降，先查 pair、pack 和 residual 语义。
4. 写出当前 pseudo RAW 与真实 RAW 至少五项 domain gap。
5. 设计一个单变量实验：只增加 inverse OETF，保持 split、seed、模型和训练步数不变。

## 8. RAW Bridge 关键词与参数验收表

| 关键词/参数 | 本周实际含义 | 为什么需要 | 证据边界 |
|---|---|---|---|
| mosaic | 从 RGB 每个位置只采对应 CFA 通道 | 模拟 Bayer 空间采样结构 | 输入源仍是 ISP 后 sRGB |
| RGGB pack | 将 2×2 Bayer block 打包成 4 通道 | 降低空间尺寸并保留四种 CFA 位置 | shape bridge，不自动恢复真实 RAW 物理属性 |
| `in/out_channels=4` | DnCNN 接收并输出 packed RGGB | 网络接口必须与 pack 合同一致 | 不能拿 RGB 3 通道 checkpoint 直接加载 |
| inverse OETF | 尝试从显示编码回到近似线性域 | 真实 RAW 接近线性，sRGB 不是 | clipping、tone 和 CCM 不可被精确逆转 |
| black/white level | RAW 零点和饱和上限 | 影响 normalize、噪声和 clipping | pseudo RAW 当前没有真实 metadata |
| unprocessing | 近似逆转 ISP 以合成 RAW-like 数据 | 缩小 RGB→RAW domain gap | 仍需与真实 RAW 验证，不是 ground truth |

## 9. Week 6 面试五问

1. Bayer mosaic 与 4-channel RAW pack 的 shape 如何变化？
2. 为什么从 sRGB 抽样得到 RGGB 仍不是真实 RAW？
3. black level、white level、linearization 和 WB 在真实 RAW 训练中如何进入合同？
4. inverse OETF 能逆转什么，不能恢复哪些已经丢失的信息？
5. 怎样用真实 RAW 与 pseudo RAW 设计 domain-gap 对照实验？

## 10. 教程闭环卡：shape bridge 不等于物理反演

本周从 Week 5 接收 `[B,3,H,W]` sRGB，输出 `[B,4,H/2,W/2]` pseudo RGGB 和可训练
checkpoint；它为后续真实 RAW 学习准备接口，不提供 Sensor 物理证据。固定 RGGB pack 为：

```text
R=x[...,0::2,0::2]  Gr=x[...,0::2,1::2]
Gb=x[...,1::2,0::2] B=x[...,1::2,1::2]
```

H/W 必须为偶数；crop、flip、rotate 需要同步更新 CFA 语义，否则通道标签会错。真实 RAW
还需要 black/white level、线性化、WB/CCM、曝光/ISO 与 shot/read noise metadata。由于 tone
mapping、clipping 和局部 ISP 可能不可逆，从 sRGB 反推 RAW 只能近似。

失败调试顺序：先用4×4手算 pack/unpack，再查 CFA、shape、range，最后看训练。故障注入可交换
Gr/Gb 或从奇数坐标裁剪，观察颜色/合同错误。trade-off 是 pack 降低空间尺寸、增加通道，
便于卷积处理却改变内存布局和 receptive field 解释；这是接口便利性与空间语义之间的工程
权衡。本周证据为 `verified_partial` 加
`verified_public` 源图；不可写成真实 RAW 去噪。
