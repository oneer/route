# Week 2：真实成对 RGB 数据入口

Week 2 的目标是从 toy RGB 去噪走向真实成对 RGB 数据。

这里先不碰 RAW、SID、复杂低光增强，也不急着上 NAFNet。当前只做一件事：

```text
把真实 noisy/clean RGB 图片整理成训练器能读取的小型数据集。
```

## 1. 为什么 Week 2 先做数据整理

Week 1 已经证明训练链路能工作：

```text
dataset -> model -> loss -> validation -> checkpoint -> visualization
```

![Week 2 paired RGB 数据管线](figures/week2_paired_rgb_data_pipeline.png)

如果直接上真实数据，最容易乱的是数据格式，而不是模型。

所以 Week 2 先固定一个简单规范：

```text
train/noisy/pair_00001.png <-> train/clean/pair_00001.png
val/noisy/pair_00001.png   <-> val/clean/pair_00001.png
```

只要文件能这样配对，现有训练代码就能继续用。

## 2. 目标目录

准备后的数据放在：

```text
ai_isp_stage2/datasets/sidd_tiny/
  train/
    noisy/
    clean/
  val/
    noisy/
    clean/
```

注意：真实数据一般不要提交进 git。这里只提交准备脚本和配置。

## 3. 准备脚本

脚本：

```text
ai_isp_stage2/scripts/04_prepare_paired_rgb_subset.py
```

用途：从外部 noisy/clean 源目录中抽取小子集，统一改名并分成 train/val。

命令模板：

```bash
python ai_isp_stage2/scripts/04_prepare_paired_rgb_subset.py --source-noisy-dir path/to/noisy --source-clean-dir path/to/clean --output-dir ai_isp_stage2/datasets/sidd_tiny --train-count 80 --val-count 20 --size 512
```

脚本会尝试匹配类似命名：

```text
NOISY_SRGB_0001.jpg <-> GT_SRGB_0001.jpg
```

并输出：

```text
pair_00001.png
```

## 4. 先测输入 baseline

准备好数据后，先不要马上看训练结果。先测 noisy 输入本身有多差。

命令：

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

你要记录：

| 项目 | 含义 |
|---|---|
| input PSNR | noisy 和 clean 的像素误差水平 |
| input SSIM | noisy 和 clean 的结构相似度 |

这个 baseline 是后面判断模型是否有用的最低参照。

如果模型训练后的 PSNR / SSIM 没有超过 noisy 输入 baseline，说明模型没有真正改善图片。

## 5. 小步训练

配置：

```text
ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

训练命令：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

默认设置：

| 项目 | 值 |
|---|---:|
| model | DnCNN residual |
| loss | L2 / MSE |
| patch size | 128 |
| train size | 1000 |
| val size | 200 |
| steps | 500 |
| batch size | 4 |

## 6. 怎么判断 Week 2 成功

Week 2 的成功标准不是“模型很强”，而是下面几件事成立：

1. 外部 noisy/clean 图片能整理成统一目录；
2. `02_measure_noise_baseline.py` 能正常读取并输出 input PSNR/SSIM；
3. 训练能跑到第一次 validation；
4. `metrics.csv`、checkpoint、三联图都能生成；
5. 模型输出指标高于 noisy 输入 baseline；
6. 可视化里 output 确实比 noisy 更接近 clean。

## 7. 如果失败，先查什么

![Week 2 真实数据排错清单](figures/week2_real_data_debug_checklist.png)

### 找不到 paired 图片

检查 noisy 和 clean 文件名是否能匹配。当前数据集要求最终文件名一致：

```text
noisy/pair_00001.png
clean/pair_00001.png
```

### Shape mismatch

说明 noisy 和 clean 尺寸不一致。可以用准备脚本的 `--size 512` 统一裁剪。

### 指标不升反降

先看三件事：

- noisy 和 clean 是否真的配对；
- crop 是否对齐；
- input baseline 是否已经很高，导致提升空间很小。

### 图像过度平滑

可能是 loss、patch size、模型容量或训练步数的问题。先不要急着换大模型，先确认 paired 数据是否正确。

## 8. Week 2 之后再考虑什么

当 SIDD-style 小子集跑通后，再考虑：

- 更大的真实 RGB 子集；
- 更严格的 train/val split；
- 更强的图像恢复模型；
- RAW denoise；
- low-light enhancement；
- SID / SIDD / NAFNet 等更正式的数据和模型路线。

但在 Week 2，没有必要提前做这些。

## 9. 本周总结

Week 2 的核心不是模型，而是数据入口：

```text
真实 noisy/clean 图片 -> 统一 paired 文件夹 -> baseline -> 小步训练 -> 可视化检查
```

这一周完成后，阶段二就从 toy 实验正式过渡到真实 RGB 去噪实验。
