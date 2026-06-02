# Week 5：NAFNet / 轻量图像恢复模型复现

Week 5 的目标不是盲目追 SOTA，而是从 DnCNN / UNet baseline 过渡到现代图像恢复模型，理解一个更强 baseline 为什么有效。

本周建议先做 `NAFNet-lite`，也就是学习 NAFNet 的核心思想，但保留小模型、小数据、小步数，避免一开始被工程规模拖住。

## 1. 它和 Week 3/4 怎么接上

Week 3 做的是：

```text
真实 paired RGB 小实验
  -> DnCNN 长训练
  -> L1 / L2
  -> patch size
  -> UNet baseline
```

Week 4 做的是：

```text
用 loss / metric / 三联图 / failure case 判断模型到底好不好
```

Week 5 才适合问：

```text
如果 DnCNN / UNet 已经成为可靠 baseline，现代轻量图像恢复模型能不能更好？
```

所以 Week 5 不是重新开始，而是基于前面建立的实验纪律：

```text
同一数据、同一指标、同一可视化方式，对比一个更强模型。
```

## 2. NAFNet 是什么

NAFNet 是图像恢复里的一个现代 baseline。名字里的 NAF 可以理解成：

```text
Nonlinear Activation Free
```

它的核心特点不是“没有任何非线性”，而是不用传统 CNN 里常见的 ReLU/GELU 这类激活函数，改用更简单的门控结构。

本阶段先记住三件事：

| 概念 | 作用 | 先怎么理解 |
|---|---|---|
| SimpleGate | 把特征一分为二，相乘 | 用乘法产生非线性 |
| SCA | Simplified Channel Attention | 让网络重新加权不同通道 |
| U-shaped backbone | 类似 UNet 的多尺度结构 | 同时看局部细节和大范围上下文 |

## 3. 它和 DnCNN / UNet 有什么关系

| 模型 | 思路 | 优点 | 局限 |
|---|---|---|---|
| DnCNN | 多层卷积，常用 residual denoise | 简单、稳定、容易解释 | 多尺度上下文弱 |
| UNet | encoder-decoder + skip connection | 能看更大范围，结构直观 | 参数和结构更复杂 |
| NAFNet-lite | 多尺度 + gate + channel attention | 更现代、更适合恢复任务 | 概念更多，调试成本更高 |

可以这样理解：

```text
DnCNN 学局部去噪；
UNet 学多尺度恢复；
NAFNet-lite 在 UNet 多尺度基础上，用更现代的 block 提升表达能力。
```

## 4. 为什么不直接跑官方完整 NAFNet

当前阶段先不建议一上来完整复现官方大模型，原因是：

- 数据还只是小型真实 RGB 子集；
- 训练资源和时间有限；
- 你现在更需要理解模型结构，而不是刷榜；
- 大模型结果不好时，很难判断是数据、实现、训练时长还是模型设置问题。

所以本周目标应该是：

```text
实现一个能跑通的 NAFNet-lite block；
在同一 sidd_tiny 数据上和 DnCNN / UNet 做小规模对比；
能解释结果，而不是只贴分数。
```

### 4.1 怎么读 NAFNet 论文和官方代码

读论文不要从所有实验表开始。建议按这个顺序：

| 顺序 | 看什么 | 目的 |
|---|---|---|
| 1 | Abstract / Introduction | 知道它想解决什么问题 |
| 2 | NAFBlock 结构图 | 抓住 SimpleGate、SCA、残差连接 |
| 3 | Ablation 表 | 看作者证明哪些模块有用 |
| 4 | SIDD / GoPro 设置 | 理解它在哪些任务上验证 |
| 5 | 官方代码的 model 文件 | 对照论文结构，不急着读训练框架 |

官方 repo 也不要一上来读训练入口。优先找：

```text
model definition
NAFBlock
SimpleGate
network width / depth config
input/output shape
```

训练脚本、分布式、日志、EMA、scheduler 可以先略读。当前阶段真正要复现的是模型思想，不是完整工程体系。

读完后要能用自己的话回答：

```text
NAFNet 为什么不用 ReLU/GELU？
SimpleGate 具体怎么产生非线性？
SCA 为什么比复杂 attention 更轻？
它和 UNet 的共同点和不同点是什么？
```

