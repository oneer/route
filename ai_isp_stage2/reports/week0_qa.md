# Week 0.5 问答题：最小训练闭环

这份问答用于复习 Week 0.5。它不是背诵题，而是帮助你把“概念、训练过程、指标、可视化、实验边界”连成一条完整逻辑。

建议使用方法：

1. 先自己口头回答问题。
2. 再看参考答案。
3. 如果答案里有一句话你说不出来，就回到 `week0_training_loop.md` 对应部分重读。

## 一、阶段二和图像恢复

### Q1：阶段二和阶段一最大的区别是什么？

**参考答案：**

阶段一是传统 Soft-ISP，核心是手写规则和模块。比如 BLC 扣黑电平、DPC 修坏点、Demosaic 做插值、AWB 调白平衡、CCM 做颜色校正。这些模块的逻辑主要由人设计，学习重点是理解 RAW 到 sRGB 的数据流，以及每个模块的输入、输出、假设和失败场景。

阶段二是 AI-ISP / 图像恢复，核心是让模型从数据中学习映射关系。它不再只依赖人手写每条规则，而是给模型大量输入和目标，让模型学会：

```text
有问题的图像 -> 更接近目标的图像
```

例如，在去噪任务中，输入是 noisy image，目标是 clean image。模型通过训练自动调整参数，让输出越来越接近 clean。

所以两者的关键区别是：

```text
阶段一：人设计规则，模块按固定逻辑处理图像。
阶段二：模型从样本中学习，参数由训练过程自动更新。
```

但是阶段二不是抛弃阶段一。Stage1 的 RAW、噪声、色彩、tone、IQA 知识仍然重要，因为 AI-ISP 最终处理的还是图像退化、颜色、亮度和主观质量问题。

### Q2：什么是 image restoration？它和“生成图像”有什么不同？

**参考答案：**

Image restoration 叫图像恢复，目标是修复输入图像里的退化，同时尽量保留原始内容。常见退化包括噪声、模糊、低光、压缩损伤、分辨率不足、Bayer 马赛克等。

典型任务包括：

| 任务 | 输入 | 目标 |
|---|---|---|
| 去噪 | 有噪声图像 | 干净图像 |
| 去模糊 | 模糊图像 | 清晰图像 |
| 超分 | 低分辨率图像 | 高分辨率图像 |
| 低光增强 | 暗且噪声大的图像 | 明亮干净图像 |
| Demosaic | Bayer RAW | RGB 图像 |

它和生成图像的区别是：图像恢复通常有明确输入，输出应该保留输入内容，只修复问题；生成图像可以从文本或随机噪声生成新内容，创造性更强，但不一定保留某张输入图的真实结构。

可以这样记：

```text
图像恢复：修图，重点是保真。
图像生成：造图，重点是生成。
```

AI-ISP 更偏图像恢复，因为相机拍到的内容是真实场景，模型要做的是还原和增强，而不是凭空创作。

### Q3：为什么 Week 0.5 先学 RGB 合成去噪，而不是直接学 RAW low-light 或 SIDD？

**参考答案：**

因为 Week 0.5 的目标不是追求真实任务效果，而是先跑通最小训练闭环。RGB 合成去噪足够简单、可控、可复现，适合学习训练流程。

RGB 合成去噪的输入输出都很直观：

```text
clean RGB patch -> 加高斯噪声 -> noisy patch
noisy patch -> 模型 -> output
output 和 clean 比较
```

它的好处是：

- 不需要下载大数据集。
- clean / noisy 天然对齐。
- 噪声强度由配置控制。
- 几分钟内能看到 loss 下降。
- 出错时容易定位是环境、代码、模型还是指标问题。

如果一开始直接上 SIDD 或 SID，会多出很多变量：真实噪声分布、数据格式、RAW 解码、曝光比例、显存、训练时间、官方评估协议。初学者会很难判断失败原因。

所以 Week 0.5 是打地基：

```text
先学会怎么跑实验、怎么看结果、怎么判断模型有没有学起来。
再进入真实数据和复杂模型。
```

## 二、数据和任务定义

### Q4：clean、noisy、output、target 分别是什么意思？

