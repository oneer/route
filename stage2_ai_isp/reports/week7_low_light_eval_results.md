# Week 7：Low-Light RGB 评估结果

本报告由 `scripts/05_evaluate_runs.py` 生成后整理。任务是从 synthetic low-light RGB 恢复到 clean RGB。

input baseline：

```text
PSNR = 14.8932
SSIM = 0.23094
```

## 1. 指标汇总

| Run | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | Last PSNR | Last SSIM |
|---|---:|---:|---:|---:|---:|---:|
| low_light_sidd_tiny_unet_l1_300 | 24.7821 | 300 | 0.81468 | 300 | 24.7821 | 0.81468 |

结论：

```text
UNet 300 steps 明显超过 low-light input baseline，
说明模型学到了增亮、去噪和颜色恢复的基本映射。
```

## 2. 指标曲线

![metrics](figures/week7_low_light_eval/metrics_plot.png)

> 图说明：曲线显示 PSNR 和 SSIM 随训练 step 提升，step 300 达到本轮最好。因为低光输入 baseline 很低，所以提升幅度非常明显。

## 3. 三联图

![triplets](figures/week7_low_light_eval/triplet_contact_sheet.png)

> 图说明：每个小块是 `low-light input | output | clean`。output 逐渐变亮并接近 clean，但局部仍有纹理残留和颜色不完全一致的问题。

## 4. Error Map

![low_light_sidd_tiny_unet_l1_300_step_0300_error_x6](figures/week7_low_light_eval/error_maps/low_light_sidd_tiny_unet_l1_300_step_0300_error_x6.png)

> 图说明：error map 显示 `abs(output - clean)` 放大 6 倍。亮区表示模型仍未恢复好的位置，通常对应暗部噪声、纹理残留或颜色偏差。

## 5. 下一步

1. 把 low-light UNet 从 300 steps 提到 1000 steps。
2. 尝试加入 SSIM loss 或 Charbonnier loss。
3. 未来接入真实 SID RAW，比较 synthetic low-light 和真实低光 RAW 的差异。
