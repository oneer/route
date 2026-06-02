# Week 4：SIDD Tiny 标准版评估结果

这份报告是比 300-step 快速版更标准的一轮真实数据实验。它仍然使用同一个 `sidd_tiny` 子集，但训练步数更长、NAFNet-lite 也使用更宽的 `width=16` 配置。

实验设置：

```text
数据：SIDD Small sRGB
子集：80 对 train / 20 对 val
crop：512x512 center crop
patch size：128
input baseline：PSNR 26.7302 / SSIM 0.52412
设备：CPU
```

## 1. 指标汇总

| Run | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | Last PSNR | Last SSIM |
|---|---:|---:|---:|---:|---:|---:|
| paired_rgb_sidd_tiny_dncnn_l2_2000 | 35.5356 | 1800 | 0.88367 | 1800 | 34.7538 | 0.87418 |
| paired_rgb_sidd_tiny_unet_l1_1000 | 30.4453 | 1000 | 0.88003 | 1000 | 30.4453 | 0.88003 |
| paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | 33.3269 | 1000 | 0.86223 | 1000 | 33.3269 | 0.86223 |

关键结论：

- `DnCNN residual` 标准版最强，Best PSNR 和 Best SSIM 都最高。
- `NAFNet-lite width=16` 比 300-step width=8 版本明显提升，说明更合理的训练设置非常重要。
- `UNet` 的 SSIM 接近 DnCNN，但 PSNR 差距较大，说明结构相似度和像素误差仍然不是同一个东西。
- DnCNN 在 step 1800 最好，step 2000 略下降，说明更久训练不一定让每个指标继续上涨。

## 2. 指标曲线

![metrics](figures/week4_sidd_tiny_standard_eval/metrics_plot.png)

> 图说明：上半部分是 PSNR 曲线，下半部分是 SSIM 曲线。蓝色 DnCNN 整体最高；黄色 NAFNet-lite 从 step 200 到 1000 持续提升，说明标准版训练比短训更有效；绿色 UNet 的 SSIM 很高，但 PSNR 曲线较低。

## 3. 三联图对比

![triplets](figures/week4_sidd_tiny_standard_eval/triplet_contact_sheet.png)

> 图说明：每个小块是 `noisy | output | clean`。DnCNN 的 output 最接近 clean 的平滑颜色块；NAFNet-lite 到 step 1000 后明显比早期干净；UNet 仍有较明显的纹理/颜色残留，这解释了为什么它的 PSNR 不如 DnCNN。

## 4. Error Map

![paired_rgb_sidd_tiny_dncnn_l2_2000_step_2000_error_x6](figures/week4_sidd_tiny_standard_eval/error_maps/paired_rgb_sidd_tiny_dncnn_l2_2000_step_2000_error_x6.png)

> 图说明：DnCNN 的误差图整体较暗，说明 output 与 clean 的像素差较小。它是这轮标准实验里最稳的 baseline。

![paired_rgb_sidd_tiny_unet_l1_1000_step_1000_error_x6](figures/week4_sidd_tiny_standard_eval/error_maps/paired_rgb_sidd_tiny_unet_l1_1000_step_1000_error_x6.png)

> 图说明：UNet 的误差图用来观察结构相似度高但像素误差仍偏大的现象。它可能保留了一些结构趋势，但颜色或局部纹理仍与 clean 有差距。

![paired_rgb_sidd_tiny_nafnet_lite_l1_1000_step_1000_error_x6](figures/week4_sidd_tiny_standard_eval/error_maps/paired_rgb_sidd_tiny_nafnet_lite_l1_1000_step_1000_error_x6.png)

> 图说明：NAFNet-lite 的误差图比短训版更好，说明 width=16 和 1000 steps 帮助模型继续收敛。但它仍未超过 DnCNN，下一步要继续看更长训练、loss 和学习率。

## 5. 300-step 快速版 vs 标准版

| Model | 快速版 Best PSNR | 标准版 Best PSNR | 快速版 Best SSIM | 标准版 Best SSIM | 说明 |
|---|---:|---:|---:|---:|---|
| DnCNN | 32.7717 | 35.5356 | 0.77100 | 0.88367 | 长训练显著提升 |
| UNet | 28.2856 | 30.4453 | 0.85951 | 0.88003 | 稳定提升，但 PSNR 仍低于 DnCNN |
| NAFNet-lite | 26.8194 | 33.3269 | 0.73509 | 0.86223 | 提升最大，说明短训版严重不足 |

