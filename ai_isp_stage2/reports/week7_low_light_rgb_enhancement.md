# Week 7：低光 RGB 增强小实验

Week7 的目标是从“去噪”扩展到“低光增强”。

去噪任务通常是：

```text
noisy -> clean
```

低光增强更接近：

```text
dark + noisy + color shift -> normal exposure clean
```

也就是说，模型不只要去噪，还要恢复亮度、颜色和局部结构。

## 1. 本周实现了什么

新增脚本：

```text
scripts/09_prepare_low_light_rgb_subset.py
```

它从 SIDD tiny 的 clean 图生成 synthetic low-light 输入：

```text
clean RGB
  -> 转到近似 linear space
  -> 乘 exposure=0.28 模拟欠曝
  -> 加 shot/read noise
  -> 转回 sRGB
  -> 保存为 low-light input
```

输出目录：

```text
datasets/sidd_low_light_tiny/train/noisy
datasets/sidd_low_light_tiny/train/clean
datasets/sidd_low_light_tiny/val/noisy
datasets/sidd_low_light_tiny/val/clean
```

这里目录仍然叫 `noisy`，是为了复用当前 paired image dataset；实际含义是 low-light input。

## 2. 操作命令

准备数据：

```bash
python ai_isp_stage2/scripts/09_prepare_low_light_rgb_subset.py --source-root ai_isp_stage2/datasets/sidd_tiny --output-dir ai_isp_stage2/datasets/sidd_low_light_tiny --figure-dir ai_isp_stage2/reports/figures/week7_low_light_rgb --exposure 0.28 --read-noise 0.015 --shot-noise 0.025 --seed 123 --max-figure-samples 8
```

测 low-light input baseline：

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/low_light_sidd_tiny_unet_l1_300.yaml
```

训练 UNet：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/low_light_sidd_tiny_unet_l1_300.yaml
```

评估结果：

```bash
python ai_isp_stage2/scripts/05_evaluate_runs.py --runs ai_isp_stage2/runs/low_light_sidd_tiny_unet_l1_300 --output-dir ai_isp_stage2/reports/figures/week7_low_light_eval --report-md ai_isp_stage2/reports/week7_low_light_eval_results.md --title "Week 7 Low-Light RGB Evaluation Results"
```

## 3. 数据检查图

![Low-light pairs](figures/week7_low_light_rgb/low_light_pairs_grid.png)

> 图说明：上排是 synthetic low-light input，下排是对应 clean target。可以看到输入明显变暗且带噪声，clean 保持正常亮度。这个任务比纯去噪更难，因为模型需要同时增亮和去噪。

## 4. Baseline 和训练结果

low-light input baseline：

```text
PSNR = 14.8932
SSIM = 0.23094
```

UNet 300-step 结果：

| Model | Steps | Loss | Best PSNR | Best SSIM | 结论 |
|---|---:|---|---:|---:|---|
| low-light UNet | 300 | L1 | 24.7821 | 0.81468 | 明显超过低光输入 baseline |

训练日志关键点：

| Step | PSNR | SSIM |
|---:|---:|---:|
| 50 | 18.37 | 0.7984 |
| 100 | 19.26 | 0.7853 |
| 150 | 19.40 | 0.7754 |
| 200 | 19.76 | 0.7830 |
| 250 | 22.83 | 0.8082 |
| 300 | 24.78 | 0.8147 |

![Low-light triplets](figures/week7_low_light_eval/triplet_contact_sheet.png)

> 图说明：每个小块是 `low-light input | output | clean`。从 step 50 到 step 300，output 逐渐变亮，颜色更接近 clean，但仍有纹理残留和局部平滑问题。

![Low-light metrics](figures/week7_low_light_eval/metrics_plot.png)

> 图说明：PSNR 和 SSIM 都明显高于 baseline，说明模型确实学到了增亮和去噪。但曲线还在上升，300 steps 只是一个学习版结果，不是最终低光增强模型。

## 5. 和去噪任务有什么不同

| 对比 | 去噪 | 低光增强 |
|---|---|---|
| 输入 | 亮度基本正常但有噪声 | 暗、噪声强、颜色可能偏 |
| 目标 | 去掉噪声 | 增亮 + 去噪 + 恢复颜色 |
| direct clean | 可行 | 更自然 |
| residual denoise | 很适合 | 不一定适合，因为不只是减噪声 |
| 指标风险 | 过平滑 | 增亮后颜色和纹理可能错 |

这也是为什么 Week7 选择 UNet direct output，而不是 DnCNN residual denoise。低光增强不是简单的 `clean = input - noise`。

## 6. 面试题和参考回答

**Q1：低光增强和去噪有什么区别？**

去噪主要减少随机噪声，输入和目标亮度通常接近。低光增强还要恢复曝光、颜色和暗部结构，输入和目标之间存在更大的亮度映射差异。

**Q2：为什么低光任务不一定适合 residual denoise？**

residual denoise 假设 clean 和 noisy 的主体内容差不多，只差噪声。但低光输入和正常曝光 clean 差了亮度、颜色和噪声，不只是一个噪声残差，所以 direct output 或 UNet 这类 encoder-decoder 更自然。

**Q3：为什么 synthetic low-light 也有学习价值？**

它不能替代真实低光 RAW/SID，但可以在没有大 RAW 训练集时先验证增强任务的训练闭环：数据生成、baseline、模型训练、指标、三联图和 failure case 分析。

**Q4：为什么 baseline 只有 14.8932 PSNR？**

因为输入被压暗到 exposure 0.28，又叠加 shot/read noise，和正常 clean 图像差异很大。这个低 baseline 说明任务确实比普通去噪更难。

**Q5：下一步怎么走向真实低光 RAW？**

下一步要学习 SID 数据格式：短曝光 RAW 作为输入，长曝光 RGB/RAW 作为 target；然后实现 RAW pack，输入从 3 通道 RGB 变成 4 通道 RAW pack。

## 7. 本周通过标准

学完 Week7 后，你应该能解释：

1. 低光增强为什么不只是去噪；
2. synthetic low-light 数据怎么生成；
3. 为什么 UNet 更适合 direct enhancement；
4. 怎么用 baseline 判断模型是否真的有效；
5. 如何从三联图看增亮、偏色、残留噪声和过平滑。
