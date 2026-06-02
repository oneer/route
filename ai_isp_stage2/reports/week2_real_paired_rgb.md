# Week 2：真实成对 RGB 数据入口

Week 2 不是为了“换一个更厉害的模型”，也不是为了马上冲 RAW、SID、NAFNet。

这一周真正要学的是：

```text
把 Week 1 已经跑通的训练闭环，接到真实 noisy/clean RGB 图片上。
```

也就是说，Week 0 让你理解训练，Week 1 让你在 toy RGB 去噪里跑通模型、loss、指标和可视化，Week 2 开始解决真实图像训练里最容易踩坑的地方：数据入口。

## 0. 它和 Week 1 怎么接上

Week 1 最后已经做过 `paired RGB smoke`。那一步的数据虽然还是合成出来的，但它证明了一件关键事情：

```text
训练代码已经不只会读 toy dataset，也能读 noisy/clean 文件夹里的成对图片。
```

Week 2 就是在这个基础上往前走一步：

| Week 1 | Week 2 |
|---|---|
| toy RGB：代码生成 clean，再人工加噪 | real paired RGB：从真实 noisy/clean 图片开始 |
| paired RGB smoke：验证文件夹数据链路 | SIDD-style tiny subset：整理真实小子集 |
| 重点看模型、loss、patch、baseline | 重点看数据配对、尺寸、对齐、真实 baseline |
| 目标是理解训练怎么学 | 目标是确认真实数据能稳定进入训练 |

所以 Week 2 不是重复 Week 1，也不是突然进入新方向。它是在问：

```text
同一套训练闭环，换成真实 noisy/clean RGB 图片后，还能不能正确工作？
```

## 1. Week 2 到底在干嘛

Week 1 的 toy RGB 数据是代码自动生成的：

```text
clean patch -> 人工加噪 -> noisy patch
```

这种数据很适合学习训练流程，因为 noisy 和 clean 天然对齐，噪声强度可控，图片尺寸也统一。

但真实数据不是这样。真实 paired RGB 数据通常来自相机、手机或公开数据集，它会遇到这些问题：

| 问题 | 为什么麻烦 |
|---|---|
| noisy 和 clean 文件名不一定一样 | 训练器不知道哪两张图是一对 |
| 图片尺寸可能不同 | loss 不能直接逐像素计算 |
| 数据目录结构不统一 | dataset loader 读不到 |
| clean 可能叫 GT、groundtruth、reference | 需要先归一化命名 |
| noisy/clean 可能裁剪不对齐 | 指标会很差，模型也学不到正确映射 |
| 数据太大 | 初学阶段直接全量训练很慢，也更难排查 |

所以 Week 2 的核心任务不是“训练出最好效果”，而是先建立一个可靠的小型真实数据入口：

```text
真实 noisy/clean 图片
  -> 统一配对
  -> 统一尺寸
  -> 统一目录
  -> 测 noisy 输入 baseline
  -> 小步训练
  -> 看 metrics / checkpoint / 三联图
```

![Week 2 paired RGB 数据管线](figures/week2_paired_rgb_data_pipeline.png)

## 2. 为什么这一步很重要

图像恢复训练最怕的不是模型小，而是数据错。

如果 noisy 和 clean 没有真正配对，模型看到的是：

```text
输入：房间 A 的 noisy 图
答案：房间 B 的 clean 图
```

这时 loss 仍然可以计算，训练也仍然会跑，甚至 `metrics.csv` 也会生成，但模型学到的是错误关系。

如果 noisy 和 clean 尺寸一样但裁剪位置不同，模型看到的是：

```text
输入：左上角的 noisy patch
答案：中间区域的 clean patch
```

这种错误更隐蔽。它不会马上报错，但 PSNR / SSIM 很可能上不去，三联图也会出现 output 变糊、细节不对、纹理错位的问题。

所以 Week 2 先做数据整理，是为了在进入更大数据、更强模型前，把最基础的真实数据训练接口确认清楚。

## 3. Week 2 不急着做什么

