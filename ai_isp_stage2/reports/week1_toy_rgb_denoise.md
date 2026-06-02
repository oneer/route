# Week 1：Toy RGB 去噪完整学习流程

Week 1 的目标是跑通一个完整但小型的 RGB 去噪任务。

它原来被拆成很多 `week1a/week1b/...` 小报告，现在统一整理成一条学习路线。

## 1. 本周目标

最小任务：

```text
clean RGB patch -> synthetic noise -> model -> denoised RGB
```

这个任务用来验证工程链路：

- toy dataset；
- train / validation split；
- checkpoint 保存；
- PSNR / SSIM 验证；
- noisy / output / clean 三联图；
- config-driven 实验设置；
- 模型、loss、patch size、噪声模型的控制实验。

## 2. 第一步：建立图像恢复直觉

图像去噪不是“让图片变好看”这么模糊，而是：

```text
输入：noisy patch
答案：clean patch
模型输出：output patch
目标：让 output 接近 clean
```

三联图通常按这个顺序看：

```text
noisy | output | clean
```

观察时不要只看 PSNR，也要看：

- output 是否比 noisy 干净；
- output 是否接近 clean；
- 纹理是否被过度抹平；
- 边缘和颜色是否异常；
- 指标差异是否能在图上看出来。

## 3. 第二步：用 TinyCNN 跑通训练闭环

TinyCNN 不是为了追求效果，而是为了确认训练真的能工作。

建议先跑三个 probe：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_10.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

已观察到的结果：

| steps | train loss | val PSNR | val SSIM | 解读 |
|---:|---:|---:|---:|---|
| 10 | 0.170468 | 13.49 | 0.6601 | 刚开始学 |
| 50 | 0.083647 | 18.19 | 0.7377 | 学到一点 |
| 100 | 0.034625 | 26.73 | 0.8526 | 明显变好 |

这一段要理解的是：

```text
step 变多 -> 参数被更多次修正 -> output 有机会更接近 clean
```

## 4. 第三步：换成 DnCNN residual

TinyCNN 适合教学，但表达能力有限。接下来使用更深一点的 DnCNN。

直接预测 clean：

```text
denoised = net(noisy)
```

Residual 去噪：

```text
noise_pred = net(noisy)
denoised = noisy - noise_pred
```

为什么 residual 更自然？

因为 noisy 本来就接近 clean：

```text
noisy = clean + noise
```

模型不用重新生成整张 clean，只要学会哪些东西像噪声，然后减掉。

已观察到的结果：

| 模型 | steps | final val PSNR | final val SSIM |
|---|---:|---:|---:|
| DnCNN residual | 300 | 31.15 | 0.8985 |
| DnCNN direct clean | 300 | 28.23 | 0.8876 |
| DnCNN residual long | 1000 | 33.13 | 0.9355 |
| DnCNN direct clean long | 1000 | 31.23 | 0.9144 |

结论：direct clean 训练久了也能变好，但 residual 在去噪任务里更容易优化。

## 5. 第四步：比较 L1 和 L2/MSE loss

同一个 DnCNN residual，只改 loss。

| Loss | final train loss | final val PSNR | final val SSIM |
|---|---:|---:|---:|
| L1 | 0.020152 | 31.1470 | 0.89850 |
| L2 / MSE | 0.000739 | 31.5874 | 0.89452 |

怎么读：

- L2/MSE 更贴近 PSNR，所以 PSNR 略高；
- L1 的 SSIM 略高，可能稍微更保结构；
- 两者差距不大，不要过度解读；
- 不同 loss 数值不能直接比较大小。

实用结论：

- 追 PSNR，用 L2/MSE；
- 检查结构和视觉平滑程度，保留 L1 对照；
- 进入真实数据前，不要只凭 toy 结果决定最终 loss。

## 6. 第五步：比较 patch size 64 和 128

Patch 更大，模型看到的上下文更多；但像素更多，训练更慢。

| Patch size | wall time | final train loss | final val PSNR | final val SSIM |
|---:|---:|---:|---:|---:|
| 64 | 15.86s | 0.000739 | 31.5874 | 0.89452 |
| 128 | 51.40s | 0.000499 | 33.4745 | 0.93176 |

结论：

- patch 64 适合快速检查；
- patch 128 在 toy 实验里指标更好；
- 进入真实数据前要考虑显存和时间。

## 7. 第六步：从 Gaussian noise 到 sensor-like noise

最开始的噪声是：

```text
noisy = clean + gaussian_noise
```

这适合做 sanity check，但真实传感器噪声更复杂。于是加入一个简化的 shot/read noise：

```text
noisy = clean + shot_noise(clean) + read_noise
```

含义：

- shot noise：和信号强度有关；
- read noise：更像固定电子噪声底。

工程结果：

```text
训练代码可以通过 config 切换噪声模型。
```

## 8. 第七步：先测 noisy 输入 baseline

比较两个噪声模型之前，先测输入本身有多难：

