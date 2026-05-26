# Week 1：RGB 合成噪声 Baseline

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
| UNet | `configs/toy_rgb_denoise_unet.yaml` | 学 encoder-decoder 和 skip connection |

## 数据退化

当前使用随机 sigma 的 Gaussian noise：

```text
noisy = clamp(clean + N(0, sigma), 0, 1)
sigma ~ Uniform(0.03, 0.12)
```

它适合入门，但不是真实 sensor 噪声。真实噪声还会受到 ISO、曝光、black level、shot noise、read noise、demosaic 和 ISP 后处理影响。

## 已验证结果

本次启动已跑通 TinyCNN、DnCNN residual 和 UNet：

| 模型 | steps | final train loss | final val PSNR | final val SSIM |
|---|---:|---:|---:|---:|
| TinyCNN | 100 | 0.034434 | 26.70 | 0.8457 |
| DnCNN residual | 300 | 0.019765 | 31.14 | 0.9010 |
| UNet | 300 | 0.058372 | 21.17 | 0.7987 |

在这个 toy 任务上，DnCNN residual 明显更容易收敛。这符合 denoise 的直觉：输入已经接近 clean，模型只需要学习噪声残差，而不是从头生成干净图。

## 小实验清单

1. DnCNN residual vs direct clean prediction。
2. L1 vs L2，对比输出平滑程度和 PSNR。
3. patch size 64 / 128，对比速度、显存和细节。
4. sigma 训练范围和测试范围错开，观察泛化下降。

## 面试复述要点

RGB 合成噪声 baseline 的价值不在于接近真实手机噪声，而在于建立可控训练闭环。它能先验证模型、loss、metric 和可视化，再进入 SIDD 真实噪声和 SID RAW low-light。