这一周先不急着做这些：

| 先不做 | 原因 |
|---|---|
| 不急着上 NAFNet | 如果数据入口错了，强模型只会更快学错 |
| 不急着做 SID / RAW low-light | RAW 数据涉及 Bayer、黑电平、白平衡、颜色空间，复杂度会突然升高 |
| 不急着全量 SIDD | 初学阶段全量数据太慢，不利于排查 |
| 不急着追最高 PSNR | Week 2 的第一目标是“真实数据能稳定读、训、评、看” |
| 不急着调很多超参数 | 数据配对没确认前，调参没有意义 |

可以把 Week 2 理解成真实数据实验的地基。地基不复杂，但必须扎实。

## 4. 什么是 paired RGB

paired RGB 的意思是：每个 noisy 输入都有一张对应的 clean 答案。

最理想的配对关系是：

```text
noisy/pair_00001.png  <->  clean/pair_00001.png
noisy/pair_00002.png  <->  clean/pair_00002.png
noisy/pair_00003.png  <->  clean/pair_00003.png
```

这里的 “paired” 有三个要求：

| 要求 | 含义 |
|---|---|
| 同一场景 | noisy 和 clean 拍的是同一个内容 |
| 同一尺寸 | 两张图可以逐像素比较 |
| 同一对齐 | 第 100 行第 100 列对应同一个物体位置 |

RGB 的意思是这里先使用普通三通道图片：

```text
R 通道 + G 通道 + B 通道
```

它暂时不处理 RAW sensor mosaic，也不处理 ISP pipeline 的黑电平、demosaic、颜色校正等问题。

这正是 Week 2 的价值：先用真实 RGB 数据建立训练入口，再逐步走向更真实、更复杂的 RAW / low-light 任务。

## 5. 目标目录结构

准备后的数据放在：

```text
ai_isp_stage2/datasets/sidd_tiny/
  train/
    noisy/
      pair_00001.png
      pair_00002.png
    clean/
      pair_00001.png
      pair_00002.png
  val/
    noisy/
      pair_00001.png
      pair_00002.png
    clean/
      pair_00001.png
      pair_00002.png
```

训练器只关心最终这个结构。

也就是说，外部数据原来叫 `NOISY_SRGB_001.png`、`GT_SRGB_001.png`、`clean_001.jpg` 都没关系。只要整理后变成同名的 noisy/clean pair，后面的训练代码就能读。

真实图片数据通常不要提交进 git。这里提交的是脚本、配置和报告，数据目录可以在本地生成。

## 6. 数据准备脚本

脚本位置：

```text
ai_isp_stage2/scripts/04_prepare_paired_rgb_subset.py
```

用途：

```text
从外部 noisy 文件夹和 clean 文件夹中，抽取一个小型 paired RGB 子集，
统一命名、统一目录，并划分 train / val。
```

命令模板：

```bash
python ai_isp_stage2/scripts/04_prepare_paired_rgb_subset.py --source-noisy-dir path/to/noisy --source-clean-dir path/to/clean --output-dir ai_isp_stage2/datasets/sidd_tiny --train-count 80 --val-count 20 --size 512
```

参数解释：

| 参数 | 含义 | 建议 |
|---|---|---|
| `--source-noisy-dir` | 外部 noisy 图片根目录 | 指向真实带噪图片 |
| `--source-clean-dir` | 外部 clean / GT 图片根目录 | 指向对应干净图 |
| `--output-dir` | 整理后的输出目录 | 默认用 `datasets/sidd_tiny` |
| `--train-count` | 写入训练集的 pair 数量 | 初学先 80 左右 |
| `--val-count` | 写入验证集的 pair 数量 | 初学先 20 左右 |
| `--size` | 统一中心裁剪尺寸 | 512 比较适合先排查 |

脚本会递归搜索常见图片格式：

```text
.jpg / .jpeg / .png / .bmp / .tif / .tiff
```

然后根据文件名生成配对 key。它会尽量忽略这些词：