**参考答案：**

这四个词是 Week 0.5 最重要的四个对象。

| 名词 | 含义 | 在去噪任务里的角色 |
|---|---|---|
| clean | 干净图像 | 模型想接近的答案 |
| noisy | 加噪后的图像 | 模型实际看到的输入 |
| output | 模型输出 | 模型根据 noisy 预测出来的结果 |
| target | 训练目标 | 通常就是 clean |

训练时发生的是：

```text
noisy -> model -> output
output 与 target/clean 计算 loss
```

模型不会直接看到 target 作为输入。target 只在计算 loss 时使用，用来告诉模型“你输出得离答案还有多远”。

可以用学生做题类比：

```text
noisy = 题目
output = 学生答案
target/clean = 标准答案
loss = 扣了多少分
```

训练就是不断做题、看扣分、调整解题方式。

### Q5：什么是 paired data？为什么 toy denoise 是 paired data？

**参考答案：**

Paired data 指输入和目标一一对应的数据。对于每个 noisy 输入，都有一个明确的 clean target。

Week 0.5 中，noisy 是从 clean 人为加噪得到的：

```text
clean -> add Gaussian noise -> noisy
```

所以 noisy 和 clean 天然对齐。每一个 noisy patch 都知道它原来的 clean patch 是什么。这就是 paired data。

Paired data 的好处是训练目标非常明确：

```text
模型输出 output 应该尽量接近 clean。
```

如果没有 paired target，训练会复杂很多，可能需要自监督、无监督、噪声建模或其他约束。Week 0.5 不碰这些复杂问题，先用 paired toy data 学清楚 supervised training。

### Q6：什么是 patch？为什么不直接用整张图训练？

**参考答案：**

Patch 是从图像中切出的小块，例如 64x64 RGB 小图。Week 0.5 使用的是 64x64 patch。

不用整张图训练，主要有几个原因：

1. **省显存。** 整张图可能很大，训练时还要保存中间激活和梯度，显存压力更高。
2. **样本更多。** 一张图可以切出很多 patch，增加训练样本数量。
3. **局部规律足够有用。** 去噪、纹理恢复、边缘处理很多时候可以从局部区域学到。
4. **训练更快。** 入门阶段重点是验证流程，小 patch 能快速看到 loss 变化。

但 patch 也有局限：它看到的上下文有限。如果任务需要大范围语义或全局亮度关系，只靠小 patch 可能不够。所以 patch 是入门和许多低层视觉任务的常用训练方式，但不是所有任务的完整答案。

## 三、训练闭环

### Q7：Week 0.5 的最小训练闭环包括哪些步骤？

**参考答案：**

最小训练闭环是：

```text
Dataset -> DataLoader -> Model -> Loss -> Backward -> Optimizer
  -> Validation -> Checkpoint -> Visualization
```

逐步解释：

| 步骤 | 作用 |
|---|---|
| Dataset | 生成或读取 clean/noisy 数据 |
| DataLoader | 按 batch 取数据 |
| Model | 输入 noisy，输出 output |
| Loss | 比较 output 和 clean 的差距 |
| Backward | 计算参数该怎么改 |
| Optimizer | 更新模型参数 |
| Validation | 在验证集上看模型有没有变好 |
| Checkpoint | 保存模型权重 |
| Visualization | 保存 noisy/output/target 对比图 |

这条链路的意义是：训练不是只跑模型，而是一个完整实验系统。模型只是其中一块。没有数据、loss、验证、保存和可视化，就不能形成可复现的实验。

### Q8：为什么要用 config 启动实验？

**参考答案：**

Config 是实验说明书。它把实验设置从代码里分离出来，让你不用改 Python 代码就能切换实验。

例如 `toy_rgb_denoise_tiny.yaml` 里定义：

```yaml
experiment:
  name: toy_rgb_denoise_tiny
  output_dir: runs/toy_rgb_denoise_tiny

data:
  patch_size: 64
  noise:
    sigma_min: 0.03
    sigma_max: 0.12

model:
  name: tiny_cnn

train:
  steps: 100
  batch_size: 8
  learning_rate: 0.001
```

