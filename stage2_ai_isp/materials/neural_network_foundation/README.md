# 神经网络前置学习路线

这个目录解决一个问题：如果一上来看到 TinyCNN、DnCNN、UNet 就吃力，应该先补哪些基础。

目标不是系统学完整机器学习，而是补齐 AI-ISP 图像恢复最需要的一条窄路：

```text
supervised learning -> neural network training -> CNN image basics -> image restoration
```

## 先学什么

| 顺序 | 主题 | 要能回答的问题 | 对应项目概念 |
|---:|---|---|---|
| 1 | 监督学习 | 输入和答案分别是什么？ | noisy -> clean |
| 2 | 模型和参数 | 为什么说模型是带参数的函数？ | TinyCNN |
| 3 | Loss | 模型错在哪里怎么量化？ | L1 / L2 |
| 4 | Forward / backward | 输出怎么产生，参数怎么知道往哪改？ | train loop |
| 5 | Optimizer | 谁真正修改参数？ | AdamW |
| 6 | Train / validation | 为什么要分训练集和验证集？ | PSNR / SSIM |
| 7 | Tensor / batch / step | 图像如何变成训练数据？ | RGB patch |
| 8 | CNN | 卷积为什么适合图像？ | TinyCNN / DnCNN |
| 9 | Residual learning | 为什么去噪常预测噪声？ | residual denoise |

## 暂时不用学什么

先不要分散到：

- SVM / 决策树 / 随机森林 / 聚类 / PCA；
- RNN / LSTM；
- Transformer 细节；
- GAN / diffusion；
- 大规模分布式训练；
- 目标检测 / 分割。

这些不是没用，而是不能解决你当前最核心的问题：

```text
为什么训练能让一个图像恢复模型变好？
```

## 建议阅读顺序

先读阶段二整理后的报告：

- `reports/stage2_learning_flow.md`
- `reports/week0_foundation.md`
- `reports/week1_toy_rgb_denoise.md`

读完 Week 0 后，要求能复述：

```text
noisy -> model -> output -> loss -> backward -> optimizer
```

然后再看 CS231n 笔记中和当前阶段最相关的几讲：

- `materials/cs231n/notes/02_linear_classifiers.md`
- `materials/cs231n/notes/03_regularization_optimization.md`
- `materials/cs231n/notes/04_neural_networks_backprop.md`
- `materials/cs231n/notes/05_cnns_image_classification.md`
- `materials/cs231n/notes/06_cnn_architectures.md`

## 小练习

跑 TinyCNN 三个 probe：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_10.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_50.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

观察：

- `metrics.csv`
- `vis/step_*.png`

你要看到的是：step 增加后，模型输出逐渐接近 clean。

## 学完检查

如果能回答下面问题，就可以继续 Week 1：

1. noisy 和 clean 分别是什么？
2. patch 为什么是小图块？
3. model 为什么说是函数？
4. 参数是什么？
5. loss 为什么能指导训练？
6. backward 在算什么？
7. optimizer 在改什么？
8. validation 为什么不参与训练？
9. CNN 的卷积核为什么适合图像？
10. residual denoise 为什么比 direct clean 更自然？