```text
noisy / clean / gt / srgb / rgb
```

例如：

```text
NOISY_SRGB_0001.png
GT_SRGB_0001.png
```

会被认为可能是一对，并输出为：

```text
train/noisy/pair_00001.png
train/clean/pair_00001.png
```

## 7. 这里最容易误会的地方

准备脚本不是“智能数据清洗器”。

它只能处理比较规整的命名。如果你的真实数据文件名完全不对应，比如：

```text
noisy/IMG_9281.png
clean/final_reference_scene_a.png
```

脚本可能匹配不到。这时不是模型问题，而是数据命名问题。需要先人工整理，或者以后再给脚本增加更明确的匹配规则。

还有一点要注意：`--size 512` 会做中心裁剪。它能统一尺寸，但不能修复原本就不对齐的 noisy/clean。如果两张图本来不是同一张图，裁剪后仍然不是一对。

## 8. 为什么先测 noisy 输入 baseline

准备好数据后，不要马上看模型训练结果。

第一步应该先测：

```text
noisy 本身和 clean 有多接近？
```

命令：

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

它会输出类似：

```text
config,noise,patch_size,val_size,input_psnr,input_ssim
...
```

这里的 input PSNR / input SSIM 是最重要的参照线。

| 指标 | 含义 |
|---|---|
| input PSNR | noisy 和 clean 的像素误差水平 |
| input SSIM | noisy 和 clean 的结构相似度 |

训练后的模型必须和这个 baseline 比。

如果模型输出的 PSNR / SSIM 没有超过 noisy 输入 baseline，那说明模型目前没有真正改善图片。它可能只是把图变糊了，或者数据配对有问题，或者训练还不够。

## 9. 为什么 Week 2 仍然用 DnCNN residual

Week 2 的重点是数据入口，所以模型继续用 Week 1 已经理解过的 DnCNN residual。

配置文件：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

关键配置：

| 配置 | 当前值 | 含义 |
|---|---:|---|
| `dataset` | `paired_image` | 使用真实 paired image dataset |
| `patch_size` | 128 | 每次训练从真实图里裁 patch |
| `train_size` | 1000 | 每轮抽取的训练 patch 数量 |
| `val_size` | 200 | 验证 patch 数量 |
| `model.name` | `dncnn` | 使用 DnCNN |
| `features` | 32 | 卷积特征通道数 |
| `depth` | 5 | 网络深度 |
| `residual` | true | 预测噪声残差，再从 noisy 中减掉 |
| `loss` | `mse` | 使用 L2 / MSE loss |
| `steps` | 500 | 先小步训练 |
| `batch_size` | 4 | 每步使用 4 个 patch |
| `val_every` | 100 | 每 100 step 做一次验证 |

为什么继续用它？

因为 Week 1 已经证明 DnCNN residual 在去噪任务上比 direct clean 更自然：

```text
direct clean：模型直接生成干净图
residual：模型只预测 noisy 里多出来的噪声
```

真实 paired RGB 的不确定因素已经很多了。Week 2 先固定模型，能让你更清楚地判断问题来自数据、训练还是指标。

## 10. Week 2 的完整执行流程

可以按这个顺序学习：

### 第一步：准备真实 paired RGB 小子集

目标是得到标准目录：

```text
datasets/sidd_tiny/train/noisy
datasets/sidd_tiny/train/clean
datasets/sidd_tiny/val/noisy
datasets/sidd_tiny/val/clean
```

看什么：

| 检查项 | 正常情况 |
|---|---|
| noisy / clean 文件数量 | train 和 val 内分别一致 |
| 文件名 | noisy 和 clean 都是 `pair_000xx.png` |
| 图片尺寸 | noisy 和 clean 一样 |
| 内容 | 两张图是同一场景 |

### 第二步：测 noisy baseline

目标是知道“不训练模型时，输入本身是什么水平”。

看什么：