这样做有三个好处：

1. **可复现。** 看到 config 就知道实验怎么跑。
2. **可对比。** 两个实验只差一个参数时，很容易定位变化来源。
3. **少改代码。** 新实验主要复制和修改 config，降低写错训练逻辑的风险。

后续 DnCNN、UNet、SIDD、RAW low-light 也会延续这个思路：换配置，跑实验，看结果。

### Q9：Backward 和 Optimizer 分别做什么？为什么两者都需要？

**参考答案：**

Backward 和 Optimizer 是训练里两个连续但不同的步骤。

Backward 负责计算梯度：

```text
loss -> gradients
```

它回答的问题是：为了让 loss 变小，每个参数应该往哪个方向调整？

Optimizer 负责更新参数：

```text
parameters + gradients -> new parameters
```

它回答的问题是：根据这些梯度，具体改多少、怎么改？

可以类比：

```text
Backward = 老师指出每道题错在哪里
Optimizer = 学生根据反馈修改自己的解题方法
```

只有 backward，没有 optimizer，模型知道错在哪里但不会改变。只有 optimizer，没有 backward，优化器不知道往哪里改。两者配合，模型参数才会随着训练逐步变好。

## 四、指标和结果分析

### Q10：train loss 从 0.112161 降到 0.034434 说明什么？

**参考答案：**

Train loss 表示模型输出 output 和训练目标 clean/target 之间的平均差距。这里使用的是 L1 loss，可以理解成平均像素绝对误差。

从：

```text
0.112161 -> 0.034434
```

说明模型在训练数据上的输出越来越接近 clean target。

这有两个含义：

1. 模型参数确实被训练更新了，不是随机输出。
2. TinyCNN 学到了一部分 noisy 到 clean 的映射。

但是 train loss 下降只能说明训练集上变好，不能单独证明泛化能力。因此还要看 validation PSNR / SSIM。

### Q11：val PSNR 从 17.61 提升到 26.70 说明什么？

**参考答案：**

PSNR 衡量 output 和 target 的像素误差。PSNR 越高，通常表示输出和目标的像素差异越小。

从：

```text
17.61 dB -> 26.70 dB
```

这是明显提升，说明在验证集上，模型输出更接近 clean target。

重点是 `val`。验证集不参与训练，所以 val PSNR 上升说明模型不是只记住训练样本，而是在没见过的样本上也有更好表现。

可以这样总结：

```text
训练不只是让 train loss 变低，也让验证图像更接近干净答案。
```

### Q12：val SSIM 从 0.7366 提升到 0.8457 说明什么？

**参考答案：**

SSIM 更关注图像结构相似度，包括亮度、对比度和结构信息。它不像 PSNR 那样只看像素误差。

从：

```text
0.7366 -> 0.8457
```

说明模型输出在结构上也更像 target。对于图像恢复来说，这很重要，因为有些输出可能像素误差低，但看起来过度平滑或结构不自然。

PSNR 和 SSIM 一起上升，说明：

```text
输出不仅像素更接近 target，结构也更接近 target。
```

但 SSIM 也不是完美主观指标。最终还要看可视化图。

### Q13：为什么不能只看 PSNR / SSIM？

**参考答案：**

因为图像质量不完全等于数字指标。PSNR / SSIM 有用，但它们不能覆盖所有主观质量。

例如：

- PSNR 高的图可能过度平滑，纹理被抹掉。
- SSIM 高的图可能颜色仍然偏。
- 指标可能对某些局部伪影不敏感。
- 人眼对肤色、边缘、暗部噪声、高光过曝特别敏感，指标未必充分反映。

所以 Week 0.5 强调：

```text
metrics.csv 看趋势
vis/ 看图像质量
```

正确判断方式是：

```text
loss 下降 + PSNR/SSIM 上升 + output 肉眼更接近 target
```

三者一起看，结论才更可靠。

## 五、可视化解读

### Q14：三联图 noisy / output / target 分别代表什么？

**参考答案：**

三联图从左到右固定为：

```text
noisy 输入 | output 模型输出 | target 干净目标
```

含义如下：

