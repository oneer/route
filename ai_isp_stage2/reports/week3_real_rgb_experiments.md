# Week 3：真实 RGB 去噪小规模实验

Week 3 的目标不是马上上 RAW、SID 或大模型，而是把 Week 2 跑通的真实 paired RGB 数据入口，变成一套可以认真比较结果的小规模实验流程。

一句话概括：

```text
Week 2 证明真实 noisy/clean 数据能进训练器；
Week 3 要判断模型在真实 RGB 数据上是否稳定变好，以及哪些设置更值得继续。
```

## 0. 它和 Week 2 怎么接上

Week 2 的重点是数据入口：

```text
真实 noisy/clean 图片
  -> 统一配对
  -> 统一目录
  -> 测 input baseline
  -> 跑 500 step
  -> 确认 metrics / checkpoint / 三联图能生成
```

Week 3 在这个基础上继续问四个问题：

| 问题 | 为什么重要 |
|---|---|
| 训练更久是否稳定变好？ | 500 step 只能证明能跑，不足以说明趋势 |
| L1 和 L2 在真实数据上谁更适合？ | toy 数据上的结论不一定完全迁移到真实数据 |
| patch 64 和 128 在真实数据上怎么取舍？ | 真实图像纹理更复杂，速度和上下文都要重新看 |
| DnCNN 和 UNet 哪个更适合作为下一步 baseline？ | 后面进入更强模型前，需要一个可靠对照 |

所以 Week 3 不是重复 Week 2，而是从“能跑”进入“会比较、会分析、会决定下一步”。

## 1. Week 3 的输入和输出

输入仍然是 Week 2 准备好的真实 paired RGB 小子集：

```text
ai_isp_stage2/datasets/sidd_tiny/
  train/
    noisy/
    clean/
  val/
    noisy/
    clean/
```

训练输出会进入不同的 `runs/` 目录：

```text
ai_isp_stage2/runs/
  paired_rgb_sidd_tiny_dncnn_l2_2000/
  paired_rgb_sidd_tiny_dncnn_l1_2000/
  paired_rgb_sidd_tiny_dncnn_l2_patch64_2000/
  paired_rgb_sidd_tiny_unet_l1_1000/
```

每个实验都要看三类产物：

| 产物 | 看什么 |
|---|---|
| `metrics.csv` | train loss、val PSNR、val SSIM 是否稳定变化 |
| `checkpoints/best_psnr.pth` | 哪一步达到最好 PSNR |
| `vis/step_*.png` | output 是否真的比 noisy 更接近 clean |

## 2. 实验总览

Week 3 一共做四组核心实验。

![Week 3 真实 RGB 实验矩阵](figures/week3_real_rgb_experiment_matrix.png)

> 图说明：这张图把 Week3 的实验变量排成矩阵。读图时注意一次只改一个核心变量，比如 loss、patch size 或模型结构，这样结果变化才知道是谁造成的。

| 实验 | 配置 | 主要变量 | 目的 |
|---|---|---|---|
| A | `paired_rgb_sidd_tiny_dncnn_l2_2000.yaml` | 训练步数从 500 到 2000 | 看 DnCNN L2 长训练趋势 |
| B | `paired_rgb_sidd_tiny_dncnn_l1_2000.yaml` | loss 从 L2 改成 L1 | 比较真实数据上的 L1 / L2 差异 |
| C | `paired_rgb_sidd_tiny_dncnn_l2_patch64_2000.yaml` | patch 128 改成 patch 64 | 比较速度、显存、上下文 |
| D | `paired_rgb_sidd_tiny_unet_l1_1000.yaml` | 模型从 DnCNN 换成 UNet | 建立第二个模型 baseline |

注意：每次比较最好只改变一个主要变量。

例如比较 L1 / L2 时，模型、patch size、训练步数、数据 split 都保持一致。这样结果才容易解释。

### 2.1 Week 3 的实验纪律

Week 3 开始就要像做算法实验，而不是像试命令。每组实验都要遵守三条纪律：

```text
一组实验只问一个问题；
每次只改一个主要变量；
每个结论都必须同时有指标和图像证据。
```

如果一次同时改了模型、loss、patch size 和训练步数，最后即使结果变好，也很难回答：

```text
到底是哪个改变带来的提升？
```

所以 Week 3 的四组实验分别对应四个问题：

| 实验 | 只问什么问题 | 固定什么 |
|---|---|---|
| A 长训练 | 训练更久是否继续变好 | 模型、loss、patch、数据 |
| B L1/L2 | loss 改变是否影响指标和视觉 | 模型、patch、steps、数据 |
| C patch | patch size 是否影响上下文和速度 | 模型、loss、steps、数据 |
| D UNet | 换模型结构是否值得继续 | 数据和大致训练流程 |

