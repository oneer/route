# Week 0.5：最小训练闭环

## 目标

阶段二第一步不追求真实数据或复杂模型，而是先确认图像恢复训练工程可靠：

```text
Dataset -> DataLoader -> Model -> Loss -> Backward -> Optimizer
  -> Validation -> Checkpoint -> Visualization
```

## 当前实现

- `ToyRGBDenoiseDataset` 生成确定性的 clean / noisy RGB patch。
- `TinyCNN`、`DnCNN`、`UNet` 提供从极简到 Week1 baseline 的模型。
- `train_from_config()` 支持配置驱动训练、验证、checkpoint 和可视化。
- `metrics.csv` 记录每次验证的 loss、PSNR 和 SSIM。
- `vis/step_*.png` 保存 noisy / output / target 三联图。

## 验收标准

1. 训练脚本能从配置文件启动。
2. train loss 应整体下降。
3. validation PSNR 应高于 noisy input 的直觉水平。
4. `last.pth` 和 `best_psnr.pth` 能正常保存。
5. 验证图能看出输出比 noisy 更平滑。

## 本次运行结果

`toy_rgb_denoise_tiny` 已跑通 100 step：

| step | train loss | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 50 | 0.112159 | 17.6089 | 0.73657 |
| 100 | 0.034437 | 26.7024 | 0.84571 |

输出位置：

- `runs/toy_rgb_denoise_tiny/checkpoints/`
- `runs/toy_rgb_denoise_tiny/vis/`
- `runs/toy_rgb_denoise_tiny/metrics.csv`

## 为什么不直接跑 NAFNet

NAFNet、SIDD 和 SID 都会引入更多变量：数据格式、显存、训练时长、官方配置和指标协议。先用 toy denoise 验证闭环，可以把后续问题定位得更清楚：如果大数据训练失败，就更可能是数据或模型问题，而不是训练循环本身。