## 5. NAFBlock 最小理解

一个简化 NAFBlock 可以先理解成：

```text
input
  -> normalization
  -> 1x1 conv 扩通道
  -> 3x3 depthwise conv
  -> SimpleGate
  -> channel attention
  -> 1x1 conv 回到原通道
  -> residual add
```

### 5.1 SimpleGate

SimpleGate 的形式可以写成：

```text
x1, x2 = split(x)
out = x1 * x2
```

它和 ReLU 的区别：

| 对比 | ReLU | SimpleGate |
|---|---|---|
| 形式 | `max(0, x)` | `x1 * x2` |
| 参数 | 无 | 无 |
| 非线性来源 | 截断负值 | 特征相乘 |
| 直觉 | 负响应关掉 | 一个特征调制另一个特征 |

所以 NAFNet 说“不用激活函数”，不是网络完全线性，而是用乘法 gate 提供非线性。

### 5.2 Channel Attention

channel attention 解决的问题是：

```text
不同特征通道的重要性不一样。
```

直觉上：

- 有些通道可能更关注噪声；
- 有些通道可能更关注边缘；
- 有些通道可能更关注颜色；
- attention 让网络自己调整这些通道的权重。

### 5.3 Residual Add

NAFBlock 里通常也有 residual：

```text
output = input + block(input)
```

它和 DnCNN residual denoise 不是完全同一层意思。

| 名字 | 发生在哪里 | 含义 |
|---|---|---|
| DnCNN residual denoise | 整个模型输出 | `output = noisy - noise_pred` |
| block residual add | 模型内部 block | `feature_out = feature_in + delta` |

一个是图像任务输出的残差，一个是网络内部特征的残差连接。

## 6. 本周推荐实现范围

最小可行版本：

```text
models/nafnet_lite.py
  -> SimpleGate
  -> NAFBlock
  -> NAFNetLite
```

不急着做：

- 完整官方训练策略；
- 大规模 SIDD 训练；
- EMA；
- cosine scheduler；
- 混合精度；
- 分布式训练；
- Restormer 对比。

先跑通：

```text
paired RGB input
  -> NAFNet-lite
  -> loss
  -> metrics.csv
  -> noisy/output/clean
```

### 6.1 推荐代码骨架

建议先按下面结构实现，不要一开始就追官方完整工程：

```text
ai_isp/models/nafnet_lite.py
  SimpleGate
  LayerNorm2d 或简化 norm
  NAFBlock
  NAFNetLite
```

最小伪代码：

```python
class SimpleGate(nn.Module):
    def forward(self, x):
        x1, x2 = x.chunk(2, dim=1)
        return x1 * x2

class NAFBlock(nn.Module):
    def forward(self, x):
        identity = x
        y = norm(x)
        y = conv1x1_expand(y)
        y = depthwise_conv3x3(y)
        y = simple_gate(y)
        y = channel_attention(y)
        y = conv1x1_project(y)
        return identity + beta * y
```

这里的 `beta` 可以先理解成残差分支的缩放系数。为了简单，第一版可以直接：

```python
return identity + y
```

等最小版本跑通后，再补可学习缩放。

### 6.2 最小实现不要同时引入太多东西

建议分三步做：

| 步骤 | 加什么 | 验证 |
|---|---|---|
| v0 | 普通 Conv block | 确认模型能训练，输出正常 |
| v1 | SimpleGate | 确认通道数、split、乘法没有 shape 错 |
| v2 | Channel Attention | 确认 attention 输出 shape 和数值范围合理 |
| v3 | U-shaped 多尺度 | 确认 down/up 后尺寸能对齐 |

如果一上来直接写完整 NAFNet-lite，报错时很难知道是 gate、attention、downsample、upsample 还是 skip connection 的问题。

### 6.3 shape 检查点

实现时最容易错的是通道数和空间尺寸。

建议每个 block 先用假数据检查：

```python
x = torch.randn(2, 32, 64, 64)
y = block(x)
assert y.shape == x.shape
```

如果是完整模型：

```python
x = torch.randn(2, 3, 128, 128)
y = model(x)
assert y.shape == x.shape
```

图像恢复模型的基本要求是：

