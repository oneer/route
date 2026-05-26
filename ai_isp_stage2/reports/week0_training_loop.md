# Week 0.5：最小训练闭环

配套复习材料：[Week 0.5 问答题](week0_qa.md)

## 0. 先回答：阶段二到底在学什么

阶段一学的是传统 Soft-ISP：你手写一条从 RAW 到可显示图像的处理链路，理解每个模块的输入、输出、假设和失败场景。

阶段二开始学 AI-ISP / 图像恢复。这里不再只靠人工设计规则，而是让模型从大量样本里学习一种映射关系：

```text
有问题的图像 -> 神经网络 -> 更接近目标的图像
```

例如：

```text
有噪声的图像 -> 去噪网络 -> 干净图像
低光 RAW -> 增强网络 -> 明亮自然图像
模糊图像 -> 去模糊网络 -> 清晰图像
低分辨率图像 -> 超分网络 -> 高分辨率图像
```

这类任务统称为 image restoration，也就是图像恢复。它的核心不是“生成一张全新的图”，而是尽量保留原图内容，同时修复噪声、模糊、低光、压缩损伤、分辨率不足等问题。

## 1. 图像恢复是什么

图像恢复可以理解成：输入图像里有某种退化，模型要把退化尽量还原。

常见退化如下：

| 任务 | 输入问题 | 输出目标 | 例子 |
|---|---|---|---|
| Denoise 去噪 | 图像有噪点、颗粒、彩色斑点 | 更干净的图像 | 夜景照片降噪 |
| Deblur 去模糊 | 手抖、运动导致边缘糊 | 更清晰的图像 | 手机拍运动物体 |
| Super-resolution 超分 | 分辨率低、细节少 | 更高分辨率图像 | 2x / 4x 放大 |
| Low-light enhancement 低光增强 | 图像太暗、噪声大、颜色偏 | 更亮、更干净 | 夜间 RAW 增强 |
| Demosaic 去马赛克 | Bayer RAW 每个像素只有一个颜色通道 | RGB 图像 | ISP 中 CFA 插值 |

你现在先学 denoise，是因为它最适合入门：输入和输出都是 RGB 图，任务直观，训练也容易跑通。

## 2. 为什么先用 toy RGB denoise

真实 AI-ISP 任务很快会变复杂：真实噪声不规则、RAW 格式多、数据集大、模型训练慢、指标协议也多。直接上真实任务，出问题时很难判断原因。

所以 Week 0.5 只做一个小任务：

```text
clean RGB patch -> 加合成噪声 -> noisy patch
noisy patch -> 小 CNN -> denoised patch
denoised patch 和 clean patch 做比较
```

这里的 clean 是“干净目标图”，noisy 是“人为加噪后的输入图”。因为噪声是我们自己加的，所以 clean / noisy 天然一一对应，这叫 paired data，也就是成对数据。

先用 toy 任务的好处：

- 数据可以随时生成，不需要下载大数据集。
- clean / noisy 对齐，不用处理复杂标定。
- 训练几分钟内能看到 loss 下降。
- 如果这里都跑不通，说明训练代码、模型、环境或指标有基础问题。
- 如果这里跑通，后续再上真实数据时，问题范围会小很多。

## 3. 最小训练闭环长什么样

本周要验证的是这条工程链路：

```text
Dataset -> DataLoader -> Model -> Loss -> Backward -> Optimizer
  -> Validation -> Checkpoint -> Visualization
```

逐个翻译：

| 名词 | 人话解释 | 在本项目里对应什么 |
|---|---|---|
| Dataset | 数据集，负责拿出一对输入和目标 | `ToyRGBDenoiseDataset` 生成 clean / noisy patch |
| DataLoader | 批量取数据的小工人 | 每次取 batch_size 张 patch |
| Model | 神经网络 | `TinyCNN`、`DnCNN`、`UNet` |
| Loss | 训练时的错误分数 | 输出图和 clean 图之间的 L1 差异 |
| Backward | 反向传播，计算每个参数该怎么改 | `loss.backward()` |
| Optimizer | 真正更新参数的算法 | Adam 优化器 |
| Validation | 验证，不参与训练，只检查效果 | 在 val set 上算 PSNR / SSIM |
| Checkpoint | 保存模型权重 | `last.pth`、`best_psnr.pth` |
| Visualization | 保存可视化图 | noisy / output / target 三联图 |

