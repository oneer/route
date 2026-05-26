# Week 1：RGB 合成噪声 Baseline

如果 DnCNN / UNet / residual 这些词看起来太突然，先按下面顺序读：

1. [Week 1A：图像恢复最小直觉](week1a_image_restoration_intuition.md)
2. [Week 1B：TinyCNN 训练闭环](week1b_training_loop_tinycnn.md)
3. [Week 1C：DnCNN 和 residual denoise](week1c_dncnn_residual.md)

## 目标

用合成 RGB denoise 任务建立图像恢复直觉：

- patch 训练为什么有效；
- DnCNN 为什么常预测 residual noise；
- UNet 的 skip connection 如何帮助恢复细节；
- L1 / L2、PSNR / SSIM 如何评价 denoise 结果。

## 当前 Baseline

| 模型 | 配置 | 作用 |
|---|---|---|
| TinyCNN | `configs/toy_rgb_denoise_tiny.yaml` | Week 0.5 训练闭环 sanity check |
| DnCNN | `configs/toy_rgb_denoise_dncnn.yaml` | 学 residual denoise |
| DnCNN direct | `configs/toy_rgb_denoise_dncnn_direct.yaml` | 对比直接预测 clean 的收敛难度 |
| DnCNN residual long | `configs/toy_rgb_denoise_dncnn_long.yaml` | 观察 residual 训练到 1000 step 后是否继续提升 |
| DnCNN direct long | `configs/toy_rgb_denoise_dncnn_direct_long.yaml` | 观察 direct clean 训练到 1000 step 后能否追上 residual |
| UNet | `configs/toy_rgb_denoise_unet.yaml` | 学 encoder-decoder 和 skip connection |

## 数据退化

当前使用随机 sigma 的 Gaussian noise：

```text
noisy = clamp(clean + N(0, sigma), 0, 1)
sigma ~ Uniform(0.03, 0.12)
```

它适合入门，但不是真实 sensor 噪声。真实噪声还会受到 ISO、曝光、black level、shot noise、read noise、demosaic 和 ISP 后处理影响。

## 已验证结果

本次启动已跑通 TinyCNN、DnCNN residual、DnCNN direct clean prediction 和 UNet：

| 模型 | steps | final train loss | final val PSNR | final val SSIM |
|---|---:|---:|---:|---:|
| TinyCNN | 100 | 0.034434 | 26.70 | 0.8457 |
| DnCNN residual | 300 | 0.020152 | 31.15 | 0.8985 |
| DnCNN direct clean | 300 | 0.037522 | 28.23 | 0.8876 |
| UNet | 300 | 0.058372 | 21.17 | 0.7987 |

在这个 toy 任务上，DnCNN residual 明显更容易收敛。同样 300 step、同样数据规模和噪声范围下，residual 版本比 direct clean prediction 高约 2.92 dB PSNR。这符合 denoise 的直觉：输入已经接近 clean，模型只需要学习噪声残差，而不是从头生成干净图。

### 加长训练：1000 step 对比

为了确认 300 step 的差距不是偶然，又跑了两组 1000 step 实验。两组只改变 `model.residual`，其余设置保持一致：patch size 64、train size 512、val size 32、DnCNN depth 5、features 32、L1 loss、learning rate 0.001。

| 模型 | 配置 | steps | final train loss | final val PSNR | final val SSIM |
|---|---|---:|---:|---:|---:|
| DnCNN residual long | `toy_rgb_denoise_dncnn_long.yaml` | 1000 | 0.017346 | 33.13 | 0.9355 |
| DnCNN direct clean long | `toy_rgb_denoise_dncnn_direct_long.yaml` | 1000 | 0.026696 | 31.23 | 0.9144 |

训练曲线可以这样读：

| step | residual PSNR | direct clean PSNR | 观察 |
|---:|---:|---:|---|
| 100 | 27.89 | 18.23 | direct clean 一开始要先学整体图像生成，起步慢很多 |
| 200 | 30.98 | 26.43 | direct clean 开始追上，但仍落后 |
| 300 | 31.24 | 28.89 | 两者都变好，residual 仍明显领先 |
| 600 | 32.78 | 30.31 | residual 稳定提升，direct clean 波动更明显 |
| 1000 | 33.13 | 31.23 | direct clean 继续进步，但没有追平 residual |

结论：训练更久后，direct clean prediction 不是完全学不会，它也能把 noisy 图变干净。但在这个去噪任务上，residual learning 仍然更容易优化，最终 PSNR 高约 1.90 dB，SSIM 高约 0.0211。

## 训练过程到底在发生什么

一次训练 step 可以理解成下面这条链：

```text
clean patch
  -> 加 Gaussian noise，得到 noisy patch
  -> 模型输入 noisy，输出 denoised
  -> 用 L1 loss 比较 denoised 和 clean
  -> backward 计算每个卷积参数该怎么改
  -> optimizer 更新参数
```

这里的 `clean` 是监督答案，`noisy` 是输入题目，模型的目标是学一个映射：

```text
f(noisy) ≈ clean
```

每隔 `val_every` step 会跑一次验证集。验证集不参与参数更新，只用来检查模型是不是真的学到了可泛化的去噪规则，而不是只记住训练样本。报告里的 PSNR / SSIM 就来自验证集。

## DnCNN 是什么

DnCNN 可以先粗略理解成“很多层 3x3 卷积叠起来的去噪 CNN”。它没有复杂的 encoder-decoder，也没有 skip connection 金字塔，结构很直接：

```text
noisy RGB
  -> Conv + ReLU
  -> Conv + ReLU
  -> Conv + ReLU
  -> Conv + ReLU
  -> Conv
  -> output
```

卷积层的作用是看局部邻域。例如一个像素周围 3x3、5x5、更多层叠加后的更大范围。去噪时，模型要学会判断“这个局部变化是图像纹理，还是随机噪声”。浅层 CNN 已经足够演示这个核心直觉。

本项目里的 DnCNN 有两个模式：

```text
residual = true:
    noise_pred = net(noisy)
    denoised = noisy - noise_pred

residual = false:
    denoised = net(noisy)
```

也就是说，`residual=true` 不是让网络直接画一张干净图，而是让网络预测“应该从 noisy 里减掉多少噪声”。这就是 residual denoise。

## Residual 和 Direct Clean 的区别

Direct clean prediction 学的是：

```text
noisy -> clean
```

Residual learning 学的是：

```text
noisy -> noise
clean = noisy - noise
```

为什么 residual 更适合 denoise？因为去噪任务里，`noisy` 本来就和 `clean` 很接近。大多数像素不需要大幅重建，只需要去掉一小部分随机扰动。让模型预测这部分“差值”通常比让它重新生成整张 clean 图更简单。

可以用一句话记：

```text
direct clean：让模型回答“干净图应该长什么样”
residual：让模型回答“输入里哪些东西像噪声，应该减掉”
```

这也是为什么 1000 step 后 direct clean 能进步，但 residual 仍然领先：direct clean 要同时学图像内容和去噪，residual 主要学噪声残差。

## 小实验清单

1. L1 vs L2，对比输出平滑程度和 PSNR。
2. patch size 64 / 128，对比速度、显存和细节。
3. sigma 训练范围和测试范围错开，观察泛化下降。

## 面试复述要点

RGB 合成噪声 baseline 的价值不在于接近真实手机噪声，而在于建立可控训练闭环。它能先验证模型、loss、metric 和可视化，再进入 SIDD 真实噪声和 SID RAW low-light。
