# 阶段二学习流程总览

阶段二的目标不是一上来追大模型或真实手机数据，而是先用一个小型 RGB 去噪任务，把深度学习图像恢复的训练闭环跑稳，再逐步接近真实相机数据。

整理后，报告按自然学习顺序分成六周：

| 周次 | 主题 | 你要学会什么 | 报告 |
|---|---|---|---|
| Week 0 | 神经网络训练基础 | 看懂 noisy、clean、model、loss、backward、optimizer | `week0_foundation.md` |
| Week 1 | Toy RGB 去噪闭环 | 跑通 TinyCNN / DnCNN，理解 residual、loss、patch、噪声模型 | `week1_toy_rgb_denoise.md` |
| Week 2 | 真实成对 RGB 数据入口 | 把外部 noisy/clean 图片整理成可训练数据，准备进入 SIDD-style 实验 | `week2_real_paired_rgb.md` |
| Week 3 | 真实 RGB 小规模实验 | 在真实 paired RGB 上比较长训练、loss、patch size 和 UNet baseline | `week3_real_rgb_experiments.md` |
| Week 4 | Loss / Metric / 可视化评估 | 建立 PSNR、SSIM、三联图、error map 和失败案例分析方法 | `week4_loss_metric_visualization.md` |
| Week 5 | NAFNet / 轻量恢复模型复现 | 理解 SimpleGate、SCA、NAFNet-lite，并和 DnCNN/UNet baseline 对比 | `week5_nafnet_reproduction.md` |

## 总路线

```text
Week 0: 看懂训练为什么能让模型变好
  -> Week 1: 用 toy RGB 去噪跑通训练、验证、可视化和对比实验
  -> Week 2: 接入真实 paired RGB 图片，开始从 toy 任务走向真实数据
  -> Week 3: 在真实 paired RGB 上做小规模实验、比较结果并决定下一步
  -> Week 4: 建立 loss / metric / 可视化 / failure case 的评价体系
  -> Week 5: 复现 NAFNet-lite，和 DnCNN / UNet 做轻量模型对比
```

![阶段二整体路线图](figures/stage2_overall_learning_flow.png)

> 图说明：这张图是阶段二的学习地图。阅读时从 Week0 往 Week5 顺着箭头走：先理解训练闭环，再跑通 toy RGB 去噪，然后进入真实 paired RGB、评估体系和 NAFNet-lite 复现。

## 现在学到哪

当前已经完成：

- toy RGB 数据集；
- TinyCNN 最小训练闭环；
- DnCNN residual 去噪；
- direct clean 和 residual 的对比；
- L1 和 L2/MSE loss 的对比；
- patch size 64 和 128 的对比；
- Gaussian noise 到 shot/read noise 的过渡；
- noisy 输入 baseline 测量；
- paired RGB 文件夹数据适配器；
- SIDD-style 小型子集准备脚本。
- Week 3 真实 RGB 实验配置和学习报告。
- Week 4 Loss / Metric / 可视化评估学习指导。
- Week 4 自动评估脚本：metrics 汇总、三联图、error map。
- Week 5 NAFNet-lite 复现代码、配置和 smoke 训练结果。

也就是说，现在已经不是“刚开始学概念”，而是走到：

```text
toy RGB 去噪已经跑通，真实 paired RGB 数据入口已经建立，
DnCNN smoke baseline、NAFNet-lite smoke 训练和 Week4 自动评估已经跑通。
下一步是把同一套流程迁移到真实 sidd_tiny 小子集上，
再做 DnCNN / UNet / NAFNet-lite 的公平对比。
```

## 推荐学习方式

不要按旧文件名找 `week1a/week1b/week1c`。那些已经被整理进 Week 1 统一报告。

按下面顺序读：

1. `week0_foundation.md`
2. `week1_toy_rgb_denoise.md`
3. `week2_real_paired_rgb.md`
4. `week3_real_rgb_experiments.md`
5. `week4_loss_metric_visualization.md`
6. `week5_nafnet_reproduction.md`

每读完一周，只问自己三个问题：

- 我能不能说清楚这周的输入和输出？
- 我能不能跑出这周对应的命令？
- 我能不能解释指标和可视化为什么变成这样？

如果能，就继续下一周；如果不能，就回到对应小节补。