| 区域 | 含义 | 你要观察什么 |
|---|---|---|
| noisy | 加噪输入，模型实际看到的图 | 噪声有多明显 |
| output | 模型预测的去噪结果 | 是否比 noisy 更干净 |
| target | 干净目标，也就是答案 | output 离答案还有多远 |

它的价值在于同时提供三个参照：

1. noisy vs output：判断模型有没有去噪。
2. output vs target：判断模型离干净答案还有多远。
3. step 50 output vs step 100 output：判断多训练是否有效。

### Q15：看到 step 50 和 step 100 的可视化图时，应该怎么分析？

**参考答案：**

不要只说“看起来好一点”。应该按固定问题分析：

1. Noisy 是否有明显噪声？
2. Output 是否比 noisy 更平滑、更干净？
3. Output 是否接近 target？
4. Output 是否过度平滑，损失纹理？
5. Step 100 是否比 Step 50 更接近 target？

如果数字显示：

```text
loss 下降
PSNR 上升
SSIM 上升
```

同时图上看到 output 更接近 target，就可以说训练有效。

如果数字变好但图像变糊，就要谨慎：模型可能在优化指标，但主观质量未必更好。这就是为什么图像任务必须保留可视化对比。

## 六、实验设计和边界

### Q16：为什么说 Week 0.5 是 sanity check？

**参考答案：**

Sanity check 是最小合理性检查。Week 0.5 不追求最终效果，而是确认训练系统基本正常。

它要确认：

- 脚本能启动。
- 数据能生成。
- 模型能 forward。
- loss 能计算。
- backward 和 optimizer 能更新参数。
- train loss 会下降。
- validation 指标会改善。
- checkpoint 能保存。
- 可视化图能生成。

如果这些都成立，说明训练闭环是通的。后续实验如果失败，就更可能是数据、模型、超参数或任务设置的问题，而不是基础训练流程坏了。

### Q17：这次 tiny baseline 的结论应该怎么写，才不过度夸大？

**参考答案：**

合理结论应该克制：

```text
TinyCNN 在合成 RGB 去噪 toy 任务上成功学到基础 denoise 映射；
训练闭环、验证指标、checkpoint 和可视化输出均已跑通。
```

不能写成：

```text
模型已经解决真实图像去噪。
```

原因是：

- 数据是 toy Gaussian noise，不是真实手机噪声。
- 模型是 TinyCNN，不是强 baseline。
- 训练只有 100 step，不是充分训练。
- 指标改善不等于主观画质完美。

所以 Week 0.5 的正确定位是：完成 AI 图像恢复训练入门，而不是完成真实 AI-ISP。

### Q18：如果把 steps 从 100 改成 50，这是一个什么实验？

**参考答案：**

这是一个受控对比实验。它只改一个变量：训练步数。

原实验：

```yaml
steps: 100
```

新实验：

```yaml
steps: 50
```

如果其他配置都不变，就可以比较：

```text
训练 50 step 和训练 100 step，效果差多少？
```

这能帮助你理解 steps 对训练效果的影响。通常 100 step 会比 50 step 更好，因为模型有更多机会更新参数。

这种实验方法非常重要：

```text
只改一个变量 -> 跑实验 -> 看 metrics -> 看 vis -> 写结论
```

后续比较 DnCNN / UNet、L1 / L2、不同噪声强度，也都要遵循这个思路。

### Q19：SIDD、SID、NAFNet 分别是什么？它们和 Week 0.5 有什么关系？

**参考答案：**

SIDD 是 Smartphone Image Denoising Dataset，是真实手机图像去噪数据集。它用于更真实的 RGB / sRGB 去噪任务。

SID 是 See-in-the-Dark，是低光 RAW 增强数据集。它更接近 AI-ISP，因为输入常常是 RAW，涉及低光、噪声、曝光比例和 RAW 处理。

NAFNet 是图像恢复模型架构，不是数据集。它可以用于去噪、去模糊、超分等任务。

关系可以这样理解：

```text
Week 0.5 = 学训练闭环
SIDD = 后续真实 RGB 去噪数据
SID = 后续 RAW low-light 数据
NAFNet = 后续可以尝试的更强模型
```