```text
input PSNR = PSNR(noisy, clean)
input SSIM = SSIM(noisy, clean)
```

命令：

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

校准结果：

| 配置 | 噪声 | Input PSNR | Input SSIM |
|---|---|---:|---:|
| `toy_rgb_denoise_dncnn_l2_loss.yaml` | Gaussian | 24.2068 | 0.46247 |
| `toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml` | 校准后 shot/read | 24.2036 | 0.45582 |

这一步的核心学习点：

```text
不要把“输入更干净”误读成“模型更好”。
```

## 9. 第八步：接入成对 RGB 图片文件夹

Toy 数据是在代码里生成的：

```text
clean patch -> synthetic noise -> noisy patch
```

真实 paired RGB 数据是文件：

```text
noisy image file + matching clean image file -> crop pair -> model
```

所以新增了 `PairedImageDenoiseDataset`，支持这种结构：

```text
clean_dir/
  pair_001.png
  pair_002.png

noisy_dir/
  pair_001.png
  pair_002.png
```

配置写法：

```yaml
data:
  dataset: paired_image
```

本地 paired RGB smoke 训练结果：

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 40 | 0.003541 | 24.6943 | 0.40882 |
| 80 | 0.001015 | 30.2105 | 0.73756 |
| 120 | 0.000558 | 32.9381 | 0.89218 |

这一步的重点不是刷指标，而是确认：

```text
只换 dataset，模型、loss、训练循环、checkpoint、metrics、可视化都不用重写。
```

## 10. 本周总结

Week 1 完成后，你应该能说清楚：

1. toy RGB denoise 的输入、答案和输出是什么；
2. TinyCNN 为什么适合先验证训练闭环；
3. DnCNN residual 为什么比 direct clean 更自然；
4. L1 和 L2/MSE loss 的差异；
5. patch size 为什么影响效果和速度；
6. Gaussian noise 和 shot/read noise 的区别；
7. 为什么比较模型前要先测 noisy 输入 baseline；
8. paired image dataset 为什么是进入真实数据前的关键接口。

## 11. Week 1 到 Week 2 的过渡

现在 toy 任务已经足够稳定。下一步不是继续堆更多 toy 实验，而是：

```text
准备真实 noisy/clean 小子集 -> 测输入 baseline -> 小步训练 -> 看模型是否真的改善真实图片
```

## 12. 实验命令总表

这一节把 Week 1 用到的命令集中放在一起。学习时不需要一次全跑，可以按小节逐步跑。

### 12.1 TinyCNN probe

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_10.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

目的：观察 step 增加后，模型是否从“不会”逐渐变得“会一点”。

### 12.2 TinyCNN 完整 baseline

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

目的：得到一个最小模型基线。

### 12.3 DnCNN residual 和 direct clean

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_direct.yaml
```

目的：比较 residual denoise 和直接预测 clean。

### 12.4 长训练对比

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_long.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_direct_long.yaml
```

目的：观察 direct clean 训练更久后是否追上 residual。

### 12.5 L1 / L2 loss

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l1.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2.yaml
```

目的：只改 loss，观察 PSNR、SSIM 和可视化的差异。

### 12.6 Patch size

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_patch128.yaml
```

目的：比较 patch 64 和 patch 128 的速度与质量。

### 12.7 Sensor-like noise

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_shot_read.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

目的：从固定 Gaussian noise 走向更接近传感器的 shot/read noise。

### 12.8 输入 noisy baseline

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

目的：训练前先知道 noisy 输入本身的 PSNR / SSIM。

### 12.9 Paired RGB smoke

```bash
python ai_isp_stage2/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_smoke_dncnn_l2.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_smoke_dncnn_l2.yaml
```

目的：验证成对图片文件夹数据链路可训练。

## 13. 结果总表

### 13.1 模型 baseline

| 模型 | steps | final train loss | final val PSNR | final val SSIM | 结论 |
|---|---:|---:|---:|---:|---|
| TinyCNN | 100 | 0.034434 | 26.70 | 0.8457 | 能跑通闭环，但能力有限 |
| DnCNN residual | 300 | 0.020152 | 31.15 | 0.8985 | 当前 toy baseline 更稳 |
| DnCNN direct clean | 300 | 0.037522 | 28.23 | 0.8876 | 直接预测 clean 更难 |
| UNet | 300 | 0.058372 | 21.17 | 0.7987 | 这个小配置下不适合作为当前 baseline |

### 13.2 DnCNN 长训练

| 模型 | steps | final val PSNR | final val SSIM | 结论 |
|---|---:|---:|---:|---|
| DnCNN residual long | 1000 | 33.13 | 0.9355 | residual 继续提升 |
| DnCNN direct clean long | 1000 | 31.23 | 0.9144 | direct clean 也变好，但仍落后 |

### 13.3 L1 / L2

