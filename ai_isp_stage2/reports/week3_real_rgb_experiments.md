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

| 实验 | 配置 | 主要变量 | 目的 |
|---|---|---|---|
| A | `paired_rgb_sidd_tiny_dncnn_l2_2000.yaml` | 训练步数从 500 到 2000 | 看 DnCNN L2 长训练趋势 |
| B | `paired_rgb_sidd_tiny_dncnn_l1_2000.yaml` | loss 从 L2 改成 L1 | 比较真实数据上的 L1 / L2 差异 |
| C | `paired_rgb_sidd_tiny_dncnn_l2_patch64_2000.yaml` | patch 128 改成 patch 64 | 比较速度、显存、上下文 |
| D | `paired_rgb_sidd_tiny_unet_l1_1000.yaml` | 模型从 DnCNN 换成 UNet | 建立第二个模型 baseline |

注意：每次比较最好只改变一个主要变量。

例如比较 L1 / L2 时，模型、patch size、训练步数、数据 split 都保持一致。这样结果才容易解释。

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
  -> Week 4: 扩大真实 RGB 数据 + 更强模型或更长训练
  -> Week 5: 再进入 RAW / low-light / SID
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