其中 D 不是严格单变量，因为 UNet 当前是 direct output，而 DnCNN 是 residual denoise。报告里要明确这一点，不能把它说成完全公平的结构对比。

### 2.2 实验前检查清单

跑 Week 3 前，先检查：

| 检查项 | 为什么重要 |
|---|---|
| `datasets/sidd_tiny` 是否存在 | 没数据就不要跑训练 |
| train/val noisy-clean 数量是否一致 | 避免 pair 缺失 |
| input baseline 是否已记录 | 没 baseline 就不知道模型是否真的改进 |
| Week2 500 step 是否能生成三联图 | 确认训练链路可用 |
| 每个 config 的 output_dir 是否不同 | 避免覆盖上一次实验结果 |
| patch size 和 batch size 是否匹配显存 | 避免训练中途 OOM |

如果这些没有确认，Week 3 跑出来的数字很可能无法解释。

## 3. 第一步：重新确认 input baseline

Week 3 开始前，先重新测 noisy 输入 baseline。

命令：

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

记录：

| Dataset | Input PSNR | Input SSIM | 备注 |
|---|---:|---:|---|
| sidd_tiny val | 待填写 | 待填写 | noisy 输入本身水平 |

为什么要重新记？

因为 Week 3 所有模型结果都要和它比较：

```text
模型 val PSNR / SSIM 必须高于 input PSNR / SSIM，才算真的改善 noisy 输入。
```

如果某个模型训练后没有超过 input baseline，就算它能生成 checkpoint，也不能说它有效。

## 4. 实验 A：DnCNN L2 长训练

配置：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
```

命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
```

这个实验只是在 Week 2 的 DnCNN L2 基础上，把训练从 500 step 延长到 2000 step。

目的不是单纯“跑久一点”，而是观察：

| 观察项 | 正常情况 |
|---|---|
| train loss | 整体下降，后期可能趋于平稳 |
| val PSNR | 至少应该超过 input baseline，最好持续上升 |
| val SSIM | 不一定每次都单调，但整体不应越来越差 |
| 三联图 | output 应逐渐比 noisy 更干净 |

结果记录模板：

| Step | Train loss | Val PSNR | Val SSIM | 视觉观察 |
|---:|---:|---:|---:|---|
| 200 | 待填写 | 待填写 | 待填写 | 待填写 |
| 400 | 待填写 | 待填写 | 待填写 | 待填写 |
| 800 | 待填写 | 待填写 | 待填写 | 待填写 |
| 1200 | 待填写 | 待填写 | 待填写 | 待填写 |
| 1600 | 待填写 | 待填写 | 待填写 | 待填写 |
| 2000 | 待填写 | 待填写 | 待填写 | 待填写 |

怎么看这个实验？

如果 500 step 后指标还在明显上升，说明 Week 2 的训练只是刚起步，继续训练有意义。

如果 1000 step 以后指标不再上升，说明当前模型、数据量或 loss 可能已经到达小实验瓶颈。

如果 train loss 下降但 val PSNR 不升，优先怀疑：

- 数据太少导致过拟合；
- train / val 分布差异较大；
- noisy/clean 配对或 crop 仍有问题；
- MSE 让输出过度平滑。

## 5. 实验 B：DnCNN L1 和 L2 对比

L2 配置：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
```

L1 配置：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l1_2000.yaml
```

命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l1_2000.yaml
```

这组实验只改变 loss。

L2 / MSE：

```text
loss = mean((output - clean)^2)
```

L1：

```text
loss = mean(abs(output - clean))
```

真实数据上要重点看：

| 对比点 | L2 可能表现 | L1 可能表现 |
|---|---|---|
| PSNR | 更容易高 | 不一定最高 |
| 边缘和纹理 | 可能更平滑 | 可能更保守 |
| 异常噪点 | 惩罚更重 | 惩罚更线性 |
| 视觉质感 | 可能干净但糊 | 可能细节更稳 |

结果记录模板：

| Loss | Best step | Best val PSNR | Best val SSIM | 视觉结论 |
|---|---:|---:|---:|---|
| L2 / MSE | 待填写 | 待填写 | 待填写 | 待填写 |
| L1 | 待填写 | 待填写 | 待填写 | 待填写 |

结论不要只看 PSNR。

如果 L2 的 PSNR 高，但三联图里 output 明显糊，说明它可能在平均化细节。

如果 L1 的 PSNR 低一点，但边缘和纹理更自然，它也值得保留作为后续对照。

## 6. 实验 C：patch 64 和 patch 128 对比

patch 128 配置：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
```

patch 64 配置：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000.yaml
```

命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000.yaml
```

这组实验只改变 patch size。

patch size 的含义：

```text
每次训练不是把整张图输入模型，而是从真实图里裁一个小块。
```

patch 64：