```text
input:  [B, 3, H, W]
output: [B, 3, H, W]
```

否则就不能和 clean 直接算 loss。

## 7. 实验设计

为了公平，先用 Week3 已有 baseline 作为对照：

| 实验 | 模型 | Loss | 数据 | 目的 |
|---|---|---|---|---|
| A | DnCNN residual | L1 或 L2 | sidd_tiny | 局部卷积 baseline |
| B | UNet | L1 | sidd_tiny | 多尺度 baseline |
| C | NAFNet-lite | L1 或 Charbonnier | sidd_tiny | 现代恢复 block baseline |

第一轮建议不要同时改 loss：

```text
先固定 L1；
模型换成 DnCNN / UNet / NAFNet-lite；
比较指标和三联图。
```

如果第一轮 NAFNet-lite 能跑通，再考虑 Charbonnier 或更长训练。

### 7.1 推荐 ablation 顺序

不要只跑一个 NAFNet-lite 然后和 DnCNN 比。建议按下面顺序：

| Ablation | 目的 | 结论要回答 |
|---|---|---|
| DnCNN baseline | 保留局部卷积参照 | 轻量模型至少要超过或接近它 |
| UNet baseline | 保留多尺度参照 | 多尺度结构是否有帮助 |
| NAFNet-lite v0 | 确认新模型管线能跑 | 新模型是否能正常收敛 |
| NAFNet-lite + SimpleGate | 单独看 gate 价值 | gate 是否改善指标或视觉 |
| NAFNet-lite + SCA | 单独看 channel attention | 通道重标定是否有帮助 |
| NAFNet-lite longer | 排除训练不足 | 结果差是否只是训练步数不够 |

每次 ablation 只回答一个问题。不要同时把模型变深、loss 改掉、patch 变大，否则无法解释。

### 7.2 和 DnCNN / UNet 对比时要公平

至少固定：

```text
同一数据 split
同一 patch size
相近训练 steps
同一 loss 或明确说明不同
同一 input baseline
同一可视化样本
```

如果 NAFNet-lite 的参数量明显大于 DnCNN，也要记录，因为性能提升可能来自更大模型，而不只是结构更好。

建议记录：

```text
参数量
训练时间
显存占用
best PSNR / SSIM
三联图视觉结论
```

## 8. 结果记录模板

| Model | Params | Loss | Steps | Patch | Best PSNR | Best SSIM | 视觉结论 | 下一步 |
|---|---:|---|---:|---:|---:|---:|---|---|
| DnCNN | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| UNet | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| NAFNet-lite | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |

视觉结论要写具体：

```text
不是“更好”，而是“暗部噪声更少，但边缘略糊”。
不是“差不多”，而是“PSNR 接近，但 NAFNet-lite 纹理保留更好/更差”。
```

## 9. 失败时先查什么

| 现象 | 优先检查 |
|---|---|
| loss 不下降 | forward 输出范围、loss、学习率、数据是否正常 |
| output 全黑/全白 | 最后一层输出、clamp、初始化、学习率 |
| 显存不够 | patch size、batch size、模型宽度 |
| PSNR 不如 DnCNN | 训练步数是否太少、模型是否过大、小数据是否不够 |
| 三联图错位 | 回到 Week2 查数据 |
| 指标高但视觉糊 | 回到 Week4 做 crop / failure analysis |

不要一失败就继续堆复杂模块。先让最小版本可解释地跑通。

## 10. 本仓库已实现内容

这一周已经不只是学习计划，仓库里已经加入了一个可以训练的 `NAFNet-lite` 最小版本。

对应文件：

| 文件 | 作用 |
|---|---|
| `ai_isp/models/nafnet_lite.py` | 实现 `SimpleGate`、`LayerNorm2d`、`NAFBlock`、`NAFNetLite` |
| `ai_isp/models/__init__.py` | 把 `nafnet_lite` 注册进 `build_model` |
| `configs/paired_rgb_smoke_nafnet_lite_l1.yaml` | smoke 数据上的 NAFNet-lite 快速训练配置 |
| `configs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml` | 真实 paired RGB 小子集上的 NAFNet-lite 训练配置 |
| `scripts/05_evaluate_runs.py` | 自动汇总多个 run 的 PSNR / SSIM、三联图和 error map |

