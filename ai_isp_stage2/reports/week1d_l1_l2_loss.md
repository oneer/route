# Week 1D：L1 vs L2 Loss 对比

## 1. 为什么要比较 loss

前面已经验证了两件事：

1. TinyCNN 能跑通最小训练闭环。
2. DnCNN residual 比 direct clean prediction 更适合这个 toy denoise 任务。

接下来要学的是：同一个模型、同一份数据，如果只改变 loss，训练结果会不会不同。

这一步很重要，因为图像恢复不只是“换模型”。Loss 会直接定义模型训练时追求什么：

```text
模型不是自然知道什么叫好图。
模型只知道怎么让 loss 变小。
```

所以 Week 1D 的问题是：

```text
同样是 DnCNN residual，L1 loss 和 L2/MSE loss 会带来什么差异？
```

## 2. 控制变量实验设计

为了让对比公平，两组实验只改变 loss，其余设置保持一致。

| 项目 | L1 实验 | L2 实验 |
|---|---|---|
| 配置 | `toy_rgb_denoise_dncnn_l1.yaml` | `toy_rgb_denoise_dncnn_l2.yaml` |
| 模型 | DnCNN residual | DnCNN residual |
| patch size | 64 | 64 |
| train size | 512 | 512 |
| val size | 32 | 32 |
| 噪声范围 | sigma 0.03 - 0.12 | sigma 0.03 - 0.12 |
| steps | 300 | 300 |
| batch size | 8 | 8 |
| learning rate | 0.001 | 0.001 |
| 唯一变量 | `loss: l1` | `loss: mse` |

这里的 `mse` 就是常说的 L2 loss：

```text
L1 = mean(abs(output - target))
L2/MSE = mean((output - target)^2)
```

## 3. 运行命令

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l1.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2.yaml
```

输出目录：

- `ai_isp_stage2/runs/toy_rgb_denoise_dncnn_l1/`
- `ai_isp_stage2/runs/toy_rgb_denoise_dncnn_l2/`

## 4. 结果表

### L1 loss

| step | train loss | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 50 | 0.047457 | 24.7426 | 0.49063 |
| 100 | 0.031129 | 27.4612 | 0.65084 |
| 150 | 0.024995 | 30.3908 | 0.84588 |
| 200 | 0.022051 | 30.7689 | 0.88403 |
| 250 | 0.023091 | 31.0023 | 0.89528 |
| 300 | 0.019765 | 31.1442 | 0.90096 |

### L2 / MSE loss

| step | train loss | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 50 | 0.004111 | 25.0671 | 0.51173 |
| 100 | 0.001419 | 28.3377 | 0.68979 |
| 150 | 0.001030 | 30.7796 | 0.85712 |
| 200 | 0.000966 | 31.0648 | 0.87936 |
| 250 | 0.001004 | 31.0929 | 0.89107 |
| 300 | 0.000719 | 31.7001 | 0.89731 |

注意：L1 loss 和 L2 loss 的数值不能直接比较大小。因为它们的定义不同：

```text
L1 是绝对误差。
L2 是平方误差。
```

所以不能说 `0.000719` 一定比 `0.019765` 好很多。比较两组实验时，应该主要看相同验证指标：PSNR、SSIM，以及可视化。

## 5. 最终指标对比

| Loss | step | val PSNR | val SSIM | 观察 |
|---|---:|---:|---:|---|
| L1 | 300 | 31.1442 | 0.90096 | SSIM 略高 |
| L2 / MSE | 300 | 31.7001 | 0.89731 | PSNR 更高 |

差异：

```text
L2 PSNR 比 L1 高约 0.56 dB。
L1 SSIM 比 L2 高约 0.00365。
```

这个结果很适合说明一件事：不同指标可能给出不同倾向。

- 如果只看 PSNR，这次 L2 更好。
- 如果只看 SSIM，这次 L1 略好。
- 如果看可视化，两者差异很小。

## 6. 可视化对比

三联图从左到右仍然是：

```text
noisy 输入 | output 模型输出 | target 干净目标
```

### L1 loss，step 300

![DnCNN L1 step 300](figures/week1d_dncnn_l1_step_0300.png)

### L2 / MSE loss，step 300

![DnCNN L2 step 300](figures/week1d_dncnn_l2_step_0300.png)

这两张图的肉眼差异不大。它们都已经把 noisy 输入变得更接近 target，说明 DnCNN residual 在两种 loss 下都能学会基础去噪。

观察时不要只问“哪张更好”，而要问：

1. output 是否比 noisy 更干净？
2. output 是否接近 target？
3. 纹理有没有被过度抹平？
4. 指标差异是否能在图上明显看出来？

这次的答案是：指标上 L2 的 PSNR 更高，但图像差异不算显著。

## 7. 为什么 L1 和 L2 会不同

L1 和 L2 对误差的惩罚方式不同。

L1：

```text
abs(error)
```

L2：

```text
error^2
```

这意味着大误差在 L2 里会被放大。例如：

```text
error = 0.1
L1 penalty = 0.1
L2 penalty = 0.01

error = 0.5
L1 penalty = 0.5
L2 penalty = 0.25
```

当误差比较大时，L2 会更强烈地惩罚它。因此 L2 常常更倾向于压低整体均方误差，PSNR 往往会比较有优势，因为 PSNR 本身也和 MSE 相关。

但图像主观质量不只由 MSE 决定。有些情况下，L2 可能更容易产生偏平滑的输出；L1 有时会保留更自然的边缘和结构。这个规律不是绝对的，必须结合具体数据、模型和可视化判断。

## 8. 本次结论

本次 controlled experiment 的结论是：

```text
在 toy RGB denoise + DnCNN residual + 300 step 设置下，
L1 和 L2 都能让模型学到有效去噪。
L2/MSE 的 PSNR 更高，L1 的 SSIM 略高。
可视化差异较小，因此不能只凭一个指标判定绝对优劣。
```

这说明你现在开始进入图像恢复实验的第二层能力：

```text
不只是会跑模型，
还要知道训练目标如何影响指标和视觉结果。
```

## 9. 下一步

下一步可以继续做两个小实验：

1. **噪声泛化实验。** 训练时用 sigma 0.03 - 0.12，测试时换更强噪声，看模型是否还能工作。
2. **patch size 对比。** 比较 64 和 128 patch，对速度、显存、PSNR、SSIM 和细节恢复的影响。

暂时仍然不建议直接跳到 SIDD / SID / NAFNet。先把 toy denoise 里的变量实验做扎实，后面进入真实数据时会稳很多。