可以把训练想成一个循环：

```text
1. 取一批 noisy / clean
2. 把 noisy 喂给模型，得到 output
3. 比较 output 和 clean，得到 loss
4. 根据 loss 更新模型参数
5. 重复很多次
6. 每隔一段时间，用验证集检查模型有没有真的变好
```

## 4. 每个核心名词再讲细一点

### Dataset

Dataset 决定“模型看到什么样的问题”。

在本项目里，Dataset 会生成一张 clean RGB patch，然后给它加随机高斯噪声，得到 noisy patch：

```text
clean -> add noise -> noisy
```

训练时模型只看 noisy，目标是输出接近 clean 的结果。

### Patch

Patch 是从图像里切出的小块，比如 64x64。

为什么不直接训练整张大图？

- 小 patch 更省显存。
- 一张图能切出很多训练样本。
- 去噪、纹理恢复这类任务常常可以从局部学习。
- 训练更快，适合入门验证。

### Batch

Batch 是“一次喂给模型的多张 patch”。

如果 `batch_size = 8`，意思是一次训练用 8 个 patch 算平均 loss，再更新一次模型。batch 太小会不稳定，太大会占显存。

### Model

Model 是可学习的函数。

传统 ISP 里，你手写规则：

```text
if hot pixel: replace with neighbor median
```

AI 图像恢复里，你让模型学习：

```text
noisy patch -> clean patch
```

模型内部有很多参数。训练就是不断调整这些参数，让输出越来越接近目标。

### Loss

Loss 是训练时用的错误分数。loss 越小，说明 output 和 target 越接近。

本项目常用 L1 loss：

```text
L1 = average(abs(output - target))
```

直觉上，它在问：每个像素平均差多少？

### Backward

Backward 是反向传播。它会计算：为了让 loss 变小，每个模型参数应该往哪个方向改。

你不需要一开始就推导公式，但要知道它的作用：

```text
loss -> gradients
```

gradient 就是“参数修改方向的提示”。

### Optimizer

Optimizer 根据 gradients 更新模型参数。

本项目用 Adam。可以先理解成一个更聪明的梯度下降：它不只是看当前方向，还会参考之前的更新趋势，让训练更稳。

### Validation

Validation 是验证集评估。它和训练集分开，作用是检查模型有没有真的学会，而不是只记住训练样本。

训练集表现变好不一定代表模型真的有用；验证集变好才更可信。

### Checkpoint

Checkpoint 是保存下来的模型参数文件。

本项目会保存：

- `last.pth`：最后一次训练状态。
- `best_psnr.pth`：验证 PSNR 最好的模型。

以后继续训练、复现实验、比较模型，都需要 checkpoint。

### Visualization

只看数字不够。图像任务一定要看图。

本项目保存三联图：

```text
noisy | output | target
```

你要观察：

- output 是否比 noisy 更干净。
- target 细节有没有被保留。
- output 是否过度平滑。
- 边缘、纹理、暗部有没有异常。

## 5. PSNR 和 SSIM 是什么

训练用 loss，验证时常看 PSNR / SSIM。

### PSNR

PSNR 是峰值信噪比。它衡量 output 和 target 的像素误差大小。

大致理解：

```text
PSNR 越高 -> 像素差异越小
```

在去噪任务里，PSNR 经常用来比较模型，但它不等于“人眼一定觉得更好”。有些图 PSNR 高，却可能偏平、细节少。

### SSIM

SSIM 更关注结构相似度，比如亮度、对比度、纹理结构。

大致理解：

```text
SSIM 越接近 1 -> 结构越接近 target
```

SSIM 比 PSNR 更接近一点主观感受，但也不是完美指标。

### 为什么还要看可视化