| 情况 | 解读 |
|---|---|
| input PSNR 很低 | 噪声重，提升空间大 |
| input PSNR 很高 | 原图已经接近 clean，模型提升空间小 |
| input SSIM 很低 | 结构差异大，可能噪声重，也可能没对齐 |
| input SSIM 异常低 | 先怀疑配对或裁剪对齐 |

### 第三步：小步训练

命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

虽然脚本名字里有 `toy_rgb`，但它会根据配置里的：

```text
data.dataset: paired_image
```

切换到 paired image dataset。

这里先跑 500 step，不追求最终效果。它主要用来确认：

```text
真实数据 -> dataset -> model -> loss -> validation -> checkpoint -> visualization
```

这条链路是通的。

### 第四步：看训练产物

训练结果会输出到：

```text
runs/paired_rgb_sidd_tiny_dncnn_l2/
```

重点看三类东西：

| 文件 | 用途 |
|---|---|
| `metrics.csv` | 看 loss、val PSNR、val SSIM 是否整体变好 |
| checkpoint | 保存模型权重，方便后续继续训练或对比 |
| 三联图 | 直接看 noisy / output / clean 的视觉差异 |

三联图尤其重要。指标变好不代表视觉一定好，视觉好也需要指标辅助确认。

## 11. 结果应该怎么分析

Week 2 的结果建议按这个顺序看。

第一，模型是否超过 noisy baseline：

```text
val PSNR / val SSIM > input PSNR / input SSIM
```

如果没有超过，先别急着换模型。

第二，训练曲线是否正常：

| 现象 | 可能说明 |
|---|---|
| train loss 下降，val PSNR 上升 | 正常学习 |
| train loss 下降，val PSNR 不动 | 可能过拟合、配对问题、验证集太少 |
| train loss 不下降 | 学习率、数据、loss 或模型输入可能有问题 |
| val PSNR 忽高忽低 | 数据太少，或 patch 随机性较大 |

第三，看三联图：

| 观察 | 解读 |
|---|---|
| output 比 noisy 更干净，细节还在 | 方向正确 |
| output 很糊 | 可能过度平滑，MSE 常见现象 |
| output 颜色偏 | 数据归一化或配对可能要查 |
| output 和 clean 内容对不上 | 优先怀疑 noisy/clean 没配对 |

## 12. 常见失败排查

![Week 2 真实数据排错清单](figures/week2_real_data_debug_checklist.png)

### 找不到 paired 图片

先检查源目录里是否真的有图片，再检查 noisy 和 clean 是否能通过文件名对应起来。

如果外部数据命名太乱，先手动整理成：

```text
source_noisy/0001.png
source_clean/0001.png
```

再运行准备脚本。

### noisy 和 clean 数量不一致

数量不一致不一定立刻错误，但最终能匹配上的 pair 数量可能不够。

脚本会要求：

```text
matched pairs >= train-count + val-count
```

如果不够，就会报：

```text
Need N pairs, found M matched pairs.
```

这时要减少 `--train-count` / `--val-count`，或者补齐配对图片。

### shape mismatch

如果不使用 `--size`，noisy 和 clean 必须原始尺寸一致。

如果尺寸不同，可以先用：

```text
--size 512
```

统一中心裁剪。

但注意：统一尺寸不等于确认对齐。尺寸只是第一层检查。

### 指标不升反降

优先按这个顺序查：

1. noisy 和 clean 是不是同一场景；
2. noisy 和 clean 裁剪位置是否一致；
3. input baseline 是否已经很高；
4. 三联图里的 output 是否明显变糊；
5. patch size 是否太小，导致模型只能看局部；
6. 训练 step 是否太少。

不要第一反应就换大模型。真实数据问题没排干净前，大模型很容易把错误放大。

### output 过度平滑

这可能和 MSE / L2 loss 有关。MSE 倾向于平均化误差，所以有时会让输出更平滑。

但 Week 2 先不用急着改 loss。先确认模型至少能超过 baseline，再回到 Week 1 的 L1 / L2 对比思路，决定是否换成 L1 或混合 loss。

## 13. Week 2 学完后，你应该能回答

