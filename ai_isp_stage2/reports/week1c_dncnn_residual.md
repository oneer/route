# Week 1C：DnCNN 和 residual denoise

Week 1C 才开始讲 DnCNN。

先记住一句话：

```text
DnCNN 不是神秘模型，它只是比 TinyCNN 更深一点的卷积去噪网络。
```

## 1. 为什么 TinyCNN 不够

TinyCNN 只有 3 层卷积，适合看懂训练闭环，但表达能力有限。

去噪时，模型需要判断：

- 某个局部变化是真实纹理还是噪声？
- 边缘要保留还是平滑？
- 彩色噪声和真实颜色怎么区分？

更深的网络能看更大范围，也能组合更复杂的局部特征。

## 2. DnCNN 是什么

DnCNN 可以先理解成：

```text
更多层 Conv + ReLU 叠起来的去噪 CNN
```

本项目的小型 DnCNN：

```text
Conv -> ReLU -> Conv -> ReLU -> Conv -> ReLU -> Conv -> ReLU -> Conv
```

它仍然是：

```text
输入图像 -> 可学习函数 -> 输出图像
```

## 3. direct clean 是什么

Direct clean prediction 直接预测干净图：

```text
denoised = net(noisy)
```

模型要回答：

```text
这张干净图应该长什么样？
```

## 4. residual 是什么

Residual denoise 不直接预测 clean，而是预测噪声：

```text
noise_pred = net(noisy)
denoised = noisy - noise_pred
```

模型要回答：

```text
输入里哪些东西像噪声，应该减掉？
```

## 5. 为什么 residual 更自然

去噪任务里，noisy 本来就接近 clean：

```text
noisy = clean + noise
```

所以模型没必要重新生成整张 clean 图，只要学会估计 noise。

这就像传统 ISP 里做校正：

```text
raw_corrected = raw - black_level
```

不是重造 raw，而是减掉不该有的偏移。

## 6. 实验结果怎么读

300 step：

| 模型 | val PSNR | val SSIM |
|---|---:|---:|
| DnCNN residual | 31.15 | 0.8985 |
| DnCNN direct clean | 28.23 | 0.8876 |

1000 step：

| 模型 | val PSNR | val SSIM |
|---|---:|---:|
| DnCNN residual long | 33.13 | 0.9355 |
| DnCNN direct clean long | 31.23 | 0.9144 |

Direct clean 训练久了也能变好，但 residual 仍然更容易优化。

## 7. 你应该跑的命令

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_direct.yaml
```

看：

```text
ai_isp_stage2/runs/toy_rgb_denoise_dncnn/metrics.csv
ai_isp_stage2/runs/toy_rgb_denoise_dncnn_direct/metrics.csv
```

## 8. 今天只需要掌握

1. DnCNN 是更深的 CNN。
2. direct clean 是直接预测 clean。
3. residual 是预测 noise，再从 noisy 里减掉。
4. 去噪里 residual 更自然，因为 noisy 本来接近 clean。
5. 模型名不重要，重要的是输入、输出、loss 和训练目标。

