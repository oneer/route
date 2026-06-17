# CS231n 学习笔记

这个目录用于记录 CS231n 中和 Stage 2 AI-ISP / 图像恢复直接相关的神经网络基础。

学习目标不是把整门课完整啃完，而是补齐当前项目需要的这条链：

```text
image tensor -> model -> loss -> backward -> optimizer -> validation
```

## 1. 推荐观看顺序

### 必看

| 顺序 | 课程 | 为什么看 | 对应本项目 |
|---:|---|---|---|
| 1 | Lecture 2 线性分类器进行图像分类 | 理解模型是可学习函数，输入图像如何变成分数 / 输出 | `TinyCNN` 也是一个可学习函数 |
| 2 | Lecture 3 正则化与优化 | 理解 loss、gradient descent、learning rate、regularization | 解释为什么 loss 下降、PSNR 上升 |
| 3 | Lecture 4 神经网络与反向传播 | 理解 forward、backward、链式法则 | 对应 `loss.backward()` |
| 4 | Lecture 5 基于 CNN 的图像分类 | 理解卷积核、feature map、channel、padding、stride | 对应 `tiny_cnn.py` 和 `dncnn.py` |
| 5 | Lecture 6 CNN 架构 | 理解为什么堆更多层、为什么结构会影响学习难度 | 为 DnCNN / UNet 打基础 |

### 可选

| 课程 | 什么时候看 | 用法 |
|---|---|---|
| Lecture 1 导论 | 开始前快速看 | 建立大图景，不用记细节 |
| Lecture 8 注意力机制与 Transformer | 后面学 Restormer / Transformer 图像恢复时 | 现在先不急 |
| Lecture 9 目标检测、图像分割与可视化 | 想理解 CNN 可视化时 | 检测和分割部分可浅看 |
| Lecture 12 自监督学习 | 后面学 Noise2Noise / Noise2Void 时 | 当前不是主线 |
| Lecture 13 / 14 生成模型 | 后面碰 GAN / diffusion 时 | 当前不是主线 |

### 先跳过

- Lecture 7 循环神经网络
- Lecture 10 视频理解
- Lecture 11 大规模分布式训练
- Lecture 15 三维视觉
- Lecture 16 视觉与语言
- Lecture 17 机器人学习
- Lecture 18 以人为本的人工智能

这些不是不好，而是和当前 RGB denoise / AI-ISP 入门目标关系不够近。

## 1.5 课程笔记索引

完整 18 讲笔记放在 `notes/`：

| Lecture | 文件 | 当前优先级 |
|---:|---|---|
| 0 | `notes/00_sources_and_reading_map.md` | 先看 |
| 1 | `notes/01_introduction.md` | 可选 |
| 2 | `notes/02_linear_classifiers.md` | 必看 |
| 3 | `notes/03_regularization_optimization.md` | 必看 |
| 4 | `notes/04_neural_networks_backprop.md` | 必看 |
| 5 | `notes/05_cnns_image_classification.md` | 必看 |
| 6 | `notes/06_cnn_architectures.md` | 必看 |
| 7 | `notes/07_recurrent_neural_networks.md` | 先跳过 |
| 8 | `notes/08_attention_transformers.md` | 可选 |
| 9 | `notes/09_detection_segmentation_visualization.md` | 可选 |
| 10 | `notes/10_video_understanding.md` | 先跳过 |
| 11 | `notes/11_large_scale_distributed_training.md` | 先跳过 |
| 12 | `notes/12_self_supervised_learning.md` | 可选 |
| 13 | `notes/13_generative_models_1.md` | 可选 |
| 14 | `notes/14_generative_models_2.md` | 可选 |
| 15 | `notes/15_3d_vision.md` | 先跳过 |
| 16 | `notes/16_vision_language.md` | 先跳过 |
| 17 | `notes/17_robot_learning_world_modeling.md` | 先跳过 |
| 18 | `notes/18_human_centered_ai.md` | 可选 |

## 2. 每讲怎么记笔记

每一讲只回答 5 个问题：

1. 这讲解释了训练链路里的哪一步？
2. 这讲最重要的 3 个概念是什么？
3. 它如何解释当前项目里的 TinyCNN / DnCNN 实验？
4. 有没有一个我能用自己的话复述的例子？
5. 看完后，我要回到项目里观察哪个文件或哪组实验？

不要追求把课件所有公式抄下来。当前目标是建立直觉，能读懂本项目训练代码和报告。

## 3. 和项目文件的对应关系

| CS231n 概念 | 项目文件 | 你要看懂什么 |
|---|---|---|
| Dataset / batch | `ai_isp/data/toy_rgb_dataset.py` | noisy / clean patch 怎么产生 |
| Model / forward | `ai_isp/models/tiny_cnn.py` | noisy 怎么经过卷积变成 output |
| CNN / residual | `ai_isp/models/dncnn.py` | residual=true 时为什么输出 `noisy - noise_pred` |
| Loss / backward / optimizer | `ai_isp/engine/train.py` | loss 怎么驱动参数更新 |
| Validation / metrics | `ai_isp/engine/validate.py` | PSNR / SSIM 怎么评估 |
| Visualization | `ai_isp/utils/visualization.py` | noisy / output / clean 三联图怎么看 |

## 4. 学完后的检查点

看完必看 5 讲后，应该能回答：

- 为什么神经网络可以看作一个可训练函数？
- loss 为什么能告诉模型哪里错了？
- backward 到底在算什么？
- optimizer 为什么能更新参数？
- CNN 为什么适合图像？
- 3x3 卷积、channel、feature map 是什么？
- 为什么 TinyCNN 是入门地基，而 DnCNN / UNet 是进一步的结构设计？
- 为什么 residual learning 适合 denoise？

如果这些能讲清，再继续 Stage 2 的 DnCNN、UNet、SIDD 会顺很多。

## 5. 建议节奏

```text
Day 1: Lecture 2 + 对照 Week 0.6
Day 2: Lecture 3 + 看 TinyCNN 10/50/100 step 指标
Day 3: Lecture 4 + 读 train.py 里的 loss.backward()
Day 4: Lecture 5 + 读 tiny_cnn.py
Day 5: Lecture 6 + 回看 DnCNN residual/direct clean 报告
```

每看完一讲，复制 `lecture_note_template.md`，新建一份自己的笔记，例如：

```text
lecture_02_linear_classifier.md
lecture_03_optimization.md
lecture_04_backprop.md
lecture_05_cnn.md
lecture_06_cnn_architecture.md
```
