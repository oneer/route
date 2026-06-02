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

## 13. 真实 SIDD Tiny 结果

这次已经在真实 SIDD Tiny 子集上跑了一个 CPU 友好的 `NAFNet-lite` 短训版本：

```text
config: paired_rgb_sidd_tiny_nafnet_lite_l1_300.yaml
width: 8
middle_blocks: 1
steps: 300
loss: L1
patch size: 128
```

对比结果：

| Model | Loss | Steps | Best PSNR | Best SSIM | 观察 |
|---|---|---:|---:|---:|---|
| noisy input baseline | 无 | 0 | 26.7302 | 0.52412 | 原始 noisy 水平 |
| DnCNN residual | L2/MSE | 300 | 32.7717 | 0.77100 | 短训最稳，PSNR 最高 |
| UNet | L1 | 300 | 28.2856 | 0.85951 | SSIM 最高，但像素误差更大 |
| NAFNet-lite | L1 | 300 | 26.8194 | 0.73509 | 略高于 noisy baseline，但还没充分训练 |

![SIDD tiny NAFNet 对比图](figures/week4_sidd_tiny_eval/triplet_contact_sheet.png)

> 图说明：这张图里 NAFNet-lite 的 output 比 noisy 有改善，但离 clean 仍有差距。这个结果说明模型和训练管线已经跑通，但不能说明 NAFNet-lite 的最终能力；当前设置是 CPU 轻量短训，不是完整 NAFNet 复现。

### 13.1 为什么 NAFNet-lite 这次没有赢？

不要把这次结果理解成“NAFNet 不如 DnCNN”。更准确的分析是：

| 原因 | 解释 |
|---|---|
| 训练太短 | 只有 300 steps，现代 block 可能还没充分收敛 |
| 模型太窄 | 为了 CPU 速度，`width=8`，表达能力被压低 |
| 配置不完全公平 | DnCNN 用 L2/MSE，NAFNet-lite 用 L1，loss 不同 |
| 数据子集小 | 只有 80/20 对，适合学习流程，不适合下最终结论 |
| 没有 scheduler/EMA | 当前训练器是基础版，没有官方恢复模型常用训练技巧 |

这正是 Week5 要学的重点：复现现代模型时，不能只把结构写出来就期待马上超过 baseline。你要同时考虑数据规模、训练步数、loss、宽度、学习率和评估方式。

### 13.2 下一步怎么改 NAFNet-lite

建议按这个顺序继续：

1. 先把 steps 从 300 提到 1000，看曲线是否继续上升。
2. 再把 `width=8` 提到 `width=16`，观察 PSNR/SSIM 和训练时间变化。
3. 保持同一个 SIDD split，不要换数据，否则无法公平比较。
4. 如果 L1 收敛慢，可以尝试 Charbonnier loss。
5. 每次只改一个变量，不要同时改 width、loss、steps。

## 14. NAFNet-lite 标准版结果

在 300-step 轻量短训之后，又跑了一轮更标准的 NAFNet-lite：

```text
config: paired_rgb_sidd_tiny_nafnet_lite_l1_1000.yaml
width: 16
middle_blocks: 2
steps: 1000
loss: L1
patch size: 128
```

结果对比：

| Model | 设置 | Best PSNR | Best SSIM | 结论 |
|---|---|---:|---:|---|
| NAFNet-lite 短训 | width=8, 300 steps | 26.8194 | 0.73509 | 刚超过 baseline |
| NAFNet-lite 标准版 | width=16, 1000 steps | 33.3269 | 0.86223 | 大幅提升，说明短训不足 |
| DnCNN 标准版 | 2000 steps, L2 | 35.5356 | 0.88367 | 当前最强 baseline |

![SIDD tiny standard NAFNet 对比图](figures/week4_sidd_tiny_standard_eval/triplet_contact_sheet.png)

> 图说明：这张图里可以看到 NAFNet-lite 从早期到 step 1000 的输出逐渐接近 clean。它仍未超过 DnCNN，但已经明显强于 300-step 轻量版，说明现代恢复模型更依赖足够训练和合适宽度。

这次标准版结果让 Week5 的结论更清楚：

```text
NAFNet-lite 不是不能学；
300-step width=8 只是太小太短；
width=16 + 1000 steps 后已经接近可用 baseline；
但当前数据和训练配置下，DnCNN residual 仍然更稳。
```

