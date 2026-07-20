# Week 7：Low-Light RGB 增强小实验

Week 7 的目标是把阶段二从“普通去噪”扩展到更接近 AI-ISP 的低光增强任务。去噪通常是：

```text
noisy -> clean
```

低光增强更接近：

```text
dark + noisy + possible color shift -> normal exposure clean
```

也就是说，模型不只要去噪，还要恢复亮度、颜色和局部结构。

## 1. 本周问题、输入域与 GT

需要增加。

原 Week 7 已经完成了 synthetic low-light 数据生成、low-light input baseline、UNet 训练和 PSNR/SSIM 评估；但按照学习路线里“能分析暗部噪声、色偏、细节糊和过增强”的掌握标准，还缺少低光任务专属诊断。只看 PSNR/SSIM 不能解释模型到底是在增亮、去噪、修色，还是产生了过增强。

本次升级增加了 Week 7 low-light diagnostics：

- 亮度均值和亮度 MAE。
- 暗区亮度 MAE。
- RGB MAE，用于近似观察颜色/通道偏差。
- 欠增强像素比例。
- 过增强像素比例。
- 黑场/白场 clipping 比例。

任务定义：

```text
input : synthetic low-light sRGB, [B,3,H,W], float32, [0,1]
target: 原 SIDD tiny clean sRGB,   [B,3,H,W], float32, [0,1]
model : direct-output UNet
loss  : L1(output, target)
```

GT 不是同一场景重新采集的真实正常曝光照片；它是已有 SIDD clean sRGB。输入由脚本
从 target 合成，因此本周只能验证受控 synthetic degradation 下的增强闭环。

## 2. 数据生成

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

简化公式可写成：

```text
x_linear = inverse_oetf(x_srgb)
x_dark   = exposure * x_linear
variance = shot_noise * x_dark + read_noise
y_linear = clip(x_dark + Normal(0, sqrt(variance)), 0, 1)
y_srgb   = oetf(y_linear)
```

变量含义：`x_srgb` 是 GT sRGB，`x_linear` 是近似逆 OETF 后的线性值，`exposure`
控制欠曝比例，`shot_noise * x_dark` 是随信号变化的方差项，`read_noise` 是简化的读出
噪声方差底，`Normal(0, sqrt(variance))` 采样零均值噪声。所有张量最终裁剪到 `[0,1]`。

例如忽略噪声和 OETF 时，线性像素 `0.5` 乘 `exposure=0.28` 后变成 `0.14`。这个例子
只说明曝光缩放，不代表真实相机曝光、黑电平、增益和色彩处理全过程。

本次参数固定为 `exposure=0.28`、`shot_noise=0.025`、
`read_noise=0.015`、`seed=123`。固定 seed 便于复现，但单一退化参数不能代表真实相机、
不同 ISO、曝光时间、黑电平、色温和 ISP 的分布。

输出目录：

```text
datasets/sidd_low_light_tiny/train/noisy
datasets/sidd_low_light_tiny/train/clean
datasets/sidd_low_light_tiny/val/noisy
datasets/sidd_low_light_tiny/val/clean
```

这里目录仍然叫 `noisy`，是为了复用当前 paired image dataset；实际含义是 low-light input。

运行命令：

```bash
python stage2_ai_isp/scripts/09_prepare_low_light_rgb_subset.py --source-root stage2_ai_isp/datasets/sidd_tiny --output-dir stage2_ai_isp/datasets/sidd_low_light_tiny --figure-dir stage2_ai_isp/reports/figures/week7_low_light_rgb --exposure 0.28 --read-noise 0.015 --shot-noise 0.025 --seed 123 --max-figure-samples 8
```

数据检查图：

![Low-light pairs](figures/week7_low_light_rgb/low_light_pairs_grid.png)

图中上排是 synthetic low-light input，下排是对应 clean target。输入明显变暗且带噪声，clean 保持正常亮度。

## 3. Baseline、训练和评估

测 low-light input baseline：

```bash
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/low_light_sidd_tiny_unet_l1_300.yaml
```