- 更快；
- 更省显存；
- batch size 可以设大一点；
- 适合快速验证；
- 但上下文少，可能看不到更大结构。

patch 128：

- 上下文更多；
- 更适合纹理和局部结构恢复；
- 训练更慢；
- 更吃显存。

结果记录模板：

| Patch size | Batch size | Best val PSNR | Best val SSIM | 速度/显存观察 | 视觉结论 |
|---:|---:|---:|---:|---|---|
| 64 | 8 | 待填写 | 待填写 | 待填写 | 待填写 |
| 128 | 4 | 待填写 | 待填写 | 待填写 | 待填写 |

怎么判断？

如果 patch 64 和 128 指标差不多，但 patch 64 快很多，后续快速实验可以用 patch 64。

如果 patch 128 明显更好，说明真实数据需要更大上下文，后续正式实验优先用 patch 128。

## 7. 实验 D：UNet baseline

配置：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_unet_l1_1000.yaml
```

命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_unet_l1_1000.yaml
```

UNet 和 DnCNN 的思路不同。

DnCNN 更像局部卷积去噪器：

```text
noisy -> 多层卷积 -> 预测噪声或 clean
```

当前 DnCNN residual 配置是：

```text
noise_pred = DnCNN(noisy)
output = noisy - noise_pred
```

UNet 是 encoder-decoder：

```text
noisy
  -> encoder 下采样，提取更大范围上下文
  -> bottleneck 压缩表示
  -> decoder 上采样，恢复空间分辨率
  -> skip connection 把浅层细节接回来
  -> output
```

UNet 的关键概念：

| 概念 | 含义 |
|---|---|
| encoder | 逐步下采样，扩大感受野 |
| decoder | 逐步上采样，恢复图像大小 |
| bottleneck | 最低分辨率的高层特征 |
| skip connection | 把前面保留的细节直接送到后面 |
| bilinear upsample | 用插值上采样，减少棋盘格伪影 |

为什么 Week 3 才引入 UNet？

因为 Week 0-2 先要把训练基础、toy 去噪、真实数据入口跑稳。UNet 比 DnCNN 概念更多，如果太早引入，容易把模型结构和数据问题混在一起。

Week 3 引入它，是为了建立第二个真实 RGB baseline：

```text
如果 DnCNN 是局部残差去噪 baseline，
UNet 就是带多尺度上下文的图像恢复 baseline。
```

结果记录模板：

| Model | Loss | Steps | Best val PSNR | Best val SSIM | 视觉结论 |
|---|---|---:|---:|---:|---|
| DnCNN residual | L1 | 2000 | 待填写 | 待填写 | 待填写 |
| UNet | L1 | 1000 | 待填写 | 待填写 | 待填写 |

注意：UNet 这个配置目前是 direct output，不是 residual denoise。它直接输出去噪图：

```text
output = UNet(noisy)
loss = distance(output, clean)
```

所以比较时要记住：这里同时改变了模型结构和输出方式。它适合作为 baseline，但不是严格单变量对比。

## 8. 怎么读 `metrics.csv`

每个实验目录里都会有：

```text
runs/<experiment_name>/metrics.csv
```

你主要看三列：

| 列 | 含义 |
|---|---|
| `step` | 当前训练步 |
| `train_loss` | 当前训练误差 |
| `val_psnr` | 验证集 PSNR |
| `val_ssim` | 验证集 SSIM |

读法：

```text
先看 val_psnr / val_ssim 是否超过 input baseline；
再看它们是否随 step 整体提升；
最后结合三联图判断视觉是否真的变好。
```

常见情况：

| 现象 | 解读 |
|---|---|
| train loss 下降，val PSNR 上升 | 正常学习 |
| train loss 下降，val PSNR 停住 | 可能过拟合或模型容量不足 |
| val PSNR 上升，三联图变糊 | 指标和视觉出现分歧，需要保留视觉判断 |
| val SSIM 低但 PSNR 高 | 像素误差小，但结构可能恢复不好 |
| 指标低于 input baseline | 模型没有真正改善 noisy 输入 |

### 8.1 每个 run 都要做的小复盘

每跑完一个实验，不要只看最后一行指标。建议固定做一次小复盘：

| 问题 | 记录 |
|---|---|
| 这个 run 的 config 是什么 | 待填写 |
| 这个 run 只改变了哪个变量 | 待填写 |
| input baseline 是多少 | 待填写 |
| best PSNR 出现在第几步 | 待填写 |
| best SSIM 是否和 best PSNR 同一步 | 待填写 |
| 最后一步是否比 best step 变差 | 待填写 |
| train loss 是否持续下降 | 待填写 |
| val PSNR 是否超过 input baseline | 待填写 |
| 三联图里 output 是否更干净 | 待填写 |
| 有没有过平滑、偏色、错位 | 待填写 |