因为图像质量有很多主观因素：

- 噪声是不是自然。
- 纹理有没有糊。
- 颜色有没有偏。
- 边缘有没有假影。
- 暗部有没有涂抹感。

所以训练报告不能只写数字，还要看 `vis/step_*.png`。

## 6. SIDD、SID、RAW low-light、NAFNet 是什么

这些名词现在先不用深挖，但要知道它们在路线图里的位置。

### SIDD

SIDD 全名是 Smartphone Image Denoising Dataset，手机图像去噪数据集。

它主要用于真实手机 RGB / sRGB 去噪。和 toy Gaussian noise 不同，SIDD 的噪声来自真实手机拍摄，更接近实际场景。

你可以先这样记：

```text
SIDD = 真实手机照片去噪数据集
```

后续从 toy denoise 进入真实 RGB denoise 时，SIDD 是常见下一站。

### SID

SID 全名是 See-in-the-Dark，是低光 RAW 增强数据集。

它关注极暗场景：短曝光、噪声很大的 RAW 输入，目标是恢复成长曝光或更明亮干净的图像。

你可以先这样记：

```text
SID = 低光 RAW 增强数据集
```

SID 更接近 AI-ISP，因为输入通常是 RAW，而不是已经处理好的 RGB。

### RAW low-light

RAW low-light 指 RAW 域低光增强任务。

它和普通 RGB 去噪不同：

- 输入是 RAW，和 Stage1 的 ISP 知识连接更紧。
- 噪声更强，暗部更难。
- 需要理解 black level、white level、Bayer pattern、曝光比例。
- 输出可能是 RGB，也可能接一个 learned ISP pipeline。

这会是阶段二后面很重要的方向，但不适合作为第一步。

### NAFNet

NAFNet 是一种图像恢复网络结构，常用于去噪、去模糊、超分等任务。

它不是数据集，而是模型架构。

你可以先这样记：

```text
SIDD / SID = 数据集
NAFNet = 模型
```

现在不直接跳 NAFNet，是因为你还需要先理解训练闭环、loss、metric、数据退化和 baseline 对比。否则模型越复杂，越难知道自己到底学会了什么。

## 7. 当前实现

- `ToyRGBDenoiseDataset` 生成确定性的 clean / noisy RGB patch。
- `TinyCNN`、`DnCNN`、`UNet` 提供从 sanity check 到 baseline 的模型选择。
- `train_from_config()` 支持配置驱动训练、验证、checkpoint 和可视化。
- `metrics.csv` 记录每次验证的 train loss、PSNR 和 SSIM。
- `vis/step_*.png` 保存 noisy / output / target 三联图。

## 8. 验收标准

1. 训练脚本能从配置文件启动。
2. train loss 整体下降。
3. validation PSNR / SSIM 随训练整体上升。
4. `last.pth` 和 `best_psnr.pth` 能正常保存。
5. 验证图能看出 output 比 noisy 更干净。
6. 能用自己的话解释 Dataset、Model、Loss、Optimizer、Validation、Checkpoint、Visualization。

## 9. 本次启动结果

命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

`toy_rgb_denoise_tiny` 已跑通 100 step：

| step | train loss | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 50 | 0.112161 | 17.61 | 0.7366 |
| 100 | 0.034434 | 26.70 | 0.8457 |

### 结果怎么解读

这张表最重要的不是某一个单独数字，而是从 50 step 到 100 step 的变化趋势。

#### 1. train loss 明显下降

```text
0.112161 -> 0.034434
```

`train loss` 表示模型输出 `output` 和干净目标 `target / clean` 之间的平均差距。它下降说明：模型在训练集上确实学会了把 noisy patch 往 clean patch 拉近。

直观理解：

```text
loss 越低 -> output 和 clean 的像素差距越小
```

这里 loss 降了很多，说明 100 step 时模型已经不再是随机输出，而是学到了一部分去噪映射。

#### 2. val PSNR 大幅上升

```text
17.61 dB -> 26.70 dB
```