| Loss | final train loss | final val PSNR | final val SSIM | 解读 |
|---|---:|---:|---:|---|
| L1 | 0.020152 | 31.1470 | 0.89850 | SSIM 略高 |
| L2 / MSE | 0.000739 | 31.5874 | 0.89452 | PSNR 略高 |

### 13.4 Patch size

| Patch size | wall time | final train loss | final val PSNR | final val SSIM | 解读 |
|---:|---:|---:|---:|---:|---|
| 64 | 15.86s | 0.000739 | 31.5874 | 0.89452 | 快速实验合适 |
| 128 | 51.40s | 0.000499 | 33.4745 | 0.93176 | 指标更好，但慢很多 |

### 13.5 噪声模型校准

| 配置 | 噪声 | Input PSNR | Input SSIM |
|---|---|---:|---:|
| `toy_rgb_denoise_dncnn_l2_loss.yaml` | Gaussian | 24.2068 | 0.46247 |
| `toy_rgb_denoise_dncnn_l2_shot_read.yaml` | 原始 shot/read | 25.9799 | 0.53497 |
| `toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml` | 校准后 shot/read | 24.2036 | 0.45582 |

| 噪声 | final val PSNR | final val SSIM | 解读 |
|---|---:|---:|---|
| Gaussian | 31.5874 | 0.89452 | 基准 |
| 校准后 shot/read | 32.1824 | 0.91118 | 输入难度接近后仍略好 |

### 13.6 Paired RGB smoke

输入 baseline：

| Dataset | Input PSNR | Input SSIM |
|---|---:|---:|
| paired RGB smoke | 22.1273 | 0.28203 |

训练结果：

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 40 | 0.003541 | 24.6943 | 0.40882 |
| 80 | 0.001015 | 30.2105 | 0.73756 |
| 120 | 0.000558 | 32.9381 | 0.89218 |

## 14. 每个实验到底在学什么

### 14.1 TinyCNN 学的是训练闭环

不要把 TinyCNN 看成真正要用的模型。它的价值是简单：

```text
数据能加载吗？
loss 能下降吗？
validation 能跑吗？
三联图能保存吗？
```

如果 TinyCNN 都跑不通，就不应该急着上 DnCNN / UNet。

### 14.2 DnCNN residual 学的是任务表达

去噪任务里，noisy 和 clean 差的是 noise。

所以 residual 写法更贴近问题：

```text
模型不必重新生成 clean；
模型只需要估计 noise；
denoised = noisy - noise_pred。
```

### 14.3 L1 / L2 学的是目标函数

模型只会追 loss。你换 loss，就是在换“你要求模型追什么”。

L2/MSE 和 PSNR 更一致；L1 有时视觉结构更自然。没有哪个永远正确，要结合数据和目标看。

### 14.4 Patch size 学的是上下文和代价

更大的 patch 给模型更多空间上下文，也给验证更多图像结构；但计算成本明显增加。

这对应真实训练中的常见取舍：

```text
更大 patch / 更大 batch / 更深模型
  -> 可能更好
  -> 也更慢、更吃显存
```

### 14.5 噪声模型学的是实验公平性

如果 Gaussian 输入本来更脏，shot/read 输入本来更干净，那么直接比较训练后指标是不公平的。

所以要先测：

```text
PSNR(noisy, clean)
SSIM(noisy, clean)
```

这一步训练前就能做。

### 14.6 Paired RGB dataset 学的是工程边界

进入真实数据时，最容易出错的是数据格式：

- noisy 和 clean 文件是否配对；
- 尺寸是否一致；
- crop 是否对齐；
- train / val 是否混在一起。

`PairedImageDenoiseDataset` 把这些问题集中到 dataset 层，训练主循环就不用重写。

## 15. 看三联图时的检查清单

每次打开 `vis/step_*.png`，都按这个顺序看：

1. noisy 的噪声强度是否合理；
2. output 是否比 noisy 更干净；
3. output 是否接近 clean；
4. 边缘有没有被抹掉；
5. 纹理有没有变成假纹理；
6. 颜色有没有偏；
7. 指标提升是否能在图上看出来。

如果 PSNR 提升但图像看起来更差，不要盲信指标。

## 16. Week 1 的通过标准

学完 Week 1 后，你应该能独立解释：

1. 为什么先跑 TinyCNN；
2. 为什么 DnCNN residual 更适合去噪；
3. 为什么 direct clean 更难；
4. L1 和 L2/MSE 分别偏向什么；
5. patch 64 和 128 的取舍；
6. 为什么 shot/read noise 更接近 sensor；
7. 为什么要先测 noisy 输入 baseline；
8. paired RGB 文件夹数据为什么是通往真实数据的关键一步；
9. `metrics.csv`、checkpoint、三联图分别有什么用；
10. 为什么当前还不急着上 NAFNet / SID / RAW low-light。

如果这些能讲清楚，Week 1 就不是“跑了一堆实验”，而是完成了从训练基础到真实数据入口前的完整准备。
