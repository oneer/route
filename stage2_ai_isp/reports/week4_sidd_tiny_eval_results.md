# Week 4：SIDD Tiny 真实数据评估结果

本报告基于真实 SIDD Small sRGB 数据的小子集生成。数据不是人工 Gaussian noise，而是真实手机拍摄噪声。

实验设置：

```text
数据：SIDD Small sRGB
子集：80 对 train / 20 对 val
裁剪：每张中心裁剪 512x512
训练：CPU，300 steps
验证：每 50 steps 保存一次 metrics 和三联图
input baseline：PSNR 26.7302 / SSIM 0.52412
```

## 1. 指标汇总

| Run | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | Last PSNR | Last SSIM |
|---|---:|---:|---:|---:|---:|---:|
| paired_rgb_sidd_tiny_dncnn_l2_300 | 32.7717 | 250 | 0.77100 | 300 | 32.2857 | 0.77100 |
| paired_rgb_sidd_tiny_unet_l1_300 | 28.2856 | 300 | 0.85951 | 300 | 28.2856 | 0.85951 |
| paired_rgb_sidd_tiny_nafnet_lite_l1_300 | 26.8194 | 250 | 0.73509 | 300 | 26.0998 | 0.73509 |

怎么读这张表：

- `DnCNN` 的 Best PSNR 最高，说明它在像素误差意义下最接近 clean。
- `UNet` 的 Best SSIM 最高，说明它在结构相似度上表现最好，但 PSNR 不如 DnCNN。
- `NAFNet-lite` 略高于 noisy baseline，但 300 steps 的轻量配置还没有充分发挥。
- `Last PSNR` 不一定等于 `Best PSNR`，例如 DnCNN 在 step 250 PSNR 最好，step 300 略降，说明继续训练不一定总让所有指标同时变好。

## 2. 指标曲线

![metrics](figures/week4_sidd_tiny_eval/metrics_plot.png)

> 图说明：上半部分是 PSNR 曲线，主要看像素级误差；下半部分是 SSIM 曲线，主要看结构相似度。蓝色 DnCNN 的 PSNR 最高，绿色 UNet 的 SSIM 最高，黄色 NAFNet-lite 在短训下仍处于追赶状态。

## 3. 三联图对比

![triplets](figures/week4_sidd_tiny_eval/triplet_contact_sheet.png)

> 图说明：每个小块都是 `noisy | output | clean`。观察时先看 output 是否比 noisy 干净，再看它有没有偏色、过度平滑或残留纹理。DnCNN 更接近 clean 的平滑颜色块；UNet 结构指标高，但图中仍能看到较明显的纹理/颜色残留；NAFNet-lite 有去噪趋势，但还需要更长训练或调参。

## 4. Error Map

![paired_rgb_sidd_tiny_dncnn_l2_300_step_0300_error_x6](figures/week4_sidd_tiny_eval/error_maps/paired_rgb_sidd_tiny_dncnn_l2_300_step_0300_error_x6.png)

> 图说明：DnCNN 的 error map 显示 `abs(output - clean)` 并放大 6 倍。越暗表示误差越小；它整体比 noisy baseline 更接近 clean，但局部仍有纹理残留。

![paired_rgb_sidd_tiny_unet_l1_300_step_0300_error_x6](figures/week4_sidd_tiny_eval/error_maps/paired_rgb_sidd_tiny_unet_l1_300_step_0300_error_x6.png)

> 图说明：UNet 的 error map 用来解释“SSIM 高但 PSNR 不一定最高”。如果结构边界保留得不错，SSIM 可能高；但颜色或像素偏差仍会让 PSNR 低于 DnCNN。

![paired_rgb_sidd_tiny_nafnet_lite_l1_300_step_0300_error_x6](figures/week4_sidd_tiny_eval/error_maps/paired_rgb_sidd_tiny_nafnet_lite_l1_300_step_0300_error_x6.png)

> 图说明：NAFNet-lite 的 error map 说明短训模型已经在减少部分噪声，但整体误差仍比较明显。这个结果不代表 NAFNet 不好，而是说明当前 CPU 轻量版、300 steps、width=8 的配置还不够充分。

## 5. 本轮结论

本轮最重要的结论不是“哪个模型永远最好”，而是学会分开看指标：

```text
DnCNN：PSNR 强，短训下像素误差最低，适合作为真实 RGB baseline。
UNet：SSIM 强，结构相似度高，但视觉上可能保留纹理/颜色残留。
NAFNet-lite：模型管线跑通，但轻量短训不充分，需要更长训练或调宽。
```

下一步建议：

1. 保留 DnCNN 作为 Week3/4 的主 baseline。
2. 给 NAFNet-lite 跑更长 steps，或把 `width` 从 8 提到 16。
3. 对 UNet 做视觉 failure case 观察，确认高 SSIM 是否真的符合人眼感受。
4. 不要只看单一指标，必须同时看 PSNR、SSIM、三联图和 error map。
