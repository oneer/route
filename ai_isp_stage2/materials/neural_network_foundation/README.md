# 神经网络前置学习路线

这个目录解决一个问题：如果阶段二一上来看到 TinyCNN、DnCNN、UNet 就吃力，应该先补哪些神经网络和机器学习概念。

目标不是系统学习完整机器学习，而是补齐 AI-ISP 图像恢复最需要的一条窄路：

```text
supervised learning -> neural network training -> CNN image basics -> image restoration
```

## 1. 先学什么

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

## 2. 暂时不用学什么

先不要碰太多旁支：

- SVM / 决策树 / 随机森林 / 聚类 / PCA。
- RNN / LSTM。
- Transformer 细节。
- GAN / diffusion。
- 大规模分布式训练。
- 目标检测 / 分割。

这些不是没用，而是不能解决你现在卡住的问题。你当前卡住的是：

```text
为什么训练能让一个图像恢复模型变好？
```

## 3. 建议学习顺序

### 第 0 步：读本项目地基笔记

先读：

- `reports/week0_6_neural_network_foundation.md`

读完只要求能复述：

```text
noisy -> model -> output -> loss -> backward -> optimizer
```

### 第 1 步：看 CS231n 前 5 个重点讲

只看：

```text
Lecture 2 -> Lecture 3 -> Lecture 4 -> Lecture 5 -> Lecture 6
```

配套笔记：

- `materials/cs231n/notes/02_linear_classifiers.md`
- `materials/cs231n/notes/03_regularization_optimization.md`
- `materials/cs231n/notes/04_neural_networks_backprop.md`
- `materials/cs231n/notes/05_cnns_image_classification.md`
- `materials/cs231n/notes/06_cnn_architectures.md`

### 第 2 步：跑 TinyCNN 三个 probe

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_10.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

观察：

- `metrics.csv`
- `vis/step_0010.png`
- `vis/step_0050.png`
- `vis/step_0100.png`

你要看到的是：step 增加后，输出逐渐接近 clean。

### 第 3 步：读 Week 1A / 1B / 1C

- `reports/week1a_image_restoration_intuition.md`
- `reports/week1b_training_loop_tinycnn.md`
- `reports/week1c_dncnn_residual.md`

这三份笔记会用更慢的节奏进入 Week 1。

## 4. 学完前置路线后的检查

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