### Week 2 是干嘛的？

Week 2 是把 toy RGB 去噪迁移到真实 paired RGB 数据的入口周。它的重点不是追求最强模型，而是确认真实 noisy/clean 数据能被整理、读取、验证、训练和可视化。

### paired RGB 为什么是进入真实数据前的关键接口？

因为监督式去噪训练需要输入和答案：

```text
输入：noisy
答案：clean
```

如果没有 paired 数据，loss 就不知道模型输出应该靠近哪张 clean 图。paired RGB 先避开 RAW 和低光增强的复杂 ISP 细节，让你专注于真实图像恢复训练的基本接口。

### 为什么要统一成 train/noisy、train/clean、val/noisy、val/clean？

因为训练器需要稳定读取数据。目录统一后，模型训练就不依赖外部数据集原始的混乱命名。以后换数据，只要整理成同样结构，训练配置可以继续复用。

### 为什么要先测 noisy 输入 baseline？

baseline 是判断模型有没有用的最低参照。

如果 noisy 输入本身 PSNR 是 30 dB，而模型输出只有 28 dB，说明模型把图变差了。没有 baseline，你只看到一个训练后的数字，很难判断它到底好不好。

### 为什么 Week 2 仍然用 DnCNN residual？

因为 Week 2 的变量应该尽量少。DnCNN residual 已经在 Week 1 里被验证过，适合去噪，也容易解释。继续用它可以把注意力集中在真实数据入口，而不是同时怀疑模型、数据、loss 和配置。

### 为什么不直接上 RAW low-light？

RAW low-light 会引入更多问题：sensor Bayer 排列、黑电平、白平衡、颜色矩阵、曝光差异、动态范围等。你现在先把 RGB paired 训练跑通，后面进入 RAW 时才知道新增问题来自 RAW pipeline，而不是基础训练链路。

### 为什么要看三联图？

因为 PSNR / SSIM 是数字，三联图是视觉证据。

三联图通常是：

```text
noisy | output | clean
```

它能告诉你 output 是否真的更干净、细节是否还在、颜色是否偏、有没有错位。真实图像任务不能只看表格。

### Week 2 的通过标准是什么？

学完 Week 2 后，你至少应该能做到：

| 标准 | 说明 |
|---|---|
| 能解释 paired RGB | noisy 和 clean 是同场景、同尺寸、同对齐的一对 |
| 能准备小型真实子集 | 用脚本整理出标准 train/val 目录 |
| 能测 input baseline | 知道 noisy 输入本身的 PSNR / SSIM |
| 能跑小步训练 | 真实数据能进入模型、loss、validation |
| 能看训练产物 | 会读 `metrics.csv`、checkpoint、三联图 |
| 能判断是否有效 | 模型指标和视觉要超过 noisy baseline |
| 能排查常见错误 | 优先查配对、尺寸、对齐、baseline，而不是盲目换模型 |

## 14. Week 2 和后续 Week 的关系

Week 2 跑通后，后面才适合继续扩展：

| 后续方向 | 建议前提 |
|---|---|
| 更大的真实 RGB 子集 | 小子集已经稳定超过 baseline |
| 更长训练 | 500 step 曲线正常，视觉没有明显错误 |
| L1 / Charbonnier loss | MSE 输出过平滑时再对比 |
| 更强模型 | 数据入口确认无误后再上 |
| RAW denoise | RGB paired 流程已经清楚 |
| low-light enhancement | 能区分去噪、增亮、颜色恢复分别在解决什么 |

## 15. 本周总结

Week 2 看起来步骤少，是因为它不是模型结构课，而是数据入口课。

它真正建立的是这条能力：

```text
我能把真实 noisy/clean RGB 图片变成训练器能读的数据，
能先测输入 baseline，
能小步训练并生成 metrics、checkpoint、三联图，
还能判断模型是不是真的比 noisy 输入更好。
```

只要这条链路跑通，阶段二就不再只是 toy 实验，而是正式进入真实图像去噪实验。