尤其要注意：

```text
best_psnr.pth 不一定是视觉最好的一步；
最后一步也不一定是指标最好的一步。
```

所以建议同时看：

```text
metrics.csv 里的 best step
vis/step_*.png 里的可视化趋势
```

如果 best PSNR 和最好看的三联图不一致，要在报告里写出来。这不是坏事，反而说明你在认真分析指标和视觉的分歧。

### 8.2 一个 run 的复盘写法示例

可以用下面这种句式：

```text
本实验使用 DnCNN residual + L2，训练 2000 step，主要变量是训练步数。
input baseline 为 ___ dB / ___ SSIM。
训练后 best PSNR 为 ___ dB，出现在 step ___，相比 input baseline 提升 ___ dB。
三联图显示 output 的平坦区噪声减少，但纹理区域略有平滑。
因此当前结论是：长训练有效，但后续需要比较 L1 或 Charbonnier 来检查视觉细节。
```

这比只写：

```text
PSNR 提升，效果变好。
```

要可靠得多。

## 9. 怎么读三联图

三联图一般是：

```text
noisy 输入 | output 模型输出 | clean 标准答案
```

看图时按这个顺序：

1. 先看 output 是否比 noisy 更干净；
2. 再看 output 是否保留 clean 的边缘；
3. 再看颜色是否偏；
4. 再看纹理是否被抹掉；
5. 最后看 output 有没有和 clean 对不齐。

如果 output 比 noisy 干净，但边缘变糊，说明模型可能在用平滑换指标。

如果 output 和 clean 内容明显错位，优先回到 Week 2 检查 paired 数据，而不是继续调模型。

### 9.1 三联图观察模板

每张三联图可以按下面表格记录：

| 区域 | noisy | output | clean | 判断 |
|---|---|---|---|---|
| 平坦区 | 待填写 | 待填写 | 待填写 | 噪声是否减少 |
| 边缘 | 待填写 | 待填写 | 待填写 | 是否变糊 |
| 纹理 | 待填写 | 待填写 | 待填写 | 是否被抹掉 |
| 暗部 | 待填写 | 待填写 | 待填写 | 是否残留噪声或偏色 |
| 高光 | 待填写 | 待填写 | 待填写 | 是否 clipping 或发灰 |

如果暂时没有手动 crop 工具，也可以先用肉眼在同一张三联图里找这些区域。关键是训练自己从“看起来还行”变成“具体哪里变好了、哪里变差了”。

### 9.2 真实 RGB 实验的常见视觉现象

| 现象 | 可能原因 | 下一步 |
|---|---|---|
| output 比 noisy 干净，但整体发糊 | L2/MSE 平均化、模型容量不足、patch 太小 | 比较 L1 / patch128 / UNet |
| output 颜色偏绿或偏红 | RGB/BGR、归一化、数据 pair 域不一致 | 查 dataset 读取和图片来源 |
| output 和 clean 边缘错开 | noisy/clean 未对齐或裁剪位置不同 | 回到 Week2 查 pair |
| 暗部噪声仍明显 | 真实噪声复杂、训练不足、loss 不敏感 | 增加数据、长训练、局部 crop |
| 纹理被当成噪声抹掉 | 模型无法区分细节和噪声 | 更大 patch、多尺度模型、视觉 loss 对照 |

## 10. Week 3 的最终结果表

跑完后建议把结果整理成一张表：

| 实验 | Config | Input baseline 是否超过 | Best val PSNR | Best val SSIM | 视觉结论 | 下一步建议 |
|---|---|---|---:|---:|---|---|
| A | DnCNN L2 2000 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| B | DnCNN L1 2000 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| C | DnCNN L2 patch64 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| D | UNet L1 1000 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |

这张表的作用不是装饰，而是帮你做决定：

```text
下一步该扩大数据，还是换模型，还是先修数据？
```

### 10.1 怎么从结果做决定

可以按下面这张决策表看：

| 观察到的结果 | 优先判断 | 下一步 |
|---|---|---|
| 所有模型都低于 input baseline | 当前训练没有真正改善输入 | 回到 Week2 查配对、裁剪、baseline |
| DnCNN L2 长训练持续上升 | 当前模型还没到瓶颈 | 继续长训练或扩大数据 |
| DnCNN L2 早早停住 | 当前配置可能到瓶颈 | 比较 L1、patch、UNet |
| L2 PSNR 高但图像糊 | 指标和视觉冲突 | 保留 L1/Charbonnier 对照 |
| L1 PSNR 低但边缘更自然 | 视觉可能更好 | 后续报告同时列 PSNR/SSIM/三联图 |
| patch128 明显好但很慢 | 上下文有价值 | 正式实验用 128，快速排查用 64 |
| patch64 接近 patch128 且快很多 | 小 patch 足够 | 先用 64 做更多 ablation |
| UNet 明显更好 | 多尺度结构有价值 | Week4/5 可继续 UNet/NAFNet-lite |
| UNet 不如 DnCNN | 当前数据量或训练设置不适合更复杂模型 | 先稳住 DnCNN baseline |