训练 UNet：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/low_light_sidd_tiny_unet_l1_300.yaml
```

评估结果：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/low_light_sidd_tiny_unet_l1_300 --output-dir stage2_ai_isp/reports/figures/week7_low_light_eval --report-md stage2_ai_isp/reports/week7_low_light_eval_results.md --title "Week 7 Low-Light RGB Evaluation Results"
```

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

![Low-light metrics](figures/week7_low_light_eval/metrics_plot.png)

## 4. 新增 Week 7 低光诊断

新增脚本：

```text
scripts/21_export_week7_low_light_diagnostics.py
```

运行命令：

```bash
python stage2_ai_isp/scripts/21_export_week7_low_light_diagnostics.py
```

输出文件：

```text
reports/figures/week7_low_light_diagnostics/week7_low_light_diagnostics.csv
reports/figures/week7_low_light_diagnostics/week7_low_light_diagnostics.md
```

诊断结果基于 20 张 validation 图：

| View | Mean Luma | Luma MAE | Dark Luma MAE | RGB MAE | Under % | Over % | Black Clip % | White Clip % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| low_light_input | 0.1843 | 0.1502 | 0.0715 | 0.1629 | 67.02 | 0.18 | 21.42 | 0.00 |
| model_output | 0.3409 | 0.0249 | 0.0388 | 0.0439 | 0.42 | 1.14 | 0.00 | 0.91 |
| clean_target | 0.3303 | 0.0000 | 0.0000 | 0.0000 | 0.00 | 0.00 | 3.47 | 0.73 |

关键解读：

- Luma MAE 从 `0.1502` 降到 `0.0249`，说明模型确实学到了增亮和亮度恢复。
- Dark-region luma MAE 从 `0.0715` 降到 `0.0388`，暗区仍有残留误差，但已经明显改善。
- RGB MAE 从 `0.1629` 降到 `0.0439`，说明颜色/通道偏差也被显著修正。
- 欠增强比例从 `67.02%` 降到 `0.42%`，这是 low-light enhancement 最核心的收益。
- 过增强比例为 `1.14%`，白场 clipping 为 `0.91%`，当前主要问题不是严重过曝，而是局部暗区和纹理恢复仍不完美。

## 5. 和去噪任务有什么不同

| 对比 | 去噪 | 低光增强 |
|---|---|---|
| 输入 | 亮度基本正常但有噪声 | 暗、噪声强、颜色可能偏 |
| 目标 | 去掉噪声 | 增亮 + 去噪 + 恢复颜色 |
| direct clean | 可行 | 更自然 |
| residual denoise | 很适合 | 不一定适合，因为不只是减噪声 |
| 指标风险 | 过平滑 | 增亮后颜色、纹理和 clipping 都可能出问题 |

这也是为什么 Week 7 选择 UNet direct output，而不是 DnCNN residual denoise。低光增强不是简单的 `clean = input - noise`。

## 6. 面试题和参考回答

**Q1：低光增强和去噪有什么区别？**

去噪主要减少随机噪声，输入和目标亮度通常接近。低光增强还要恢复曝光、颜色和暗部结构，输入和目标之间存在更大的亮度映射差异。

**Q2：为什么低光任务不一定适合 residual denoise？**

Residual denoise 假设 clean 和 noisy 的主体内容差不多，只差噪声。但低光输入和正常曝光 clean 差了亮度、颜色和噪声，不只是一个噪声残差，所以 direct output 或 UNet 这类 encoder-decoder 更自然。

**Q3：为什么 synthetic low-light 也有学习价值？**

它不能替代真实低光 RAW/SID，但可以在没有大 RAW 训练集时先验证增强任务的训练闭环：数据生成、baseline、模型训练、指标、三联图和 failure case 分析。

**Q4：为什么 baseline 只有 14.8932 PSNR？**

因为输入被压暗到 exposure 0.28，又叠加 shot/read noise，和正常 clean 图像差异很大。这个低 baseline 说明任务确实比普通去噪更难。

**Q5：新增 diagnostics 比 PSNR/SSIM 多说明了什么？**

PSNR/SSIM 只能说明整体像素误差和结构相似度。Diagnostics 能说明模型是否真的恢复亮度、暗区误差是否下降、颜色偏差是否改善、有没有欠增强或过增强。这些更贴近 ISP 画质分析。

## 7. 本周通过标准

