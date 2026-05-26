# AI-ISP Stage 2

阶段二聚焦 AI-ISP 与图像恢复。第一步不是直接上真实手机数据或大模型，而是先用一个小型 RGB 去噪任务，把深度学习训练闭环跑稳。

## 当前目标

最小任务：

```text
clean RGB patch -> synthetic noise -> tiny CNN / DnCNN / UNet -> denoised RGB
```

这一步用于验证工程链路：

- 确定性 toy dataset
- train / validation split
- checkpoint 保存
- PSNR / SSIM 验证
- noisy / output / target 可视化
- config-driven experiment settings

## 环境

```bash
pip install -r requirements.txt
```

本地启动验证使用：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

## 已跑通的 baseline

三组 toy RGB denoise baseline 已经跑通：

| 模型 | steps | final train loss | final val PSNR | final val SSIM |
|---|---:|---:|---:|---:|
| TinyCNN | 100 | 0.034434 | 26.70 | 0.8457 |
| DnCNN residual | 300 | 0.019765 | 31.14 | 0.9010 |
| UNet | 300 | 0.058372 | 21.17 | 0.7987 |

输出位于：

- `ai_isp_stage2/runs/toy_rgb_denoise_tiny/`
- `ai_isp_stage2/runs/toy_rgb_denoise_dncnn/`
- `ai_isp_stage2/runs/toy_rgb_denoise_unet/`

`runs/` 已被 git ignore，因为它包含 checkpoint、日志和可视化结果。

## 可用训练命令

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_unet.yaml
```

## 项目结构

```text
ai_isp_stage2/
├── configs/
├── ai_isp/
│   ├── data/
│   ├── engine/
│   ├── metrics/
│   ├── models/
│   └── utils/
├── scripts/
├── reports/
└── runs/              # ignored
```

## 下一步

1. 做 DnCNN residual vs direct clean prediction。
2. 做 L1 / L2 loss 对比，观察平滑程度和 PSNR/SSIM。
3. 做 patch size 64 / 128 对比，观察速度、显存和细节。
4. 把 synthetic Gaussian noise 推进到更接近 sensor 的 noise model。
5. 再进入 SIDD RGB denoise 或 SID RAW low-light。