`val PSNR` 是验证集上的像素误差指标。PSNR 越高，通常说明 output 和 target 的像素差异越小。

这次从 17.61 上升到 26.70，提升非常明显，说明模型不只是记住训练样本，在没参与训练的验证样本上也变好了。

直观理解：

```text
PSNR 上升 -> 输出图更接近干净答案
```

#### 3. val SSIM 上升

```text
0.7366 -> 0.8457
```

`val SSIM` 更关注结构相似度。它上升说明模型输出不只是像素值更接近，图像结构也更接近 target。

直观理解：

```text
SSIM 上升 -> 亮度、对比度、纹理结构更像干净图
```

#### 4. 这说明模型有什么效果

这次 tiny baseline 的效果可以总结为：

```text
模型已经学会了基础去噪：
输入 noisy patch 后，输出会比输入更接近 clean patch。
```

具体表现是：

- 噪声被压低了一部分。
- output 和 target 的像素差距变小。
- 图像结构更稳定。
- 训练到 100 step 比 50 step 明显更好。

这就说明 Week 0.5 的最小训练闭环是有效的。

#### 5. 这还不能说明什么

不过，这个结果也不能过度解读：

- 它只是在 toy Gaussian noise 上有效，不代表真实手机噪声也能处理好。
- TinyCNN 很小，不代表它是最佳模型。
- PSNR / SSIM 变好，不等于主观画质一定完美。
- 100 step 只是 sanity check，不是充分训练。

所以本次结论应该写得克制一点：

```text
TinyCNN 在合成 RGB 去噪 toy 任务上成功学到基础 denoise 映射；
训练闭环、验证指标、checkpoint 和可视化输出均已跑通。
下一步可以用 DnCNN / UNet 做模型对比，再逐步进入更真实的噪声模型。
```

输出位置：

- `ai_isp_stage2/runs/toy_rgb_denoise_tiny/checkpoints/`
- `ai_isp_stage2/runs/toy_rgb_denoise_tiny/vis/`
- `ai_isp_stage2/runs/toy_rgb_denoise_tiny/metrics.csv`

## 10. 本次实验的具体过程

这次 Week 0.5 实验可以拆成 8 个连续动作。你要学的不是某一个孤立名词，而是这些动作之间怎么接起来。

### 第 1 步：选一份配置

运行命令里最重要的是 `--config`：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

这句话的意思是：用 `01_train_toy_rgb.py` 作为训练入口，并读取 `toy_rgb_denoise_tiny.yaml` 这份实验说明书。

配置文件决定了这次实验的基本信息：

```yaml
experiment:
  name: toy_rgb_denoise_tiny
  seed: 42
  output_dir: runs/toy_rgb_denoise_tiny
```

你可以把它理解成：

- `name`：这次实验叫什么。
- `seed`：随机过程固定住，方便下次复现。
- `output_dir`：训练结果保存到哪里。

### 第 2 步：生成 toy 数据

这次不用真实照片数据集，而是生成合成数据：

```text
clean patch -> 加高斯噪声 -> noisy patch
```

配置里对应的是：

```yaml
data:
  patch_size: 64
  train_size: 256
  val_size: 16
  noise:
    type: gaussian
    sigma_min: 0.03
    sigma_max: 0.12
```

这里发生的事是：

1. 程序生成一批 64x64 的 RGB 小图块，作为 `clean`。
2. 给 clean 加随机噪声，得到 `noisy`。
3. 训练时输入 noisy，答案是 clean。
4. 模型要学习把 noisy 变回接近 clean。

所以这不是“随便让模型看图”，而是在构造一个明确任务：

```text
输入：有噪声的小图
目标：干净的小图
```

### 第 3 步：创建模型

配置里写的是：

```yaml
model:
  name: tiny_cnn
  in_channels: 3
  out_channels: 3
  features: 32
```

这表示：

- 输入是 RGB，所以 `in_channels = 3`。
- 输出也是 RGB，所以 `out_channels = 3`。
- `tiny_cnn` 是一个很小的 CNN，用来确认训练流程能跑通。