学完 Week 7 后，应该能解释：

1. 低光增强为什么不只是去噪。
2. synthetic low-light 数据怎么生成。
3. 为什么 UNet 更适合 direct enhancement baseline。
4. 怎么用 low-light input baseline 判断模型是否真的有效。
5. 如何从 triplet、PSNR/SSIM 和 low-light diagnostics 分析增亮、偏色、残留噪声、过增强和 clipping。

还应完成三个练习：

1. 运行前预测：把 exposure 从 `0.28` 改为 `0.15`，哪些指标最先恶化；
2. 用 1～5 张图做 overfit，确认模型能拟合亮度映射，再扩大数据；
3. 只改变一个退化参数，保持 split、seed、模型、loss 和 steps 不变，解释指标与主观图冲突。

## 8. 结果边界与工程表达

补完 diagnostics 后，Week 7 更接近三年 ISP 算法社招的表达要求：不仅能跑一个 low-light enhancement baseline，还能把低光任务拆成曝光、噪声、颜色、暗区和 clipping 几类问题，并用数字说明模型改善了什么、还剩什么。

下一步如果继续增强，优先做真实 SID RAW low-light 或至少加入更真实的曝光 ratio、黑电平、white balance 和 RAW pack 流程；但这可以放到后续阶段，不阻塞 Week 7 进入 Week 8 failure case。

## 9. 退化参数与评价验收表

| 参数/指标 | 当前值或定义 | 调节方向与含义 | 限制 |
|---|---|---|---|
| `exposure=0.28` | 近似线性域信号乘数 | 越小越暗、恢复难度越高；曝光比约为 `1/0.28` | 不等同于真实快门/ISO metadata |
| `read_noise=0.015` | 加性噪声基项，输入范围 `[0,1]` | 增大主要恶化暗区 | 是合成参数，不是 Sensor 标定值 |
| `shot_noise=0.025` | 与 `sqrt(signal)` 相关的噪声项 | 增大使亮度相关噪声更强 | 公式是简化模型 |
| `seed=123` | 合成退化随机种子 | 固定后便于同输入比较 | 单 seed 不代表所有噪声 realization |
| dark-ROI error | 暗区局部恢复误差 | 能补充全图 PSNR 对暗区不敏感的问题 | ROI 语义需人工确认 |
| clipping/color error | 饱和比例与通道/颜色偏差 | 曝光恢复不能以高光截断和偏色为代价 | sRGB 域颜色指标不是 RAW 色彩标定 |

## 10. Week 7 面试五问

1. 低光增强为什么不只是“把图变亮”，而是曝光、噪声、颜色和 clipping 的联合问题？
2. read noise 与 shot noise 的信号依赖关系有何不同？
3. `exposure=0.28` 如何解释，为什么不能直接称为真实曝光比标定？
4. PSNR 提升但 dark-ROI error 仍高时，下一步应改模型还是先改退化/指标？
5. synthetic low-light 到 SID RAW 还缺哪些数据合同和物理因素？

## 11. 教程闭环卡：低光是联合目标，不是单一亮度指标

Week 6 强调输入域，本周强调任务域：输入是由 clean sRGB 合成的暗噪图，GT仍是原 clean
sRGB，shape/layout/range 为 `[B,3,H,W]`/NCHW/`float32 [0,1]`。概念噪声模型可写为：

```text
x_dark = exposure * y
x = clip(x_dark + sqrt(max(x_dark,0))*shot*z1 + read*z2, 0, 1)
```

其中 `z1,z2` 是零均值随机量。该公式只提供受控退化直觉，不是从真实 Sensor 标定出的
Poisson-Gaussian 参数。exposure 变小会同时降低信号和有效 SNR；shot/read 增大则增加恢复
难度，三者耦合，因此单变量 sweep 才能解释结果。

结果按全图、暗区、颜色通道、欠/过增强和 clipping 五层检查。输出更亮但高光截断，体现
亮度恢复与高光保留的权衡，不能简单称“增强更好”。失败调试先确认 GT/退化顺序和随机
seed，再做小样本 overfit，最后分析模型。证据等级为 `verified_synthetic`；不能外推真实
SID、曝光 metadata、RAW 色彩或手机夜景时序。