Week 0.5 是进入它们之前的基础训练场。没有 Week 0.5 的闭环直觉，直接看 SIDD / SID / NAFNet 很容易只会跑命令，不知道结果为什么好或为什么坏。

## 七、综合题

### Q20：请完整复述 Week 0.5 的训练过程。

**参考答案：**

Week 0.5 用 `toy_rgb_denoise_tiny.yaml` 定义一个 RGB 合成去噪实验。配置文件指定实验名、输出目录、patch size、训练集和验证集大小、噪声强度、模型类型和训练参数。

训练开始后，Dataset 生成 clean RGB patch，并添加高斯噪声得到 noisy patch。DataLoader 每次取一个 batch。模型 TinyCNN 接收 noisy，输出 output。训练时用 L1 loss 比较 output 和 clean 的差距。然后通过 backward 计算梯度，再由 optimizer 更新模型参数。

每训练 50 step，会在验证集上计算 PSNR 和 SSIM，并保存 noisy / output / target 三联图。最终结果显示，train loss 从 0.112161 降到 0.034434，val PSNR 从 17.61 升到 26.70，val SSIM 从 0.7366 升到 0.8457。

这说明 TinyCNN 在 toy Gaussian noise 任务上学到了基础去噪映射，训练闭环有效。但它还不能代表真实手机噪声或产品级 AI-ISP 效果。下一步应该用 DnCNN / UNet 做模型对比，再逐步进入更真实的噪声模型和数据集。

### Q21：如果面试官问“这个 Week 0.5 项目有什么意义”，应该怎么回答？

**参考答案：**

可以这样回答：

> Week 0.5 的意义不是做出最强去噪效果，而是搭建 AI 图像恢复的最小可复现训练闭环。我用合成 RGB 去噪任务构造 clean/noisy paired data，通过配置文件启动 TinyCNN 训练，并完成 Dataset、DataLoader、Model、Loss、Backward、Optimizer、Validation、Checkpoint 和 Visualization 的完整流程。实验中 train loss 明显下降，验证 PSNR 和 SSIM 上升，并且保存了 noisy/output/target 三联图用于主观检查。这说明训练系统是通的，模型在 toy 任务上确实学到了基础去噪映射。后续可以在这个闭环上替换模型、loss、噪声模型和真实数据集，例如 DnCNN、UNet、SIDD 或 SID。

这个回答的重点是：你不是只会跑脚本，而是知道为什么要先跑 toy baseline，以及它如何支撑后续复杂实验。

### Q22：学完 Week 0.5 后，下一步最合理做什么？

**参考答案：**

下一步不要立刻跳到大模型或真实 RAW 数据。更合理的顺序是：

1. 跑 DnCNN 和 UNet baseline，比较不同模型结构。
2. 对比 residual prediction 和 direct clean prediction。
3. 对比 L1 和 L2 loss，看输出平滑程度、PSNR 和 SSIM。
4. 改变噪声强度范围，观察模型泛化。
5. 再进入 SIDD 真实手机 RGB 去噪。
6. 最后进入 SID / RAW low-light，把 Stage1 的 RAW/ISP 知识接回来。

原因是：Week 0.5 只证明训练闭环有效。接下来要逐步增加复杂度，每一步只引入一个主要变量。这样如果结果变化，你才能知道变化来自模型、loss、数据还是噪声设置。

## 八、自测标准

如果你能不看答案讲清楚下面 6 句话，就说明 Week 0.5 真正学会了：

1. 图像恢复是把退化图像恢复成更接近目标的图像，不是凭空生成新图。
2. Toy denoise 用 clean 生成 noisy，因此是 paired supervised learning。
3. 训练闭环包括 Dataset、DataLoader、Model、Loss、Backward、Optimizer、Validation、Checkpoint 和 Visualization。
4. Loss 下降、PSNR/SSIM 上升，说明模型在 toy 任务上确实学起来了。
5. 三联图 noisy/output/target 用来把数字指标和视觉效果对应起来。
6. Week 0.5 是 sanity check，不代表真实手机去噪已经解决。
