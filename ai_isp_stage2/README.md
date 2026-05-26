# AI-ISP Stage 2

阶段二聚焦 AI-ISP 与图像恢复。第一步不是直接上真实手机数据或大模型，而是先用一个小型 RGB 去噪任务，把深度学习训练闭环跑稳。

## 前置学习路线

如果一上来看到 TinyCNN、DnCNN、UNet 就吃力，建议先补这条窄路：

```text
supervised learning -> neural network training -> CNN image basics -> image restoration
```

目标不是系统学习完整机器学习，而是补齐 AI-ISP 图像恢复最需要的基础。

### 先学什么

| 顺序 | 主题 | 你要能回答的问题 | 对应项目 |
|---:|---|---|---|
| 1 | 监督学习 | 输入、答案、模型分别是什么？ | noisy -> clean |
| 2 | 模型和参数 | 为什么说模型是带参数的函数？ | `TinyCNN` |
| 3 | Loss | 模型错在哪里怎么量化？ | L1 loss |
| 4 | Forward / backward | 输出怎么产生，参数怎么更新？ | `train.py` |
| 5 | Optimizer | 谁真正修改参数？ | AdamW |
| 6 | Train / validation | 为什么要分训练集和验证集？ | PSNR / SSIM |
| 7 | Tensor / batch / step | 图像如何变成训练数据？ | 64x64 RGB patch |
| 8 | CNN | 卷积为什么适合图像？ | `tiny_cnn.py` |
| 9 | Residual learning | 为什么去噪常预测噪声？ | `dncnn.py` |

术语速查见 `materials/neural_network_foundation/glossary.md`。

### 暂时不用学

先不要碰：SVM / 决策树 / 随机森林 / 聚类 / PCA、RNN / LSTM、Transformer 细节、GAN / diffusion、大规模分布式训练、目标检测 / 分割。

这些不是没用，而是不能解决你当前卡住的问题：

```text
为什么训练能让一个图像恢复模型变好？
```

### 建议学习顺序

**第 0 步：读地基笔记**

- `materials/neural_network_foundation/README.md` — 前置学习路线和检查点
- `materials/neural_network_foundation/glossary.md` — 术语速查表
- `reports/week0_6_neural_network_foundation.md` — 神经网络图像恢复基础

读完只要求能复述：

```text
noisy -> model -> output -> loss -> backward -> optimizer
```

**第 1 步：看 CS231n 前 5 个重点讲**

只看 Lecture 2 → 3 → 4 → 5 → 6。配套笔记在 `materials/cs231n/notes/`，目录和每讲的优先级见 `materials/cs231n/README.md`。

**第 2 步：跑 TinyCNN 三个 probe**

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_10.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

观察 `metrics.csv` 和 `vis/step_*.png`，确认 step 增加后输出逐渐接近 clean。

**第 3 步：读 Week 1A / 1B / 1C**

- `reports/week1a_image_restoration_intuition.md` — noisy / clean / output / patch 直觉
- `reports/week1b_training_loop_tinycnn.md` — TinyCNN 训练闭环
- `reports/week1c_dncnn_residual.md` — DnCNN 和 residual denoise

这三份笔记用更慢的节奏进入 Week 1，把训练闭环的每个零件讲清楚。

### 学完前置路线后的检查

如果你能回答下面 10 个问题，就可以继续正式 Week 1：

1. noisy 和 clean 分别是什么？
2. patch 为什么是 64x64 小图？
3. model 为什么说是函数？
4. 参数是什么？
5. loss 为什么能指导训练？
6. backward 在算什么？
7. optimizer 在改什么？
8. validation 为什么不能参与训练？
9. CNN 的卷积核为什么适合图像？
10. residual denoise 为什么比 direct clean 更自然？

如果其中一半以上说不清，就先别碰 SIDD / SID / NAFNet。

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

## 已跑通的 baseline

四组 toy RGB denoise baseline 已经跑通：

| 模型 | steps | final train loss | final val PSNR | final val SSIM |
|---:|---:|---:|---:|---:|
| TinyCNN | 100 | 0.034434 | 26.70 | 0.8457 |
| DnCNN residual | 300 | 0.020152 | 31.15 | 0.8985 |
| DnCNN direct clean | 300 | 0.037522 | 28.23 | 0.8876 |
| UNet | 300 | 0.058372 | 21.17 | 0.7987 |

输出位于 `ai_isp_stage2/runs/` 下对应子目录。`runs/` 已被 git ignore。

## 可用训练命令

**TinyCNN probe（推荐先跑，理解训练过程）：**

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_10.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

**TinyCNN 完整训练：**

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

**DnCNN：**

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_direct.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_long.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_direct_long.yaml
```

**UNet：**

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_unet.yaml
```

## 项目结构

```text
ai_isp_stage2/
├── configs/
├── materials/
│   ├── cs231n/
│   └── neural_network_foundation/
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

1. 做 L1 / L2 loss 对比，观察平滑程度和 PSNR/SSIM。
2. 做 patch size 64 / 128 对比，观察速度、显存和细节。
3. 把 synthetic Gaussian noise 推进到更接近 sensor 的 noise model。
4. 再进入 SIDD RGB denoise 或 SID RAW low-light。