此时模型还没有学会去噪。刚开始它只是一个带随机参数的函数：

```text
noisy -> tiny_cnn -> output
```

训练的目的就是不断调整 tiny_cnn 内部参数，让 output 越来越接近 clean。

### 第 4 步：前向传播

每次训练会取一个 batch。当前配置是：

```yaml
batch_size: 8
```

也就是一次拿 8 个 noisy / clean patch。

模型先做一次预测：

```text
output = model(noisy)
```

这一过程叫 forward，前向传播。它只是把输入送进模型，得到输出。

### 第 5 步：计算 loss

模型输出之后，要比较：

```text
output 和 clean 差多少？
```

当前配置：

```yaml
loss: l1
```

L1 loss 可以先理解成：

```text
每个像素的平均绝对差
```

如果 output 和 clean 差很多，loss 就大；如果 output 越来越接近 clean，loss 就会下降。

### 第 6 步：反向传播并更新参数

训练真正发生在这里：

```text
loss -> backward -> optimizer -> 更新模型参数
```

直觉上：

1. loss 告诉模型“这次错了多少”。
2. backward 计算“每个参数该往哪个方向改”。
3. optimizer 按照这个方向更新参数。

一次参数更新就是一个 step。当前配置：

```yaml
steps: 100
```

表示模型会更新 100 次。

### 第 7 步：验证

训练不能只看训练集，因为模型可能只是记住了训练样本。所以每隔一段时间要在验证集上检查。

当前配置：

```yaml
val_every: 50
```

表示每 50 step 验证一次。验证时会计算：

- PSNR：像素误差是否变小。
- SSIM：结构是否更接近 clean。

这就是终端里这两行的来源：

```text
val step=0050 psnr=17.61 ssim=0.7366
val step=0100 psnr=26.70 ssim=0.8457
```

### 第 8 步：保存结果

训练结束后，最重要的输出有三类：

| 输出 | 路径 | 用途 |
|---|---|---|
| 指标表 | `runs/toy_rgb_denoise_tiny/metrics.csv` | 看 loss / PSNR / SSIM 变化 |
| 模型权重 | `runs/toy_rgb_denoise_tiny/checkpoints/` | 保存模型，后续可继续训练或复现 |
| 可视化图 | `runs/toy_rgb_denoise_tiny/vis/` | 肉眼检查去噪效果 |

所以这次实验的完整闭环是：

```text
读 config
-> 生成 clean/noisy 数据
-> 创建 tiny_cnn
-> noisy 输入模型得到 output
-> output 和 clean 算 loss
-> backward + optimizer 更新参数
-> 每 50 step 做 validation
-> 保存 metrics / checkpoints / vis
```

## 11. 对比图怎么读

本项目保存的是三联图，从左到右固定为：

```text
noisy 输入 | output 模型输出 | target 干净目标
```

也就是说：

- 左边 noisy：模型实际看到的输入，带噪声。
- 中间 output：模型当前给出的去噪结果。
- 右边 target：干净答案，也就是模型想接近的目标。

### Step 50 可视化

![TinyCNN step 50 denoise triplet](figures/week0_tiny_step_0050.png)

Step 50 表示模型已经更新了 50 次参数。此时你要看：

- 左边 noisy 是否能看到明显噪声。
- 中间 output 是否已经比 noisy 更平滑。
- 中间 output 和右边 target 还有多大差距。
- 如果 output 发灰、发糊或颜色不准，说明模型还没完全学好。

对应指标：

| step | train loss | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 50 | 0.112161 | 17.61 | 0.7366 |

这个阶段的意义是：模型开始学到“去掉一部分噪声”，但结果还不够接近 target。

### Step 100 可视化

![TinyCNN step 100 denoise triplet](figures/week0_tiny_step_0100.png)

Step 100 表示模型又多训练了 50 次。现在你要和 Step 50 对比：

- output 是否更接近 target。
- 噪声是否进一步减少。
- 图像是否出现过度平滑。
- 颜色和亮度是否更稳定。

对应指标：

| step | train loss | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 100 | 0.034434 | 26.70 | 0.8457 |