不要把“最佳 PSNR”当成唯一结论。Week 3 的真正产出应该是一句话决策：

```text
基于当前小子集，下一步最值得做的是 _____ ，因为指标显示 _____ ，三联图显示 _____ 。
```

例如：

```text
下一步先扩大真实 RGB 数据，而不是立刻上 NAFNet，
因为 DnCNN L2 已经超过 input baseline，但长训练曲线还没有明显饱和。
```

或者：

```text
下一步先回到 Week2 查数据，
因为所有模型都没有超过 noisy baseline，并且三联图里 output/clean 存在错位。
```

## 11. Week 3 的通过标准

学完 Week 3 后，你应该能独立解释：

### 为什么 Week 3 不直接上 RAW / SID？

因为当前刚刚接入真实 paired RGB。先把 RGB 小规模实验规范建立起来，后面进入 RAW 时才知道新增复杂度来自 RAW，而不是基础训练链路。

### 为什么要做长训练？

500 step 只能证明能跑，不能证明趋势。长训练能观察指标是否稳定提升、是否过拟合、是否达到瓶颈。

### 为什么要在真实数据上重新比较 L1 / L2？

toy 数据的噪声是合成的，真实数据的噪声、纹理、配对误差都更复杂。loss 在 toy 上的表现不能直接当成真实数据结论。

### 为什么 patch size 要重新比较？

真实图像有更复杂的纹理和结构。patch 太小可能缺上下文，patch 太大又会变慢、吃显存，所以需要重新测。

### UNet 和 DnCNN 的主要区别是什么？

DnCNN 是多层卷积去噪器，当前主要依靠 residual 学噪声。

UNet 是 encoder-decoder，多了下采样、上采样和 skip connection，能看到更大范围上下文，也能把浅层细节接回输出。

### 为什么不能只看 PSNR？

PSNR 衡量像素误差，但真实图像恢复还要看结构、边缘、颜色和纹理。PSNR 高但图像过平滑时，视觉上不一定更好。

### 怎么判断 Week 3 做完了？

至少满足：

| 标准 | 说明 |
|---|---|
| 已记录 input baseline | 知道 noisy 输入本身水平 |
| 至少一个模型超过 baseline | 证明模型真的改善图片 |
| 有 L1 / L2 对比结论 | 不只凭 toy 结果判断 loss |
| 有 patch size 对比结论 | 知道速度和效果取舍 |
| 有 DnCNN / UNet baseline | 后续换强模型时有参照 |
| 会读 metrics 和三联图 | 能解释数字和视觉差异 |
| 能决定下一步 | 扩数据、长训练、换模型或回头修数据 |

## 12. Week 3 之后做什么

Week 3 完成后，再根据结果选择方向。

| Week 3 结果 | 下一步 |
|---|---|
| DnCNN 已稳定超过 baseline | 扩大真实 RGB 数据子集 |
| L1 视觉更好 | 保留 L1 或尝试 Charbonnier loss |
| L2 PSNR 明显更好 | 正式指标实验可继续用 L2 |
| patch 128 明显更好 | 后续正式训练优先 patch 128 |
| UNet 明显更好 | Week 4 可以做 UNet 更长训练或更强模型 |
| 所有模型都不超过 baseline | 回到 Week 2 检查数据配对、裁剪、baseline |

更合理的后续路线是：

```text
Week 3: 真实 RGB 小规模实验
  -> Week 4: 建立 loss / metric / 可视化 / failure case 的评价体系
  -> Week 5: 复现 NAFNet-lite，和 DnCNN / UNet baseline 对比
  -> 后续: 再进入 RAW / low-light / SID
```

## 13. 本周总结

Week 3 的核心不是“多跑几个配置”，而是学会做真实图像恢复实验。

它真正要建立的是这套判断能力：

```text
我知道 input baseline 是多少；
我能让模型超过 baseline；
我能比较 loss、patch size 和模型结构；
我能读 metrics.csv；
我能看三联图；
我能决定下一步该扩数据、换模型，还是回头修数据。
```

如果这些能讲清楚，Week 3 就不是机械跑实验，而是从“真实数据能跑”进入“真实数据实验会分析”。

## 14. 本机 SIDD Tiny 真实数据短训实验

这次已经在真实 SIDD 小子集上跑完三组 300-step 短训，用来建立 Week3 的真实 RGB baseline。

共同设置：

```text
数据：SIDD Small sRGB
训练集：80 对 512x512 center crop
验证集：20 对 512x512 center crop
patch size：128
设备：CPU
训练步数：300
验证间隔：50 steps
```