模型输出已经做过 shape 检查：

```text
input : torch.Size([2, 3, 128, 128])
output: torch.Size([2, 3, 128, 128])
```

这说明它可以直接接入当前训练框架，和 clean 图计算 loss。

## 11. Smoke 结果

在 smoke paired RGB 数据上，已经完成一轮 NAFNet-lite 快速训练，并用 Week4 的评估脚本和 DnCNN smoke baseline 做了对比。

| Run | Model | Loss | Steps | Patch | Best PSNR | Best SSIM | 结论 |
|---|---|---|---:|---:|---:|---:|---|
| noisy input baseline | 无模型 | 无 | 0 | - | 22.1273 | 0.28203 | 原始 noisy 图的参考线 |
| `paired_rgb_smoke_dncnn_l2` | DnCNN residual | L2/MSE | 120 | 128 | 32.9687 | 0.89384 | smoke 数据上收敛很好 |
| `paired_rgb_smoke_nafnet_lite_l1` | NAFNet-lite | L1 | 80 | 128 | 25.2235 | 0.62806 | 模型管线跑通，但还没充分训练和调参 |

这组结果不能说明“DnCNN 一定比 NAFNet-lite 强”。它只能说明：

```text
当前这个小 NAFNet-lite 配置已经能学习；
但是在 80 steps、width=8、L1、很小 smoke 数据上，还没有追上已经跑到 120 steps 的 DnCNN baseline。
```

下一步如果要公平比较，应该固定：

```text
同一数据 split
同一 patch size
相近训练 steps
相同或明确记录的 loss
同一评估脚本
同一组可视化样本
```

本轮自动评估产物：

| 产物 | 路径 |
|---|---|
| 指标汇总 | `reports/figures/week4_smoke_eval/metrics_summary.csv` |
| 指标曲线 | `reports/figures/week4_smoke_eval/metrics_plot.png` |
| 三联图对比 | `reports/figures/week4_smoke_eval/triplet_contact_sheet.png` |
| error map | `reports/figures/week4_smoke_eval/error_maps/` |
| markdown 结果 | `reports/week4_smoke_eval_results.md` |

## 12. 怎么运行

先跑 smoke 版，确认模型和评估脚本都正常：

```bash
python ai_isp_stage2/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_smoke_nafnet_lite_l1.yaml
python ai_isp_stage2/scripts/05_evaluate_runs.py --runs ai_isp_stage2/runs/paired_rgb_smoke_dncnn_l2 ai_isp_stage2/runs/paired_rgb_smoke_nafnet_lite_l1 --output-dir ai_isp_stage2/reports/figures/week4_smoke_eval --report-md ai_isp_stage2/reports/week4_smoke_eval_results.md --title "Week 4 Smoke Evaluation Results"
```

再跑真实 paired RGB 小子集版本：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml
```

如果真实数据集还没准备好，先回到 Week2，用 `04_prepare_paired_rgb_subset.py` 建立 `datasets/sidd_tiny`。

## 13. 面试复述

学完 Week5 后，你应该能这样讲：

```text
我先用 DnCNN residual 和 UNet 建立真实 RGB 去噪 baseline，
再实现一个 NAFNet-lite，重点学习 SimpleGate、通道注意力和多尺度恢复结构。
我没有直接追官方大模型，而是在同一小型 paired RGB 数据上比较 PSNR、SSIM 和三联图，
分析它相对 DnCNN/UNet 是否真的改善纹理、边缘和噪声。
```

## 14. 通过标准

学完 Week5 后，至少能回答：

1. NAFNet 和 UNet / DnCNN 的关系是什么；
2. SimpleGate 为什么能提供非线性；
3. NAFNet 说不用传统激活函数是什么意思；
4. channel attention 在图像恢复里解决什么问题；
5. block 内部 residual 和 DnCNN residual denoise 有什么区别；
6. 为什么先做 NAFNet-lite，而不是直接复现完整官方模型；
7. 如果 NAFNet-lite 不如 DnCNN，应该怎么分析。

一句话总结：

```text
Week5 的目标是从“会用基础 CNN baseline”升级到“能理解并复现一个现代轻量图像恢复 block”。
```