从数字看：

```text
loss: 0.112161 -> 0.034434  下降
PSNR: 17.61 -> 26.70        上升
SSIM: 0.7366 -> 0.8457      上升
```

从图像看：中间 output 应该比 Step 50 更接近右边 target。

这就是 Week 0.5 最重要的判断方式：

```text
数字趋势变好 + 可视化更接近 target = 训练确实学起来了
```

### 为什么三联图比单张 output 更有用

如果只看 output，你不知道它到底好不好。三联图能同时回答三个问题：

| 对比 | 你在判断什么 |
|---|---|
| noisy vs output | 模型有没有去掉噪声 |
| output vs target | 模型离干净答案还有多远 |
| step 50 output vs step 100 output | 多训练一段时间有没有进步 |

以后做 DnCNN、UNet、SIDD、RAW low-light，也会一直用这种思路：

```text
输入是什么？
模型输出是什么？
目标答案是什么？
输出比输入好在哪里？
输出离目标还差在哪里？
```

## 12. 这一周真正要学会什么

Week 0.5 不是为了学会某个厉害模型，也不是为了做出产品级去噪效果。它真正训练的是你进入 AI-ISP 前必须具备的第一个能力：

```text
我能把一个图像恢复实验跑起来，并判断它有没有学起来。
```

更具体地说，学完 Week 0.5，你应该得到 5 个能力。

### 能力 1：知道一个 AI 图像实验由哪几块组成

你要能把一次训练拆成这几块：

```text
config -> dataset -> model -> loss -> optimizer -> validation -> output files
```

这意味着你以后看到任何 AI-ISP 项目，都不会只觉得“它在跑一个黑盒”。你会先问：

- 数据在哪里？
- 模型是谁？
- loss 怎么算？
- 验证指标是什么？
- 输出保存到哪里？

### 能力 2：能独立启动一个实验

你要能看懂这条命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

它的意思是：

```text
用 01_train_toy_rgb.py 这个训练入口，
读取 toy_rgb_denoise_tiny.yaml 这份实验配置，
启动一次 tiny RGB 去噪训练。
```

这就是后面所有实验的基本形态。以后换 DnCNN、UNet、SIDD、RAW low-light，本质上仍然是：

```text
换一份 config，再跑同一个或类似的训练入口。
```

### 能力 3：能看懂训练有没有变好

你要能打开：

```text
ai_isp_stage2/runs/toy_rgb_denoise_tiny/metrics.csv
```

并判断：

```text
loss 是否下降
PSNR 是否上升
SSIM 是否上升
```

如果你看到：

```text
50 step:  loss=0.112161, PSNR=17.61, SSIM=0.7366
100 step: loss=0.034434, PSNR=26.70, SSIM=0.8457
```

你就应该能说：

```text
这个模型确实在学习。它输出的图像越来越接近 clean target。
```

这比“知道 PSNR 是什么”更重要。Week 0.5 不是让你背指标定义，而是让你形成判断训练趋势的习惯。

### 能力 4：能把数字和图像对应起来

图像任务不能只看数字。你还要打开：

```text
ai_isp_stage2/runs/toy_rgb_denoise_tiny/vis/step_0050.png
ai_isp_stage2/runs/toy_rgb_denoise_tiny/vis/step_0100.png
```

你要能回答：

- noisy 是输入，有噪声。
- output 是模型输出，应该更干净。
- target 是干净答案，也就是模型想接近的目标。
- step 100 的 output 应该比 step 50 更接近 target。

如果你能把 `metrics.csv` 里的数字变化和 `vis/` 里的图像变化联系起来，就已经跨过 AI 图像恢复的第一道门了。

### 能力 5：能改一个配置做一个小对比

最后，你要知道 config 不是摆设。比如把：

```yaml
steps: 100
```

改成：

```yaml
steps: 50
```

并改一个新的实验名和输出目录，你就能比较：

```text
训练 50 step 和训练 100 step，哪个效果更好？
```