input baseline：

| 输入 | PSNR | SSIM | 含义 |
|---|---:|---:|---|
| noisy image | 26.7302 | 0.52412 | 不经过模型时，noisy 与 clean 的差距 |

模型结果：

| Model | Config | Loss | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | 结论 |
|---|---|---|---:|---:|---:|---:|---|
| DnCNN residual | `paired_rgb_sidd_tiny_dncnn_l2_300.yaml` | L2/MSE | 32.7717 | 250 | 0.77100 | 300 | PSNR 最强，短训 baseline 最稳 |
| UNet | `paired_rgb_sidd_tiny_unet_l1_300.yaml` | L1 | 28.2856 | 300 | 0.85951 | 300 | SSIM 最高，但 PSNR 不如 DnCNN |
| NAFNet-lite | `paired_rgb_sidd_tiny_nafnet_lite_l1_300.yaml` | L1 | 26.8194 | 250 | 0.73509 | 300 | 刚超过 noisy baseline，短训还不充分 |

这张表要重点学会三件事：

1. `DnCNN` 虽然结构简单，但在这个 300-step CPU 短训里最稳，说明 baseline 不一定要复杂。
2. `UNet` 的 SSIM 高于 DnCNN，但 PSNR 低很多，说明不同指标看的是不同侧面。
3. `NAFNet-lite` 跑通不等于跑好，现代结构需要合适宽度、训练步数和调参。

本轮训练命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_300.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_unet_l1_300.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_300.yaml
```

实验产物：

```text
ai_isp_stage2/runs/paired_rgb_sidd_tiny_dncnn_l2_300
ai_isp_stage2/runs/paired_rgb_sidd_tiny_unet_l1_300
ai_isp_stage2/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_300
```

每个 run 里都有：

```text
metrics.csv
checkpoints/last.pth
checkpoints/best_psnr.pth
vis/step_0050.png ... step_0300.png
```

这些文件就是 Week3 学习的核心证据：指标曲线告诉你趋势，checkpoint 保存模型，三联图告诉你视觉上到底有没有变好。

## 15. 本机 SIDD Tiny 标准版实验

在 300-step 短训之后，又跑了一轮更接近标准设置的实验：

| Model | Config | Loss | Steps | Best PSNR | Best SSIM | 结论 |
|---|---|---|---:|---:|---:|---|
| DnCNN residual | `paired_rgb_sidd_tiny_dncnn_l2_2000.yaml` | L2/MSE | 2000 | 35.5356 | 0.88367 | 当前最强 baseline |
| UNet | `paired_rgb_sidd_tiny_unet_l1_1000.yaml` | L1 | 1000 | 30.4453 | 0.88003 | SSIM 接近 DnCNN，但 PSNR 低 |
| NAFNet-lite | `paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml` | L1 | 1000 | 33.3269 | 0.86223 | 比短训版大幅提升，说明 300 steps 不足 |

标准版和短训版对比：

| Model | 300-step Best PSNR | 标准版 Best PSNR | 300-step Best SSIM | 标准版 Best SSIM |
|---|---:|---:|---:|---:|
| DnCNN | 32.7717 | 35.5356 | 0.77100 | 0.88367 |
| UNet | 28.2856 | 30.4453 | 0.85951 | 0.88003 |
| NAFNet-lite | 26.8194 | 33.3269 | 0.73509 | 0.86223 |

这里能学到一个很关键的实验原则：

```text
短训只能说明“能不能跑、有没有学习趋势”；
标准训才更适合比较模型能力。
```

尤其是 NAFNet-lite：300-step 版本刚超过 noisy baseline，但 1000-step width=16 版本已经追到 33.3269 PSNR。这说明现代模型不能只看最小 smoke 结果，训练设置会极大影响结论。

### 15.1 标准训练怎么操作

完整操作顺序如下：

```bash
# 1. 准备 SIDD tiny 数据
python ai_isp_stage2/scripts/07_prepare_sidd_small_subset.py --source-root ai_isp_stage2/datasets/downloads/SIDD_Small_sRGB_Only/SIDD_Small_sRGB_Only/Data --output-dir ai_isp_stage2/datasets/sidd_tiny --train-count 80 --val-count 20 --crop-size 512

# 2. 检查 train / val 是否配对
python ai_isp_stage2/scripts/06_inspect_paired_dataset.py --noisy-dir ai_isp_stage2/datasets/sidd_tiny/train/noisy --clean-dir ai_isp_stage2/datasets/sidd_tiny/train/clean --output-dir ai_isp_stage2/reports/figures/week2_sidd_tiny_dataset_inspection --max-samples 8
python ai_isp_stage2/scripts/06_inspect_paired_dataset.py --noisy-dir ai_isp_stage2/datasets/sidd_tiny/val/noisy --clean-dir ai_isp_stage2/datasets/sidd_tiny/val/clean --output-dir ai_isp_stage2/reports/figures/week2_sidd_tiny_val_inspection --max-samples 8