下一步如果继续做 NAFNet-lite，最值得跑的是：

```text
paired_rgb_sidd_tiny_nafnet_lite_l1_2000.yaml
或
NAFNet-lite + Charbonnier loss
```

这时再和 DnCNN 2000 做比较，才更接近公平。

## 15. 面试复述

学完 Week5 后，你应该能这样讲：

```text
我先用 DnCNN residual 和 UNet 建立真实 RGB 去噪 baseline，
再实现一个 NAFNet-lite，重点学习 SimpleGate、通道注意力和多尺度恢复结构。
我没有直接追官方大模型，而是在同一小型 paired RGB 数据上比较 PSNR、SSIM 和三联图，
分析它相对 DnCNN/UNet 是否真的改善纹理、边缘和噪声。
```

## 16. 通过标准

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

## 17. Week5 面试题和参考回答

**Q1：NAFNet-lite 和普通 CNN 最大区别是什么？**

普通 CNN baseline 通常是卷积 + ReLU 堆叠，主要靠局部卷积提取特征。NAFNet-lite 仍然用卷积，但引入了更现代的恢复模块：`SimpleGate`、通道注意力、block 内部 residual、多尺度 encoder-decoder。它不是完全不同的范式，而是在 CNN 基础上做更适合图像恢复的结构设计。

**Q2：NAFNet 说 activation free，是不是没有非线性？**

不是。它不用传统 ReLU/GELU 这类激活函数，但 `SimpleGate` 里的乘法仍然提供非线性：

```text
x1, x2 = split(x)
out = x1 * x2
```

两个特征相乘不是线性操作，所以网络仍然有表达复杂关系的能力。

**Q3：SimpleGate 为什么可能适合图像恢复？**

图像恢复经常需要“一个特征调制另一个特征”。比如某些通道判断哪里像噪声，另一些通道保存颜色或边缘。`x1 * x2` 可以看成一种门控：一部分特征决定另一部分特征通过多少。

**Q4：block residual 和 DnCNN residual denoise 有什么区别？**

DnCNN residual denoise 是任务输出层面的残差：

```text
clean = noisy - predicted_noise
```

NAFBlock 内部 residual 是特征层面的残差：

```text
feature_out = feature_in + delta_feature
```

一个发生在图像输出空间，一个发生在网络中间特征空间。名字都叫 residual，但层级不同。

**Q5：为什么这轮 NAFNet-lite 没有超过 DnCNN？**

当前 DnCNN 是 `2000 steps + residual denoise + L2/MSE`，非常适合这个 SIDD tiny 去噪任务。NAFNet-lite 虽然更现代，但当前只跑 `1000 steps + L1`，并且是简化版，没有官方完整训练策略、scheduler、EMA 或更大数据。因此它没赢 DnCNN 不代表结构无效，只说明当前设置下 DnCNN 更稳。

**Q6：那 NAFNet-lite 的实验价值在哪里？**

价值在于它证明了现代恢复 block 已经接入当前训练框架，并且从短训版 `26.8194 PSNR` 提升到标准版 `33.3269 PSNR`。这说明训练设置对现代模型非常关键，也说明后续可以继续做更公平的 ablation。

**Q7：如果继续优化 NAFNet-lite，你会怎么做？**

我会一次只改一个变量：

```text
1. 固定 width=16，把 steps 提到 2000；
2. 固定 steps，比较 L1 和 Charbonnier；
3. 如果仍然欠拟合，再增大 width 或 middle_blocks；
4. 始终使用同一 SIDD split 和同一评估脚本；
5. 同时看 PSNR、SSIM、三联图和 error map。
```

**Q8：这个项目怎么写进简历？**

可以写：

```text
基于 PyTorch 搭建真实 paired RGB 图像去噪实验闭环，整理 SIDD Small sRGB 子集，完成 noisy baseline、DnCNN residual、UNet、NAFNet-lite 的训练与对比；实现 PSNR/SSIM 评估、三联图可视化和 error map 分析，在 SIDD tiny 上 DnCNN baseline 达到 35.54 dB PSNR / 0.8837 SSIM。
```

如果面试官继续追问，就讲：

```text
我没有只跑模型，而是先做数据配对检查和 input baseline；
再用统一 split 比较不同模型；
最后用指标曲线、三联图和 error map 分析为什么模型表现不同。
```