这件事很小，但它是做实验的开始。AI-ISP 后面所有工作，本质都是不断做这种受控对比：

```text
只改一个变量 -> 跑实验 -> 看 metrics -> 看图 -> 写结论
```

### Week 0.5 暂时不学什么

为了不把一开始学得太散，这一周暂时不要求：

- 不要求理解 CNN 每一层的数学细节。
- 不要求理解 DnCNN / UNet 的完整结构。
- 不要求下载 SIDD / SID。
- 不要求训练大模型。
- 不要求做真实 RAW low-light。
- 不要求追求最高 PSNR。

这些都放到后面。Week 0.5 只解决一件事：

```text
从“我不知道 AI 图像实验怎么开始”
变成
“我知道一次训练实验怎么启动、怎么看结果、怎么做最小对比”。
```

学完 Week 0.5，你不需要马上会设计新模型，但要能回答：

1. 图像恢复和传统 ISP 有什么关系？
2. 为什么先从 toy RGB denoise 开始？
3. clean、noisy、output、target 分别是什么？
4. Dataset / DataLoader / Model / Loss / Optimizer 分别负责什么？
5. 为什么训练集和验证集要分开？
6. PSNR / SSIM 能说明什么，不能说明什么？
7. checkpoint 和可视化为什么重要？
8. SIDD、SID、NAFNet 分别是数据集还是模型？

一句话总结：Week 0.5 的目标不是追高分，而是建立神经网络图像恢复的第一条可解释训练闭环。

## 13. Week 0.5 到底怎么学

这一周不要按“读完所有名词”的方式学。更好的方式是按三次动手实验走，每次只解决一个问题。

### 第一次：先把训练跑起来

目标：确认你知道“一个训练实验从哪里启动、输出到哪里”。

先运行：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

然后只看三样东西：

1. 终端里有没有打印 `step=... loss=...`。
2. 终端里有没有打印 `val step=... psnr=... ssim=...`。
3. `ai_isp_stage2/runs/toy_rgb_denoise_tiny/` 下面有没有生成结果。

这一步不要急着理解所有代码。你只需要先建立一个大图：

```text
配置文件 -> 训练脚本 -> 模型训练 -> 保存结果
```

完成后写下这句话：

```text
我已经知道 Stage2 的实验是通过 config 启动的，训练结果会保存到 runs/。
```

### 第二次：看懂一次训练产生了什么

目标：把输出文件和训练过程对应起来。

打开：

```text
ai_isp_stage2/runs/toy_rgb_denoise_tiny/metrics.csv
```

你会看到类似：

```text
step,train_loss,val_psnr,val_ssim
50,0.112161,17.6088,0.73656
100,0.034434,26.7033,0.84572
```

这样理解：

- `step`：训练进行了多少次参数更新。
- `train_loss`：训练时 output 和 clean 的差距。
- `val_psnr`：验证集上 output 和 clean 的像素误差指标。
- `val_ssim`：验证集上 output 和 clean 的结构相似度。

你要观察的不是某个数字本身，而是趋势：

```text
loss 下降
PSNR 上升
SSIM 上升
```

这说明模型不是乱输出，而是在逐渐学会把 noisy 变得接近 clean。

然后打开：

```text
ai_isp_stage2/runs/toy_rgb_denoise_tiny/vis/step_0050.png
ai_isp_stage2/runs/toy_rgb_denoise_tiny/vis/step_0100.png
```

看图时按这个顺序问自己：

1. noisy 有没有明显噪声？
2. output 比 noisy 干净吗？
3. output 和 target 还有什么差距？
4. step 100 是否比 step 50 更好？

完成后写下这句话：

```text
我已经知道 metrics.csv 看数字趋势，vis/ 看图像质量，二者要一起判断。
```

### 第三次：只改一个参数，看训练有什么变化

目标：理解配置文件不是摆设，而是在控制实验。

先打开：

```text
ai_isp_stage2/configs/toy_rgb_denoise_tiny.yaml
```

只看这几项：