# 3. 测 noisy baseline
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_300.yaml

# 4. 跑标准训练
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_unet_l1_1000.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml
```

不要跳过第 2 步。真实数据最常见的问题不是模型不够强，而是 noisy/clean 配错、裁剪不一致或路径写错。

### 15.2 训练代码里发生了什么

训练入口是：

```text
scripts/01_train_toy_rgb.py
  -> ai_isp.engine.train.train_from_config(config)
```

核心流程：

```text
读取 YAML config
  -> 根据 data.dataset 创建 PairedImageDenoiseDataset
  -> 根据 model.name 创建 DnCNN / UNet / NAFNet-lite
  -> 根据 train.loss 创建 L1Loss 或 MSELoss
  -> 循环读取 noisy / clean patch
  -> output = model(noisy)
  -> loss = criterion(output, clean)
  -> loss.backward()
  -> optimizer.step()
  -> 每 val_every steps 做 validation
  -> 写 metrics.csv、保存 checkpoint、保存三联图
```

`PairedImageDenoiseDataset` 每次返回：

```text
{
  "noisy": noisy_patch,
  "clean": clean_patch,
  "sigma": 0.0
}
```

这里 `sigma=0.0` 不是说真实数据没有噪声，而是说真实 paired RGB 数据没有一个人工设定的 Gaussian sigma。噪声已经存在于真实 noisy 图里。

### 15.3 为什么 DnCNN 这轮这么强

DnCNN 的任务设定非常适合去噪：

```text
模型预测 noise residual
clean = noisy - predicted_noise
```

这比直接生成整张 clean 图更容易，因为真实 noisy 和 clean 大部分内容相同，差异主要是噪声。标准版 DnCNN 跑到：

```text
Best PSNR = 35.5356
Best SSIM = 0.88367
```

说明它在这个 SIDD tiny split 上已经是很强的 baseline。

### 15.4 为什么 UNet SSIM 高但 PSNR 低

UNet 有 encoder-decoder 和 skip connection，更容易保留结构信息，所以 SSIM 很高：

```text
Best SSIM = 0.88003
```

但它的 PSNR 只有：

```text
Best PSNR = 30.4453
```

这说明它虽然结构相似度不错，但像素级颜色、纹理或局部残留误差仍然比较大。面试时不要说“UNet 更好”或“UNet 更差”，要说：

```text
UNet 在结构指标上接近 DnCNN，但像素误差明显更高。
```

### 15.5 Week3 面试题和参考回答

**Q1：为什么短训和标准训结论不同？**

短训主要验证训练管线能跑、loss 能下降、模型有学习趋势。标准训更接近模型能力比较。NAFNet-lite 在 300 steps 只有 `26.8194 PSNR`，但标准版到 `33.3269 PSNR`，说明短训不足会低估现代模型。

**Q2：为什么要固定同一个 SIDD split？**

如果每次换 train/val 数据，指标变化可能来自数据难度不同，而不是模型不同。公平比较要求同一数据 split、同一 patch size、相近训练设置。

**Q3：为什么 DnCNN 2000 step 的 last PSNR 低于 best PSNR？**

因为训练更久不一定让验证指标单调上升。DnCNN 在 step 1800 达到 `35.5356`，step 2000 变成 `34.7538`，说明后期可能有波动或轻微过拟合，所以要保存 `best_psnr.pth`，不能只看最后一步。

**Q4：如果只能选一个 baseline 写进简历，选哪个？**

选 DnCNN residual。它结构清楚、结果稳定、PSNR/SSIM 都强，而且能讲清 residual denoise 的动机。UNet 和 NAFNet-lite 可以作为后续模型对比。

## 16. Week 3 升级：自动模型对比卡与补充实验

新版阶段二路线要求 Week 3 不只列出几个训练结果，而是形成一张可复查的 model comparison table。它需要同时回答：

```text
哪个模型超过 noisy baseline？
哪个 loss 更适合当前 SIDD tiny？
patch 64 和 patch 128 有什么取舍？
短训结果和标准训练结果是否一致？
参数量和 checkpoint 大小是否合理？
```

为此新增脚本：

```text
ai_isp_stage2/scripts/15_export_week3_model_comparison.py
```

运行命令：

```bash
python ai_isp_stage2/scripts/15_export_week3_model_comparison.py
```

输出文件：

```text
ai_isp_stage2/reports/figures/week3_model_comparison/week3_model_comparison.csv
ai_isp_stage2/reports/figures/week3_model_comparison/week3_model_comparison.md
```

同时补跑了原 Week 3 设计里缺失的两组实验：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l1_2000.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000.yaml
```