这张表的学习重点：

```text
短训用于确认管线；
标准训用于看模型趋势；
不能用 300-step 结果给现代模型下最终结论。
```

## 6. 下一步

建议后续只围绕一个问题继续做：

```text
NAFNet-lite 能不能通过更长训练或更合适 loss 追上 DnCNN？
```

可选实验：

1. NAFNet-lite `steps=2000`，保持 width=16。
2. NAFNet-lite 改 Charbonnier loss。
3. DnCNN L1 vs L2 标准训练，确认 PSNR 和视觉差异。
4. 扩大 SIDD 子集，比如 train 120 / val 40。

## 7. 如何复现这份报告

先完成三组训练：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_unet_l1_1000.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml
```

再运行评估汇总：

```bash
python ai_isp_stage2/scripts/05_evaluate_runs.py --runs ai_isp_stage2/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 ai_isp_stage2/runs/paired_rgb_sidd_tiny_unet_l1_1000 ai_isp_stage2/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 --output-dir ai_isp_stage2/reports/figures/week4_sidd_tiny_standard_eval --report-md ai_isp_stage2/reports/week4_sidd_tiny_standard_eval_results.md --title "Week 4 SIDD Tiny Standard Evaluation Results"
```

这个脚本会读取每个 run 的：

```text
runs/<name>/metrics.csv
runs/<name>/vis/step_XXXX.png
```

然后生成：

```text
metrics_summary.csv
metrics_plot.png
triplet_contact_sheet.png
error_maps/*.png
week4_sidd_tiny_standard_eval_results.md
```

## 8. 评估脚本怎么实现

`scripts/05_evaluate_runs.py` 做了四件事：

| 步骤 | 实现内容 | 学习意义 |
|---|---|---|
| 读指标 | 用 `csv.DictReader` 读取每个 run 的 `metrics.csv` | 把训练日志变成可比较数据 |
| 找最佳 | 分别找 best PSNR、best SSIM、last metric | 避免只看最后一步 |
| 画曲线 | 用 Pillow 画 PSNR / SSIM 双面板图 | 把数字趋势可视化 |
| 做图像对比 | 收集 `vis/step_*.png`，生成三联图和 error map | 把指标和视觉联系起来 |

为什么 error map 用 `abs(output - clean) * 6`：

```text
output 和 clean 的差异通常很小，直接看不明显；
乘以 6 是为了把误差放大，方便人眼观察哪里还没恢复好。
```

## 9. 面试题和参考回答

**Q1：PSNR 和 SSIM 同时看，为什么还要看三联图？**

PSNR 和 SSIM 都是压缩成单个数字的指标，会丢失很多局部信息。三联图能直接看到颜色偏移、过度平滑、纹理残留和错位。真实图像恢复不能只靠一个数字判断。

**Q2：这轮实验里哪个模型最好？**

如果按当前 SIDD tiny 标准版综合看，DnCNN residual 最稳。它 Best PSNR 是 `35.5356`，Best SSIM 是 `0.88367`，两个指标都最高。但这只是当前数据子集和训练配置下的结论，不代表所有数据和所有训练设置下永远最好。

**Q3：为什么 NAFNet-lite 标准版比短训版提升这么多？**

短训版是 `width=8, 300 steps`，表达能力和训练时间都不足。标准版是 `width=16, 1000 steps`，模型更宽、训练更久，所以 PSNR 从 `26.8194` 提升到 `33.3269`。这说明模型比较必须给足合理训练条件。

**Q4：为什么 DnCNN step 1800 比 step 2000 好？**

验证指标不是单调函数。训练后期可能因为 batch 随机性、学习率、过拟合或验证样本差异出现波动。所以要记录 best checkpoint，而不是默认最后一个 checkpoint 最好。

**Q5：如果面试官问“你怎么保证实验公平”？**

可以回答：我固定了同一个 SIDD tiny split、同一个 patch size、同一个 validation set、同一个评估脚本和同一组可视化方式。仍然需要说明当前 loss 和 steps 不完全一致，所以这是阶段性对比，不是最终论文级公平对比。

**Q6：这个项目目前最有价值的结果是什么？**

最有价值的是建立了从真实 SIDD paired RGB 数据到训练、验证、可视化、error map、周报分析的完整闭环，并用 DnCNN/UNet/NAFNet-lite 做了可复现对比。