```yaml
data:
  patch_size: 64
  train_size: 256
  val_size: 16
  noise:
    sigma_min: 0.03
    sigma_max: 0.12

train:
  steps: 100
  batch_size: 8
  learning_rate: 0.001
```

这些参数先这样理解：

| 参数 | 意思 | 改大/改小会发生什么 |
|---|---|---|
| `patch_size` | 每张训练小图的尺寸 | 越大越慢，但看到的区域更多 |
| `train_size` | 训练集样本数 | 越大越稳定，但更慢 |
| `val_size` | 验证集样本数 | 越大评估更稳，但更慢 |
| `sigma_min/max` | 噪声强度范围 | 越大任务越难 |
| `steps` | 训练步数 | 越大训练更久，通常更好 |
| `batch_size` | 每次训练喂多少张 patch | 越大越占内存 |
| `learning_rate` | 每次参数更新幅度 | 太大容易不稳定，太小学得慢 |

第一次不要改很多。只做一个小实验：把 `steps` 从 100 改成 50，另存为：

```text
ai_isp_stage2/configs/toy_rgb_denoise_tiny_50step.yaml
```

并把实验名也改掉：

```yaml
experiment:
  name: toy_rgb_denoise_tiny_50step
  output_dir: runs/toy_rgb_denoise_tiny_50step
```

再运行：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50step.yaml
```

比较两个结果：

```text
runs/toy_rgb_denoise_tiny/metrics.csv
runs/toy_rgb_denoise_tiny_50step/metrics.csv
```

你应该能看到：50 step 的结果通常不如 100 step。这个实验的重点不是追分，而是理解：

```text
训练步数会影响模型学到多少。
```

完成后写下这句话：

```text
我已经知道改 config 可以定义一个新实验，并且能用 metrics 和 vis 比较两个实验。
```

## 14. 你今天的最小学习任务

如果你今天只学 1 小时，按这个顺序来：

1. 读第 0 到第 3 节，只要求知道整体流程。
2. 跑一次 `toy_rgb_denoise_tiny`。
3. 打开 `metrics.csv`，确认 loss 下降、PSNR / SSIM 上升。
4. 打开 `vis/step_0050.png` 和 `vis/step_0100.png`，肉眼比较 noisy / output / target。
5. 回到配置文件，看懂 `steps`、`batch_size`、`learning_rate`、`sigma_min/max` 分别控制什么。

今天不用学 DnCNN、UNet、SIDD、SID、NAFNet。那些是后面的事。

今天真正的完成标准是：

```text
我能从 config 启动一个训练实验，知道它输出了什么，并能用 loss、PSNR、SSIM 和可视化判断它有没有学起来。
```

## 15. 如果还是卡住，从这里开始

只记住这四个文件：

| 文件 | 你用它干什么 |
|---|---|
| `configs/toy_rgb_denoise_tiny.yaml` | 带注释的实验说明书，先从这里看 |
| `scripts/01_train_toy_rgb.py` | 启动训练，重点看最后的 `main()` |
| `runs/toy_rgb_denoise_tiny/metrics.csv` | 看数字有没有变好 |
| `runs/toy_rgb_denoise_tiny/vis/step_0100.png` | 看输出图有没有变好 |

也就是说，Week 0.5 的学习入口不是论文，不是模型结构图，而是这条最短路径：

```text
看 config -> 跑 script -> 查 metrics -> 看 vis
```

等这条路径顺了，再去读 Dataset、Model、Loss、Optimizer 的代码。

建议阅读顺序：

1. 打开 `configs/toy_rgb_denoise_tiny.yaml`，只读注释，不急着记参数。
2. 找到 `experiment`，理解“实验叫什么、输出到哪里”。
3. 找到 `data`，理解“训练数据怎么生成”。
4. 找到 `model`，理解“这次用哪个网络”。
5. 找到 `train`，理解“训练多少步、多久验证一次”。
6. 再打开 `scripts/01_train_toy_rgb.py`，只看 `main()` 里的三步注释。

先不要读 `train.py`、`toy_rgb_dataset.py`、`tiny_cnn.py`。那些是第二轮再读的代码细节。