### 16.1 完整 Week 3 对比表

input noisy baseline：

```text
PSNR = 26.7302
SSIM = 0.52412
```

自动导出的模型对比结果：

| Group | Run | Model | Loss | Residual | Patch | Steps | Params | Checkpoint MB | Best PSNR | Best SSIM | PSNR gain | SSIM gain |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| short_300 | `paired_rgb_sidd_tiny_dncnn_l2_300` | dncnn | mse | true | 128 | 300 | 29507 | 0.351 | 32.7717@250 | 0.77100@300 | 6.0415 | 0.24688 |
| short_300 | `paired_rgb_sidd_tiny_unet_l1_300` | unet | l1 | false | 128 | 300 | 118307 | 1.380 | 28.2856@300 | 0.85951@300 | 1.5554 | 0.33539 |
| short_300 | `paired_rgb_sidd_tiny_nafnet_lite_l1_300` | nafnet_lite | l1 | false | 128 | 300 | 19995 | 0.343 | 26.8194@250 | 0.73509@300 | 0.0892 | 0.21097 |
| standard | `paired_rgb_sidd_tiny_dncnn_l2_2000` | dncnn | mse | true | 128 | 2000 | 29507 | 0.351 | 35.5356@1800 | 0.88367@1800 | 8.8054 | 0.35955 |
| loss_ablation | `paired_rgb_sidd_tiny_dncnn_l1_2000` | dncnn | l1 | true | 128 | 2000 | 29507 | 0.351 | 35.6334@2000 | 0.88839@1800 | 8.9032 | 0.36427 |
| patch_ablation | `paired_rgb_sidd_tiny_dncnn_l2_patch64_2000` | dncnn | mse | true | 64 | 2000 | 29507 | 0.351 | 35.2304@1600 | 0.88455@1800 | 8.5002 | 0.36043 |
| standard | `paired_rgb_sidd_tiny_unet_l1_1000` | unet | l1 | false | 128 | 1000 | 118307 | 1.380 | 30.4453@1000 | 0.88003@1000 | 3.7151 | 0.35591 |
| standard | `paired_rgb_sidd_tiny_nafnet_lite_l1_1000` | nafnet_lite | l1 | false | 128 | 1000 | 104307 | 1.329 | 33.3269@1000 | 0.86223@1000 | 6.5967 | 0.33811 |

### 16.2 新增实验结论

**DnCNN L1 vs L2：**

在同样 2000 step、patch 128、DnCNN residual 设置下，L1 略高于 L2：

```text
DnCNN L2: 35.5356 PSNR / 0.88367 SSIM
DnCNN L1: 35.6334 PSNR / 0.88839 SSIM
```

这说明在当前 SIDD tiny split 上，L1 不只是视觉对照，也能取得略好的 PSNR/SSIM。后续正式 baseline 可以优先保留 DnCNN L1 和 DnCNN L2 两条线，而不是只凭习惯选择 MSE。

**patch 64 vs patch 128：**

DnCNN L2 patch64 的结果：

```text
patch64: 35.2304 PSNR / 0.88455 SSIM
patch128: 35.5356 PSNR / 0.88367 SSIM
```

patch64 的 PSNR 略低，但 SSIM 基本持平。这说明小 patch 可以作为快速实验配置；如果追求最高 PSNR，当前仍优先用 patch128。

**短训 vs 标准训练：**

300-step 只能判断模型能不能学，不能直接代表模型能力。最明显的是 NAFNet-lite：

```text
300-step: 26.8194 PSNR
1000-step: 33.3269 PSNR
```

所以面试时不能说“NAFNet-lite 不行”，只能说：

```text
在 300-step smoke test 下 NAFNet-lite 尚未充分收敛；
标准训练后明显提升，但在当前 tiny split 上仍低于 DnCNN residual。
```

### 16.3 当前 Week 3 是否达标

按新版学习路线，Week 3 现在已经满足主要要求：

| 要求 | 当前状态 |
|---|---|
| 至少一个模型超过 input baseline | 已满足，所有正式 run 都超过 |
| DnCNN / UNet / NAFNet-lite 对比 | 已完成 |
| L1 / L2 对比 | 已补跑 DnCNN L1 2000 |
| patch 64 / 128 对比 | 已补跑 DnCNN L2 patch64 2000 |
| 参数量和 checkpoint 大小 | 已由对比脚本导出 |
| best step 和 last step 区分 | 已由 `metrics.csv` 和对比表体现 |
| 下一步判断 | DnCNN residual 是当前最稳 baseline，NAFNet-lite 保留为现代结构对照 |

下一步不建议继续盲目堆新模型。更合理的路线是进入 Week 4，把这些结果转成统一评估、error map、triplet 和 failure case 分析。
