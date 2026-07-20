# Week 1：Toy RGB 去噪完整学习流程

Week 1 的目标是跑通一个完整但小型的 RGB 去噪任务。

它原来被拆成很多 `week1a/week1b/...` 小报告，现在统一整理成一条学习路线。

## 阅读导航

本章较长，不要求第一遍逐字背诵：

- 第一遍必读：第1～4、8～12、15～17节，跑通最小闭环并完成通过标准；
- 第二遍深入：第3.1～3.7和第4.1，跟踪卷积 shape、padding、ReLU 和 residual；
- 实验复盘：第13～14节，用结果表和图像解释单变量对比；
- 遇到问题再查：具体命令、历史数值和详细参考回答。

第一遍的完成标志是“能独立解释并跑通”，不是“逐字背完两千多行”。

## 0. 本次补充：Week1 核心实验总表

对照阶段二学习路线，Week1 原有内容已经覆盖 toy RGB denoise 的主体学习目标：TinyCNN probe、DnCNN residual、direct clean、L1/L2、patch size、shot/read noise 和 paired RGB smoke。

这次补充的重点不是再增加一个模型，而是增加一个可复现的汇总脚本，把已有 `runs/*/metrics.csv` 自动整理成 Week1 核心实验总表：

```bash
python stage2_ai_isp/scripts/15_export_week1_summary.py --runs-root stage2_ai_isp/runs --output-dir stage2_ai_isp/reports/figures/week1_summary
```

输出文件：

```text
reports/figures/week1_summary/week1_core_experiments.csv
reports/figures/week1_summary/week1_core_experiments.png
```

![Week1 core experiments](figures/week1_summary/week1_core_experiments.png)

这张表的读法：

- TinyCNN 10/50/100 steps 用来确认训练闭环是否真的在工作；
- DnCNN residual vs direct clean 用来理解“预测噪声再相减”为什么更适合去噪；
- L1 vs L2/MSE 用来理解 loss 和 PSNR/SSIM 的偏向；
- patch 128 和 shot/read noise 用来建立“上下文、代价、噪声建模”的实验意识；
- paired RGB smoke 用来证明训练入口已经能从 toy 数据过渡到文件夹成对数据。

所以 Week1 的最终学习重点可以压缩成一句话：

```text
先用最小 toy 任务证明训练闭环可信，再用一组控制实验理解模型、loss、patch 和噪声模型的取舍。
```

## 1. 本周目标

最小任务：

```text
clean RGB patch -> synthetic noise -> model -> denoised RGB
```

这个任务用来验证工程链路：

- toy dataset；
- train / validation split；
- checkpoint 保存；
- PSNR / SSIM 验证；
- noisy / output / clean 三联图；
- config-driven 实验设置；
- 模型、loss、patch size、噪声模型的控制实验。

## 2. 第一步：建立图像恢复直觉

图像去噪不是“让图片变好看”这么模糊，而是：

```text
输入：noisy patch
答案：clean patch
模型输出：output patch
目标：让 output 接近 clean
```

三联图通常按这个顺序看：

```text
noisy | output | clean
```

观察时不要只看 PSNR，也要看：

- output 是否比 noisy 干净；
- output 是否接近 clean；
- 纹理是否被过度抹平；
- 边缘和颜色是否异常；
- 指标差异是否能在图上看出来。

## 3. 第二步：用 TinyCNN 跑通训练闭环

TinyCNN 不是为了追求效果，而是为了确认训练真的能工作。

建议先跑三个 probe：

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_10.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_50.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

已观察到的结果：

| steps | train loss | val PSNR | val SSIM | 解读 |
|---:|---:|---:|---:|---|
| 10 | 0.170468 | 13.49 | 0.6601 | 刚开始学 |
| 50 | 0.083647 | 18.19 | 0.7377 | 学到一点 |
| 100 | 0.034625 | 26.73 | 0.8526 | 明显变好 |

对应的真实三联图如下。每一行都是：

```text
noisy 输入 | output 模型输出 | clean 标准答案
```

![TinyCNN step 10/50/100 真实输出对比](figures/week1_tinycnn_10_50_100_real_compare.png)

> 图说明：这张图按训练步数对比 TinyCNN 的输出。每行通常是 noisy、output、clean；step 10 的 output 颜色偏绿，说明模型刚开始还没学会正确重建 RGB 三个通道，step 50 变灰说明它学到了一些平均化去噪但颜色还不稳定，step 100 才明显接近 clean。

这一段要理解的是：

```text
step 变多 -> 参数被更多次修正 -> output 有机会更接近 clean
```

### 3.1 TinyCNN 到底是什么？

TinyCNN 是本项目里最小的 CNN 去噪模型。它不是为了追求最高指标，而是为了让你第一次看清楚：

```text
一张 noisy RGB 图像，怎么经过几个可学习卷积层，变成一张 output 图像。
```

它可以先理解成一个函数：

```text
output = TinyCNN(noisy)
```

输入和输出形状保持一致：

```text
noisy:  [B, 3, H, W]
output: [B, 3, H, W]
clean:  [B, 3, H, W]
```

这里：

- `B` 是 batch size；
- `3` 是 RGB 三个通道；
- `H/W` 是 patch 的高和宽，比如 64x64；
- output 要和 clean 对齐，才能计算 loss。

### 3.2 TinyCNN 的结构

当前 TinyCNN 是 3 层卷积：

```text
Conv2d(3 -> features, 3x3, padding=1)
  -> ReLU
  -> Conv2d(features -> features, 3x3, padding=1)
  -> ReLU
  -> Conv2d(features -> 3, 3x3, padding=1)
```

用更直观的话说：

```text
RGB noisy 图
  -> 提取局部特征
  -> 组合局部特征
  -> 输出 RGB denoised 图
```

`padding=1` 的作用是保持图像大小不变。否则 3x3 卷积会让图像边缘变小，output 就无法和 clean 直接对齐。

### 3.3 每一层在做什么？

先用图建立直觉：TinyCNN 不是一下子“凭空生成”干净图，而是先把 RGB 图变成一组中间特征图，再把这些特征图映射回 RGB 输出。

![TinyCNN 每层作用示意图](figures/week1_tinycnn_layer_flow.png)

> 图说明：这张图展示 TinyCNN 的三层卷积如何流动。输入是 `[B, 3, H, W]` 的 RGB 图，第一层把 3 个颜色通道变成更多特征通道，中间层继续组合局部特征，最后一层再压回 3 个 RGB 通道作为输出。

第一层卷积：

```text
Conv2d(3 -> features)
```

把 RGB 输入变成一组特征图。你可以把它理解成从原图里提取局部模式，比如边缘、颜色变化、局部纹理和噪声模式。

第二层卷积：

```text
Conv2d(features -> features)
```

继续组合这些局部特征。第一层看到的是比较原始的局部变化，第二层可以把这些变化组合成稍微复杂一点的判断。

第三层卷积：

```text
Conv2d(features -> 3)
```

把中间特征重新映射回 RGB 图像，所以输出又变成 3 个通道。

### 3.4 ReLU 是什么作用？

ReLU 是非线性激活：

```text
ReLU(x) = max(0, x)
```

可以把 ReLU 理解成一个逐像素、逐通道的开关函数：负响应关掉，正响应保留。

![ReLU 激活函数示意图](figures/week1_relu_activation_explained.png)

> 图说明：左边是 ReLU 的表达式 `max(0, x)`，右边是函数曲线。横轴是输入响应，纵轴是输出响应；小于 0 的值会被压成 0，大于 0 的值原样保留，所以它像一个“负值关掉、正值通过”的开关。

如果没有 ReLU，多层卷积叠起来本质上仍然接近一个线性变换，表达能力会很弱。

ReLU 让模型能表达更复杂的规则，比如：

```text
如果这个局部变化像噪声，就抑制；
如果这个局部变化像边缘，就保留。
```

它不是显式写死这些规则，而是训练后参数学出来的。

更直观地说，卷积层会产生很多中间特征。有些特征响应是正的，表示“这个局部模式比较像我正在找的东西”；有些响应是负的，表示“不像”或者方向相反。

ReLU 做了一件很简单的事：

```text
正响应保留；
负响应压成 0。
```

这样做有几个好处。

第一，它引入非线性。没有 ReLU 时，多个卷积层连续叠加，整体仍然接近一个线性变换。线性模型表达能力有限，很难学会复杂的图像恢复规则。

第二，它让特征更稀疏。很多不重要或不匹配的响应被压成 0，后续卷积层可以更专注地组合有用特征。

第三，它计算简单，训练稳定，是 CNN 里最常见的基础激活函数之一。

在 TinyCNN 里，ReLU 出现在前两层卷积后面：

```text
Conv -> ReLU -> Conv -> ReLU -> Conv
```

最后一层后面没有 ReLU，是因为最后输出要回到 RGB 图像空间。输出值可能需要通过后续 clamp 或 loss 来约束，而不是在模型内部直接把负值全部截断。否则模型输出的表达会被过早限制。

如果去掉 ReLU，TinyCNN 仍然能跑，但表达能力会弱很多。它更像一个简单的线性滤波器，而不是一个能学习复杂局部规则的神经网络。

### 3.4.1 padding 是什么作用？

TinyCNN 每一层卷积都用了：

```text
kernel size = 3x3
padding = 1
```

3x3 卷积的意思是：每个输出像素会看输入里一个 3x3 的局部邻域。

如果不加 padding，图像会越卷越小。比如输入是 64x64：

```text
64x64 --3x3 conv, no padding--> 62x62
62x62 --3x3 conv, no padding--> 60x60
60x60 --3x3 conv, no padding--> 58x58
```

这样 output 就变成 58x58，而 clean 还是 64x64。它们尺寸不一致，loss 就不能直接算。

`padding=1` 会在图像四周补一圈像素，让 3x3 卷积后空间尺寸保持不变：

```text
64x64 --3x3 conv, padding=1--> 64x64
```

这对图像恢复非常重要，因为我们通常希望：

```text
输入 noisy 是多大；
输出 denoised 就是多大；
clean target 也是多大。
```

也就是：

```text
noisy:  [B, 3, H, W]
output: [B, 3, H, W]
clean:  [B, 3, H, W]
```

padding 还有一个边界问题。卷积在图像中心很自然，因为中心像素周围有完整邻域；但图像边缘没有完整 3x3 邻域。padding 相当于给边缘补出可计算的邻域，让边缘也能参与卷积输出。

不过 padding 不是完全没有代价。补出来的边界像素不是真实图像内容，所以边缘区域的预测可能更容易受影响。当前 toy 实验里 patch 较小，主要目的是跑通训练闭环，所以使用最常见、最简单的 `padding=1`。

### 3.4.2 ReLU 和 padding 分别解决什么问题？

可以简单记成：

| 概念 | 解决的问题 | 对 TinyCNN 的意义 |
|---|---|---|
| ReLU | 让模型有非线性表达能力 | 不只是线性滤波，能学习更复杂的去噪规则 |
| padding | 保持图像尺寸不变 | output 能和 clean 对齐计算 loss |

它们不是同一类东西：

- ReLU 改的是特征数值的表达方式；
- padding 改的是卷积计算时图像边界和尺寸的处理方式。

在 TinyCNN 里，两者一起让模型既能训练，又能保持输入输出尺寸一致。

![ReLU 和 padding 直观对比](figures/week1_relu_padding_visual_compare.png)

> 图说明：这张图把 ReLU 和 padding 两个容易混的概念分开。ReLU 改的是数值，把负响应变成 0；padding 改的是卷积时图像边界怎么补，让卷积后空间尺寸不至于不断变小。

### 3.5 TinyCNN 为什么适合做第一个模型？

TinyCNN 的优点是简单、快、容易定位问题。

它没有：

- 下采样；
- 上采样；
- skip connection；
- BatchNorm；
- 多尺度结构；
- residual output 设计。

这意味着如果训练失败，排查范围很小。你只需要先问：

```text
数据对吗？
loss 对吗？
梯度能回传吗？
optimizer 在更新吗？
validation 能跑吗？
图能保存吗？
```

所以 TinyCNN 的学习价值不是“它强”，而是“它能帮我们确认管线是活的”。

### 3.6 TinyCNN 的局限是什么？

TinyCNN 只有 3 层卷积，表达能力有限。

它的局限包括：

- 能看到的空间上下文比较小；
- 很难处理复杂纹理；
- 对真实 sensor noise 的表达能力有限；
- 没有 residual denoise 的任务先验；
- 没有多尺度结构，不能很好利用大范围信息。

所以 TinyCNN 跑通后，不应该停在 TinyCNN，而应该换到 DnCNN residual 做更合理的 denoise baseline。

### 3.7 怎么看 TinyCNN probe 的结果？

TinyCNN probe 的重点不是最终分数，而是趋势。

你应该看三个东西：

1. `metrics.csv`
2. `vis/step_*.png`
3. 终端里的 loss / validation 输出

理想趋势是：

```text
step 10: output 还比较差
step 50: output 开始变干净
step 100: output 明显接近 clean
```

已观察结果：

| steps | train loss | val PSNR | val SSIM | 说明 |
|---:|---:|---:|---:|---|
| 10 | 0.170468 | 13.49 | 0.6601 | 刚开始学，输出还不稳定 |
| 50 | 0.083647 | 18.19 | 0.7377 | 已经学到一些去噪规律 |
| 100 | 0.034625 | 26.73 | 0.8526 | 输出明显接近 clean |

这说明训练闭环在工作：

```text
参数不是随机不变的；
loss 能指导参数更新；
更新后的模型确实让 output 更接近 clean。
```

## 4. 第三步：换成 DnCNN residual

TinyCNN 适合教学，但表达能力有限。接下来使用更深一点的 DnCNN。

先把三个名字的关系分清楚：

- `CNN` 是一类网络，核心是用卷积层处理图像；
- `TinyCNN` 是一个很小的 CNN，用来验证训练闭环；
- `DnCNN` 是一个更适合去噪的 CNN，通常更深，并且常用 residual denoise。

![CNN / TinyCNN / DnCNN 关系对比图](figures/week1_cnn_tinycnn_dncnn_compare.png)

> 图说明：这张图说明 CNN 是一类模型，TinyCNN 和 DnCNN 都是 CNN 的具体版本。TinyCNN 用很少的卷积层帮助你看懂基本流程；DnCNN 更深，通常学习噪声残差，再用 `clean = noisy - noise_pred` 得到去噪结果。

所以问题不是“DnCNN 和 CNN 有什么区别”。更准确地说：

```text
CNN 是大类；
TinyCNN 和 DnCNN 都是 CNN；
DnCNN 是专门为 denoise 设计得更合理的一种 CNN。
```

更细的区别可以这样看：

| 对比项 | CNN | TinyCNN | DnCNN residual |
|---|---|---|---|
| 是什么 | 卷积神经网络这一大类 | 一个最小 CNN baseline | 一个去噪 CNN baseline |
| 层数 | 不固定 | 当前 3 层卷积 | 当前配置更深，默认 5 层卷积 |
| 输出含义 | 看具体任务 | 直接输出 clean RGB | 默认输出 noise，再做 `noisy - noise_pred` |
| 学习重点 | 图像局部特征 | 训练链路是否跑通 | 去噪任务表达是否更自然 |
| 优点 | 适合图像局部模式 | 简单、快、容易排查 | 更强、更适合 denoise |
| 局限 | 只是类别名，不是具体模型 | 表达能力有限 | 比 TinyCNN 多一些结构和变量 |

直接预测 clean：

```text
denoised = net(noisy)
```

Residual 去噪：

```text
noise_pred = net(noisy)
denoised = noisy - noise_pred
```

为什么 residual 更自然？

因为 noisy 本来就接近 clean：

```text
noisy = clean + noise
```

模型不用重新生成整张 clean，只要学会哪些东西像噪声，然后减掉。

已观察到的结果：

| 模型 | steps | final val PSNR | final val SSIM |
|---|---:|---:|---:|
| DnCNN residual | 300 | 31.15 | 0.8985 |
| DnCNN direct clean | 300 | 28.23 | 0.8876 |
| DnCNN residual long | 1000 | 33.13 | 0.9355 |
| DnCNN direct clean long | 1000 | 31.23 | 0.9144 |

结论：direct clean 训练久了也能变好，但 residual 在去噪任务里更容易优化。

### 4.1 DnCNN residual 和 direct clean 的核心区别

这两个实验用的都是 DnCNN 这个网络骨架，区别不在“卷积层长什么样”，而在“网络输出被解释成什么”。

#### Direct clean：网络直接输出干净图

direct clean 的形式是：

```text
output = net(noisy)
loss = distance(output, clean)
```

这里 `net(noisy)` 被直接当成去噪后的图像。

模型要学的是完整映射：

```text
noisy -> clean
```

也就是说，它必须自己决定整张干净图应该长什么样，包括：

- 原图颜色；
- 边缘；
- 纹理；
- 平滑区域；
- 噪声应该消失的位置。

这当然能学，但任务比较大。因为 clean 的大部分内容其实已经在 noisy 里了，direct clean 仍然让模型重新输出整张图。

#### Residual denoise：网络输出噪声，再从 noisy 里减掉

residual 的形式是：

```text
noise_pred = net(noisy)
output = noisy - noise_pred
loss = distance(output, clean)
```

这里 `net(noisy)` 不再被解释成干净图，而是被解释成“预测出来的噪声”。

模型要学的是：

```text
noisy -> noise
```

然后用：

```text
denoised = noisy - noise
```

得到最终输出。

这个写法更适合去噪，因为去噪的本质往往就是：

```text
clean = noisy - noise
```

#### 两者对比

| 对比项 | direct clean | residual denoise |
|---|---|---|
| 网络输出含义 | 干净图 `clean_pred` | 噪声 `noise_pred` |
| 最终输出 | `output = net(noisy)` | `output = noisy - net(noisy)` |
| 学习目标 | 从 noisy 直接生成 clean | 从 noisy 估计 noise |
| 是否利用 noisy 本来接近 clean | 利用得不明显 | 显式利用 |
| 优化难度 | 相对更难 | 通常更容易 |
| 保留原图结构 | 需要模型自己学会 | 更自然，因为从 noisy 上减噪声 |

#### 一个直观例子

假设某个像素位置：

```text
clean = 0.70
noise = 0.05
noisy = 0.75
```

direct clean 要学：

```text
0.75 -> 0.70
```

residual 要学：

```text
0.75 -> 0.05
output = 0.75 - 0.05 = 0.70
```

在去噪任务里，预测“该减掉多少”通常比“重新生成最终答案”更贴近问题。

#### 为什么 residual denoise 通常更容易优化？

先看图，再看下面的解释：

![Direct clean 和 residual denoise 的直觉对比](figures/week1_direct_vs_residual_intuition.png)

> 图说明：上半部分是 direct clean：模型直接从 noisy 预测 clean。下半部分是 residual denoise：模型先预测 noise，再用 noisy 减去 noise 得到 clean。去噪任务里 noise 往往比整张 clean 图更简单，所以 residual denoise 通常更容易学。

去噪任务里有一个很重要的前提：

```text
noisy 通常不是一张完全错误的图；
noisy 是一张已经接近 clean、但多了噪声的图。
```

也就是说，大部分图像内容已经在 noisy 里了：

- 物体大致在哪里；
- 边缘大致在哪里；
- 颜色大致是什么；
- 亮度结构大致是什么；
- 纹理主体大致还在。

direct clean 的学习目标是：

```text
noisy -> clean
```

这等于让模型重新输出整张干净图。哪怕 clean 的大部分内容已经在 noisy 里，模型仍然要自己决定整张图每个像素应该是多少。

residual denoise 的学习目标是：

```text
noisy -> noise
output = noisy - noise
```

这等于让模型只回答一个更小的问题：

```text
这张 noisy 图里，哪些东西像噪声？每个位置应该减掉多少？
```

所以 residual 的优势不是“数学上一定更强”，而是它把任务改得更贴近去噪本质：

```text
direct clean: 重新生成完整答案
residual denoise: 学会从已有答案里扣掉错误部分
```

如果噪声很弱，最理想的输出本来就接近：

```text
output ≈ noisy
```

这时 residual 网络只要预测一个接近 0 的 `noise_pred`，就已经不会严重破坏原图：

```text
noise_pred ≈ 0
output = noisy - 0 ≈ noisy
```

而 direct clean 即使在噪声很弱时，也仍然必须直接输出一张完整 RGB 图。如果训练初期输出偏灰、偏绿或亮度不对，整张图都会受影响。

从优化角度看，residual 往往更容易，是因为它学习的是“小改动”：

```text
clean 和 noisy 的差值 = noise
```

这个差值通常比整张 clean 图更简单、更小、更集中。因此模型更容易先学到“哪里要减一点”，再逐步学细节。

可以把它类比成改作文：

```text
direct clean: 看着有错的作文，重新写一篇正确作文
residual denoise: 在原文上标出哪些字句要删改
```

如果原文大体已经对，第二种任务通常更容易。

#### 从算法和代码角度看，两者到底差在哪里？

从算法上看，direct clean 和 residual denoise 的差异不是“有没有 CNN”，而是**网络输出的物理含义不同**。

direct clean 的算法流程是：

```text
输入 noisy
  -> CNN
  -> 直接得到 clean_pred
  -> clean_pred 和 clean 算 loss
```

对应公式：

```text
clean_pred = net(noisy)
loss = distance(clean_pred, clean)
```

代码直觉是：

```python
pred = net(noisy)
output = pred
loss = criterion(output, clean)
```

这里 `net(noisy)` 本身就被当成最终干净图。也就是说，网络最后一层输出的 3 个通道就是 RGB 图像：

```text
net(noisy): [B, 3, H, W]  # clean_pred
```

residual denoise 的算法流程是：

```text
输入 noisy
  -> CNN
  -> 得到 noise_pred
  -> output = noisy - noise_pred
  -> output 和 clean 算 loss
```

对应公式：

```text
noise_pred = net(noisy)
output = noisy - noise_pred
loss = distance(output, clean)
```

代码直觉是：

```python
noise_pred = net(noisy)
output = noisy - noise_pred
loss = criterion(output, clean)
```

这里 `net(noisy)` 不再被当成干净图，而是被当成噪声图：

```text
net(noisy): [B, 3, H, W]  # noise_pred
```

注意：两者的 CNN 主体可以长得很像，甚至可以完全一样。真正不同的是 forward 末尾怎么解释网络输出：

```python
# direct clean
return pred

# residual denoise
return x - pred
```

本项目里的 DnCNN 代码就是这样写的：

```python
pred = self.net(x)
out = x - pred if self.residual else pred
return out
```

所以同一个 DnCNN，如果：

```text
residual = False
```

它就是 direct clean：

```text
output = pred
```

如果：

```text
residual = True
```

它就是 residual denoise：

```text
output = noisy - pred
```

从 loss 角度看，两者最后都和 clean 比：

```text
loss = distance(output, clean)
```

区别在于 output 怎么来：

| 角度 | direct clean | residual denoise |
|---|---|---|
| CNN 输出 | `clean_pred` | `noise_pred` |
| forward 最后一步 | `output = pred` | `output = noisy - pred` |
| loss 比较对象 | `pred` vs `clean` | `noisy - pred` vs `clean` |
| 模型学的内容 | 整张干净图 | noisy 里要减掉的噪声 |
| 输入结构是否直接保留 | 不显式保留 | 显式从 noisy 继承 |

从梯度/优化角度也可以这样理解：residual denoise 的 loss 虽然仍然约束最终 output，但梯度会推动 `noise_pred` 接近真实噪声：

```text
真实 noise = noisy - clean
希望 noise_pred ≈ noisy - clean
```

因为只要：

```text
noise_pred = noisy - clean
```

那么：

```text
output = noisy - noise_pred
       = noisy - (noisy - clean)
       = clean
```

这就是 residual denoise 的代码含义：**网络不是直接学 clean，而是通过最终 loss，被训练成预测 noisy 和 clean 之间的差值。**

#### 为什么 residual 不是永远无敌？

Residual 更适合当前去噪任务，但不是所有图像恢复任务都一定选 residual。

如果输入和目标差异很大，比如：

- 极端低光增强；
- 大幅颜色映射；
- 风格转换；
- 从 RAW 到 sRGB 的复杂变换；

那么目标不一定只是“从输入里减掉一部分”。这时 direct 或更复杂的映射可能更合理。

所以这里的结论要限定在当前任务：

```text
在 toy RGB denoise 里，noisy 本来接近 clean，因此 DnCNN residual 比 direct clean 更自然。
```

## 5. 第四步：比较 L1 和 L2/MSE loss

同一个 DnCNN residual，只改 loss。

先解释名字：

```text
L1 loss = 平均绝对误差 = mean(abs(output - clean))
L2 loss = 平均平方误差 = mean((output - clean)^2)
MSE = Mean Squared Error = 平均平方误差
```

所以在本项目里：

```text
L2 loss 和 MSE 基本是同一个意思。
```

假设某个像素位置：

```text
output = 0.60
clean  = 0.70
error  = output - clean = -0.10
```

L1 看的是误差绝对值：

```text
abs(error) = abs(-0.10) = 0.10
```

L2/MSE 看的是误差平方：

```text
error^2 = (-0.10)^2 = 0.01
```

如果误差变大，比如：

```text
error = 0.50
```

那么：

```text
L1: abs(0.50) = 0.50
L2: 0.50^2 = 0.25
```

再对比小误差：

```text
error = 0.10
L1 = 0.10
L2 = 0.01
```

可以看到 L2/MSE 会更明显地区分大误差和小误差。误差越大，平方以后惩罚增长越快。

直觉上：

| Loss | 怎么看误差 | 倾向 |
|---|---|---|
| L1 | 误差有多大就罚多大 | 更线性，通常对异常大误差没那么敏感 |
| L2/MSE | 误差先平方再平均 | 大误差罚得更重，更贴近 PSNR |

为什么 L2/MSE 更贴近 PSNR？

因为 PSNR 本身就是从 MSE 推出来的：

```text
MSE 越小 -> PSNR 越高
```

所以如果训练目标是 MSE，验证指标又看 PSNR，目标和指标更一致，PSNR 往往更容易高。

为什么 L1 有时视觉上更自然？

因为 L1 不会像 L2 那样特别强烈地惩罚少数大误差。它有时不会那么倾向于把不确定区域平均化，所以边缘、纹理、结构可能看起来更自然。但这不是绝对规律，必须看三联图。

最重要的一点：

```text
L1 loss 的数字和 L2/MSE loss 的数字不能直接比大小。
```

比如：

```text
L1 = 0.02
L2 = 0.0007
```

不能说 `0.0007` 比 `0.02` 小很多，所以 L2 一定更好。它们不是同一把尺子。正确比较方式是看：

```text
val PSNR / val SSIM / 三联图
```

| Loss | final train loss | final val PSNR | final val SSIM |
|---|---:|---:|---:|
| L1 | 0.020152 | 31.1470 | 0.89850 |
| L2 / MSE | 0.000739 | 31.5874 | 0.89452 |

怎么读：

- L2/MSE 更贴近 PSNR，所以 PSNR 略高；
- L1 的 SSIM 略高，可能稍微更保结构；
- 两者差距不大，不要过度解读；
- 不同 loss 数值不能直接比较大小。

实用结论：

- 追 PSNR，用 L2/MSE；
- 检查结构和视觉平滑程度，保留 L1 对照；
- 进入真实数据前，不要只凭 toy 结果决定最终 loss。

## 6. 第五步：比较 patch size 64 和 128

Patch 更大，模型看到的上下文更多；但像素更多，训练更慢。

`patch size` 指的是训练时从图像里裁出来的小块尺寸。

图像恢复任务通常不会一开始就把整张大图丢进模型训练，而是从图里随机裁小块，比如：

```text
patch size = 64   -> 裁出 64x64 的小图块
patch size = 128  -> 裁出 128x128 的小图块
```

如果是 RGB 图，单张 patch 的形状就是：

```text
patch 64:  [3, 64, 64]
patch 128: [3, 128, 128]
```

加上 batch size 后，训练张量可能是：

```text
batch 8, patch 64:  [8, 3, 64, 64]
batch 8, patch 128: [8, 3, 128, 128]
```

这里的区别很大。因为像素数不是翻 2 倍，而是按面积算：

```text
64 x 64   = 4096 像素
128 x 128 = 16384 像素
```

所以 patch 从 64 变成 128，边长是 2 倍，但面积是 4 倍。模型每一步要处理的像素更多，训练时间和显存都会明显增加。

为什么 patch 128 可能效果更好？

因为模型看到的局部范围更大。去噪时，一个像素是不是噪声，不能只看它自己，还要看周围：

- 周围是不是平坦区域；
- 周围有没有边缘；
- 周围纹理是不是连续；
- 这个亮点是噪声，还是图像里的真实细节。

patch 64 看到的上下文少一些，适合快速验证；patch 128 看到的上下文多一些，有时更利于恢复结构和纹理。

但 patch size 不是越大越好：

- patch 越大，训练越慢；
- patch 越大，占用显存越多；
- 小数据上 patch 太大，随机裁剪变化可能减少；
- 真实数据里还要考虑显卡、batch size 和训练时间。

所以这组实验学的不是“128 永远比 64 好”，而是：

```text
patch size 是上下文和代价的取舍。
```

| Patch size | wall time | final train loss | final val PSNR | final val SSIM |
|---:|---:|---:|---:|---:|
| 64 | 15.86s | 0.000739 | 31.5874 | 0.89452 |
| 128 | 51.40s | 0.000499 | 33.4745 | 0.93176 |

结论：

- patch 64 适合快速检查；
- patch 128 在 toy 实验里指标更好；
- 进入真实数据前要考虑显存和时间。

## 7. 第六步：从 Gaussian noise 到 sensor-like noise

最开始的噪声是：

```text
noisy = clean + gaussian_noise
```

这适合做 sanity check，但真实传感器噪声更复杂。于是加入一个简化的 shot/read noise：

```text
noisy = clean + shot_noise(clean) + read_noise
```

含义：

- shot noise：和信号强度有关；
- read noise：更像固定电子噪声底。

工程结果：

```text
训练代码可以通过 config 切换噪声模型。
```

## 8. 第七步：先测 noisy 输入 baseline

比较两个噪声模型之前，先测输入本身有多难：

```text
input PSNR = PSNR(noisy, clean)
input SSIM = SSIM(noisy, clean)
```

命令：

```bash
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

校准结果：

| 配置 | 噪声 | Input PSNR | Input SSIM |
|---|---|---:|---:|
| `toy_rgb_denoise_dncnn_l2_loss.yaml` | Gaussian | 24.2068 | 0.46247 |
| `toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml` | 校准后 shot/read | 24.2036 | 0.45582 |

这一步的核心学习点：

```text
不要把“输入更干净”误读成“模型更好”。
```

## 9. 第八步：接入成对 RGB 图片文件夹

Toy 数据是在代码里生成的：

```text
clean patch -> synthetic noise -> noisy patch
```

真实 paired RGB 数据是文件：

```text
noisy image file + matching clean image file -> crop pair -> model
```

所以新增了 `PairedImageDenoiseDataset`，支持这种结构：

```text
clean_dir/
  pair_001.png
  pair_002.png

noisy_dir/
  pair_001.png
  pair_002.png
```

配置写法：

```yaml
data:
  dataset: paired_image
```

本地 paired RGB smoke 训练结果：

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 40 | 0.003541 | 24.6943 | 0.40882 |
| 80 | 0.001015 | 30.2105 | 0.73756 |
| 120 | 0.000558 | 32.9381 | 0.89218 |

这一步的重点不是刷指标，而是确认：

```text
只换 dataset，模型、loss、训练循环、checkpoint、metrics、可视化都不用重写。
```

## 10. 本周总结

Week 1 完成后，你应该能说清楚：

### 10.1 toy RGB denoise 的输入、答案和输出是什么？

toy RGB denoise 是一个监督学习任务。它的核心是：

```text
noisy RGB patch -> model -> output RGB patch
```

其中：

- 输入是 `noisy`，也就是带噪声的 RGB 小图块；
- 答案是 `clean`，也就是没有加噪声的干净 RGB 小图块；
- 输出是 `output`，也就是模型当前预测出来的去噪结果。

在 toy 数据里，noisy 通常由 clean 人工加噪声得到：

```text
noisy = clean + synthetic noise
```

所以 noisy 和 clean 天然对齐。模型训练时要做的是让：

```text
output 接近 clean
```

这也是为什么三联图总是按下面顺序看：

```text
noisy 输入 | output 模型输出 | clean 标准答案
```

这个任务虽然是 toy，但它已经包含图像恢复训练最核心的结构：有输入、有答案、有模型输出、有 loss、有验证指标。

### 10.2 TinyCNN 为什么适合先验证训练闭环？

TinyCNN 适合做第一个模型，不是因为它强，而是因为它简单。

它只有 3 层卷积和 2 个 ReLU，没有下采样、上采样、skip connection、BatchNorm 或复杂多尺度结构。这样一来，如果训练失败，问题更容易定位。

先跑 TinyCNN 可以检查：

- 数据能不能加载；
- noisy / clean shape 是否正确；
- model forward 是否能跑；
- loss 是否能计算；
- backward 是否能回传梯度；
- optimizer 是否能更新参数；
- validation 是否能正常输出 PSNR / SSIM；
- 三联图是否能保存。

TinyCNN probe 的核心目的不是刷分，而是确认训练闭环真的活着：

```text
step 增加 -> 参数被更新 -> output 更接近 clean -> validation 指标提高
```

如果 TinyCNN 都跑不通，直接上 DnCNN、UNet 或更强模型，只会让排查范围变大。

### 10.3 DnCNN residual 为什么比 direct clean 更自然？

去噪任务里，noisy 和 clean 的关系通常可以近似理解成：

```text
noisy = clean + noise
```

也就是说，noisy 不是完全错误的图。它里面大部分结构、颜色和边缘本来就来自 clean，只是多了噪声。

direct clean 的写法是：

```text
denoised = net(noisy)
```

模型要直接生成整张 clean 图。

residual denoise 的写法是：

```text
noise_pred = net(noisy)
denoised = noisy - noise_pred
```

模型只需要学习 noisy 里哪些部分像噪声，然后减掉。

这更符合去噪任务本质：

- noisy 本来接近 clean；
- noise 是 noisy 和 clean 之间的差值；
- 预测差值通常比重建整张图更容易；
- 原图结构更容易被保留。

所以在当前 toy RGB denoise 中，DnCNN residual 比 direct clean 更自然，也更容易优化。

### 10.4 L1 和 L2/MSE loss 的差异是什么？

L1 和 L2/MSE 都衡量 output 和 clean 的差距，但惩罚方式不同。

L1：

```text
loss = mean(abs(output - clean))
```

L2/MSE：

```text
loss = mean((output - clean)^2)
```

直觉上：

- L1 对误差的惩罚更线性；
- L2/MSE 会放大较大的误差；
- PSNR 和 MSE 直接相关，所以 L2/MSE 往往更利于 PSNR；
- L1 有时对结构和边缘更友好，但不是绝对规律。

当前实验里：

| Loss | val PSNR | val SSIM | 倾向 |
|---|---:|---:|---|
| L1 | 31.1442 | 0.90096 | SSIM 略高 |
| L2/MSE | 31.7001 | 0.89731 | PSNR 略高 |

所以不能简单说 L1 或 L2 谁永远更好。正确做法是同时看：

```text
loss + PSNR + SSIM + 三联图
```

### 10.5 patch size 为什么影响效果和速度？

patch size 决定模型一次看到多大的图像区域。

patch 64：

- 小；
- 快；
- 省显存；
- 适合快速检查训练链路。

patch 128：

- 面积是 64 的 4 倍；
- 模型看到更多空间上下文；
- 可能更有利于恢复纹理和结构；
- 训练更慢，也更吃显存。

当前 toy 实验里：

| Patch size | wall time | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 64 | 15.86s | 31.5874 | 0.89452 |
| 128 | 51.40s | 33.4745 | 0.93176 |

这说明 patch 128 在这个设置下效果更好，但代价明显更高。

实际使用时要根据目标选择：

```text
快速验证 -> patch 64
更正式比较 -> patch 128
真实数据训练 -> 根据显存和速度再定
```

### 10.6 Gaussian noise 和 shot/read noise 的区别是什么？

Gaussian noise 是最简单的合成噪声：

```text
noisy = clean + gaussian_noise
```

它通常假设噪声和图像内容关系不大，每个位置都按类似规则加随机扰动。

shot/read noise 更接近相机传感器噪声的直觉：

```text
noisy = clean + shot_noise(clean) + read_noise
```

其中：

- shot noise 和信号强度有关，亮暗区域的噪声表现可能不同；
- read noise 更像传感器读出过程中的电子噪声底；
- 它比纯 Gaussian 多了一层“噪声和成像过程有关”的假设。

但要注意：这里的 shot/read 仍然是简化模型，不等于真实相机噪声。它只是从 toy Gaussian 向 sensor-like noise 迈了一步。

### 10.7 为什么比较模型前要先测 noisy 输入 baseline？

因为不同实验的输入难度可能不同。

如果一个实验的 noisy 输入本来就更干净，它训练后的 PSNR / SSIM 更高，不一定说明模型更强。

所以训练前先测：

```text
input PSNR = PSNR(noisy, clean)
input SSIM = SSIM(noisy, clean)
```

这样可以判断输入本身有多难。

比如当前校准里：

| 噪声 | Input PSNR | Input SSIM |
|---|---:|---:|
| Gaussian | 24.2068 | 0.46247 |
| 校准后 shot/read | 24.2036 | 0.45582 |

两者 input PSNR 很接近，说明输入难度接近。之后再比较训练后的模型输出，结论才更公平。

核心原则是：

```text
先比较输入难度，再比较模型能力。
```

### 10.8 paired image dataset 为什么是进入真实数据前的关键接口？

toy 数据是在代码里生成的：

```text
clean patch -> synthetic noise -> noisy patch
```

真实数据通常不是这样。真实 RGB 去噪数据更像：

```text
noisy image file + clean image file
```

所以训练器必须能读取成对图片文件夹：

```text
train/noisy/pair_00001.png
train/clean/pair_00001.png
val/noisy/pair_00001.png
val/clean/pair_00001.png
```

paired image dataset 的意义是把“数据格式问题”和“训练逻辑问题”分开。

有了它以后：

- dataset 负责读图、配对、裁剪；
- model 继续负责从 noisy 预测 output；
- loss 继续比较 output 和 clean；
- validation、checkpoint、三联图都不用重写。

这就是为什么它是进入真实数据前的关键接口。没有这一步，后面接 SIDD-style 数据时就会把训练代码和数据格式搅在一起，难以维护和排错。

## 11. Week 1 到 Week 2 的过渡

现在 toy 任务已经足够稳定。下一步不是继续堆更多 toy 实验，而是：

```text
准备真实 noisy/clean 小子集 -> 测输入 baseline -> 小步训练 -> 看模型是否真的改善真实图片
```

到这里，Week 1 已经完成了三件关键准备：

| Week 1 已经学会 | Week 2 会继续用在哪里 |
|---|---|
| TinyCNN 验证训练闭环 | 真实数据训练前，先确认 pipeline 能跑通 |
| DnCNN residual 做去噪 | Week 2 继续固定这个模型，减少变量 |
| L1 / L2、patch、baseline、metrics、三联图 | Week 2 用同一套方法判断真实数据训练是否有效 |
| Paired RGB smoke | Week 2 从“合成 smoke 数据”升级到“真实 noisy/clean 文件” |

所以 Week 2 不是另起炉灶，而是把 Week 1 的训练方法接到真实 paired RGB 数据上。

## 12. 实验命令总表

这一节把 Week 1 用到的命令集中放在一起。学习时不需要一次全跑，可以按小节逐步跑。

### 12.1 TinyCNN probe

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_10.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_50.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

目的：观察 step 增加后，模型是否从“不会”逐渐变得“会一点”。

### 12.2 TinyCNN 完整 baseline

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_tiny.yaml
```

目的：得到一个最小模型基线。

### 12.3 DnCNN residual 和 direct clean

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_direct.yaml
```

目的：比较 residual denoise 和直接预测 clean。

### 12.4 长训练对比

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_long.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_direct_long.yaml
```

目的：观察 direct clean 训练更久后是否追上 residual。

### 12.5 L1 / L2 loss

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l1.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2.yaml
```

目的：只改 loss，观察 PSNR、SSIM 和可视化的差异。

### 12.6 Patch size

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_patch128.yaml
```

目的：比较 patch 64 和 patch 128 的速度与质量。

### 12.7 Sensor-like noise

```bash
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_shot_read.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

目的：从固定 Gaussian noise 走向更接近传感器的 shot/read noise。

### 12.8 输入 noisy baseline

```bash
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_loss.yaml
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

目的：训练前先知道 noisy 输入本身的 PSNR / SSIM。

### 12.9 Paired RGB smoke

```bash
python stage2_ai_isp/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
python stage2_ai_isp/scripts/02_measure_noise_baseline.py --config stage2_ai_isp/configs/paired_rgb_smoke_dncnn_l2.yaml
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_smoke_dncnn_l2.yaml
```

目的：验证成对图片文件夹数据链路可训练。

## 13. 结果总表

一次实验会留下多种产物。先看整体关系，再看后面的结果表和对比图。

![Week 1 实验产物关系图](figures/week1_experiment_outputs_map.png)

> 图说明：这张图整理 Week1 训练后会产生哪些文件。重点看 `runs/` 下面的 `metrics.csv`、checkpoint 和可视化图片：它们分别用来记录指标、保存模型参数、观察输出图像。

### 13.1 模型 baseline

| 模型 | steps | final train loss | final val PSNR | final val SSIM | 结论 |
|---|---:|---:|---:|---:|---|
| TinyCNN | 100 | 0.034434 | 26.70 | 0.8457 | 能跑通闭环，但能力有限 |
| DnCNN residual | 300 | 0.020152 | 31.15 | 0.8985 | 当前 toy baseline 更稳 |
| DnCNN direct clean | 300 | 0.037522 | 28.23 | 0.8876 | 直接预测 clean 更难 |
| UNet | 300 | 0.058372 | 21.17 | 0.7987 | 这个小配置下不适合作为当前 baseline |

### 13.2 DnCNN 长训练

| 模型 | steps | final val PSNR | final val SSIM | 结论 |
|---|---:|---:|---:|---|
| DnCNN residual long | 1000 | 33.13 | 0.9355 | residual 继续提升 |
| DnCNN direct clean long | 1000 | 31.23 | 0.9144 | direct clean 也变好，但仍落后 |

### 13.3 L1 / L2

| Loss | final train loss | final val PSNR | final val SSIM | 解读 |
|---|---:|---:|---:|---|
| L1 | 0.020152 | 31.1470 | 0.89850 | SSIM 略高 |
| L2 / MSE | 0.000739 | 31.5874 | 0.89452 | PSNR 略高 |

### 13.4 Patch size

| Patch size | wall time | final train loss | final val PSNR | final val SSIM | 解读 |
|---:|---:|---:|---:|---:|---|
| 64 | 15.86s | 0.000739 | 31.5874 | 0.89452 | 快速实验合适 |
| 128 | 51.40s | 0.000499 | 33.4745 | 0.93176 | 指标更好，但慢很多 |

### 13.5 噪声模型校准

| 配置 | 噪声 | Input PSNR | Input SSIM |
|---|---|---:|---:|
| `toy_rgb_denoise_dncnn_l2_loss.yaml` | Gaussian | 24.2068 | 0.46247 |
| `toy_rgb_denoise_dncnn_l2_shot_read.yaml` | 原始 shot/read | 25.9799 | 0.53497 |
| `toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml` | 校准后 shot/read | 24.2036 | 0.45582 |

| 噪声 | final val PSNR | final val SSIM | 解读 |
|---|---:|---:|---|
| Gaussian | 31.5874 | 0.89452 | 基准 |
| 校准后 shot/read | 32.1824 | 0.91118 | 输入难度接近后仍略好 |

### 13.6 Paired RGB smoke

输入 baseline：

| Dataset | Input PSNR | Input SSIM |
|---|---:|---:|
| paired RGB smoke | 22.1273 | 0.28203 |

训练结果：

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 40 | 0.003541 | 24.6943 | 0.40882 |
| 80 | 0.001015 | 30.2105 | 0.73756 |
| 120 | 0.000558 | 32.9381 | 0.89218 |

### 13.7 结果详细分析与可视化对比

这一节把数字结果和可视化放在一起读。图里的每一行都是：

```text
noisy | output | clean
```

也就是左边看输入问题，中间看模型输出，右边看标准答案。

#### 13.7.1 TinyCNN：先确认模型真的在学

![TinyCNN training progress](figures/week1_tinycnn_progress_compare.png)

> 图说明：这张图把 TinyCNN 不同步数的可视化结果放在一起。阅读时不要只看“像不像”，还要看颜色、噪声、边缘是否逐步接近 clean，这能帮助你理解训练 step 增加带来的变化。

TinyCNN 的 step 50 和 step 100 对比，重点不是“最终图像多漂亮”，而是看训练闭环是否有效。

从指标看：

| steps | train loss | val PSNR | val SSIM |
|---:|---:|---:|---:|
| 50 | 0.112161 | 17.6088 | 0.73656 |
| 100 | 0.034434 | 26.7033 | 0.84572 |

这说明三件事：

1. train loss 从 `0.112161` 降到 `0.034434`，模型确实在减少 output 和 clean 的差距。
2. val PSNR 从 `17.61` 提到 `26.70`，说明不是只在训练集上变好，验证集也变好。
3. val SSIM 从 `0.73656` 提到 `0.84572`，说明结构相似度也在改善。

图上应该重点看 output 是否从“仍然带明显噪声”变成“更接近 clean”。如果图像也同步变好，才说明训练闭环可信。

TinyCNN 的结论：

```text
TinyCNN 能证明训练管线有效，但它不是最终去噪 baseline。
```

#### 13.7.2 TinyCNN / DnCNN / UNet：模型能力不是只看名字

![Model final comparison](figures/week1_model_final_compare.png)

> 图说明：这张图比较不同模型或不同训练设置的最终输出。看图时按 noisy、output、clean 的顺序观察：好的模型应该减少噪声，同时尽量不把边缘、颜色和纹理抹掉。

这张图把 TinyCNN、DnCNN residual、UNet 的本地可见最终可视化放在一起。

指标对比：

| 模型 | steps | final val PSNR | final val SSIM |
|---|---:|---:|---:|
| TinyCNN | 100 | 26.7033 | 0.84572 |
| DnCNN residual | 300 | 31.1442 | 0.90096 |
| UNet | 300 | 21.1749 | 0.79869 |

DnCNN residual 明显比 TinyCNN 更好，原因是 DnCNN 更深，能组合更多局部特征，也更适合 denoise baseline。

UNet 在这个小实验里指标反而差，不代表 UNet 这个架构没用。更合理的解释是：

- 当前 UNet 配置可能不适合这么小的 toy 设置；
- 训练步数、学习率、模型容量可能没有调好；
- encoder-decoder 结构更复杂，未必在小规模 toy probe 上马上占优；
- 当前阶段目标是学习训练链路，不是调出最强 UNet。

这一组实验的学习点是：

```text
模型名字不等于效果。必须结合任务、配置、训练步数、指标和可视化判断。
```

#### 13.7.3 L1 vs L2：指标偏向和视觉差异要分开看

![L1 L2 visual comparison](figures/week1_l1_l2_visual_compare.png)

> 图说明：这张图用于直观看 L1 和 L2/MSE loss 的差别。L2 对大误差惩罚更重，可能更偏向平滑；L1 对异常大误差没那么敏感，视觉上有时更能保留边缘和纹理。

L1 和 L2/MSE 使用同样的 DnCNN residual，只改 loss。

本地可见结果：

| Loss | step | train loss | val PSNR | val SSIM |
|---|---:|---:|---:|---:|
| L1 | 300 | 0.019765 | 31.1442 | 0.90096 |
| L2/MSE | 300 | 0.000719 | 31.7001 | 0.89731 |

这里有两个重点。

第一，L1 和 L2 的 train loss 数值不能直接比较。`0.019765` 和 `0.000719` 是不同 loss 定义下的数字，不是同一把尺子。

第二，PSNR 和 SSIM 给出的倾向不同：

- L2/MSE 的 PSNR 更高，因为 PSNR 和 MSE 更一致；
- L1 的 SSIM 略高，说明结构相似度略占优；
- 从可视化看，两者差异不一定非常明显。

这说明图像恢复不能只看一个指标。比较 loss 时要同时看：

```text
PSNR + SSIM + 三联图
```

本阶段结论：

```text
如果目标是 PSNR，L2/MSE 是合理默认；
如果关心结构和视觉质感，L1 仍然值得保留作对照。
```

#### 13.7.4 Paired RGB smoke：文件夹成对数据链路已经能训练

![Paired RGB smoke progress](figures/week1_paired_rgb_smoke_progress.png)

> 图说明：这张图展示 paired RGB smoke 数据上的训练进展。它不是最终真实数据结果，而是用一个可控小数据集确认数据读取、训练、验证和可视化整条管线都能跑通。

Paired RGB smoke 的重点不是数据多真实，而是验证训练器能从 noisy/clean 文件夹读取成对图片。

输入 baseline：

| Dataset | Input PSNR | Input SSIM |
|---|---:|---:|
| paired RGB smoke | 22.1273 | 0.28203 |

训练结果：

| Step | Train loss | Val PSNR | Val SSIM |
|---:|---:|---:|---:|
| 40 | 0.003541 | 24.6943 | 0.40882 |
| 80 | 0.001015 | 30.2105 | 0.73756 |
| 120 | 0.000558 | 32.9381 | 0.89218 |

这个结果非常重要，因为它说明：

1. noisy/clean 文件夹能正确配对；
2. dataset 能裁剪并返回 paired patch；
3. 训练主循环不需要为 paired data 重写；
4. 模型输出明显超过 noisy 输入 baseline；
5. 三联图能显示 output 逐步接近 clean。

这一步是 Week 1 通往 Week 2 的关键证据。

#### 13.7.5 怎么读这些图，而不是只看热闹

每张对比图都按同一个顺序读：

1. 先看 noisy：输入噪声有多强，是否合理。
2. 再看 output：模型有没有去掉噪声。
3. 再看 clean：output 离答案还有多远。
4. 回头看指标：PSNR / SSIM 的变化是否能在图上解释。
5. 最后看副作用：边缘、纹理、颜色有没有被破坏。

如果出现下面情况，要谨慎：

- PSNR 提升，但图像明显过度平滑；
- SSIM 提升，但颜色偏了；
- output 看起来干净，但细节也被抹掉；
- 指标很好，但 noisy/clean 其实没有正确配对。

所以 Week 1 的正确读法是：

```text
表格给趋势；
三联图给直觉；
两者一致时，结论才更可信。
```

## 14. 每个实验到底在学什么

### 14.1 TinyCNN 学的是训练闭环

不要把 TinyCNN 看成真正要用的模型。它的价值是简单：

```text
数据能加载吗？
loss 能下降吗？
validation 能跑吗？
三联图能保存吗？
```

如果 TinyCNN 都跑不通，就不应该急着上 DnCNN / UNet。

### 14.2 DnCNN residual 学的是任务表达

去噪任务里，noisy 和 clean 差的是 noise。

所以 residual 写法更贴近问题：

```text
模型不必重新生成 clean；
模型只需要估计 noise；
denoised = noisy - noise_pred。
```

### 14.3 L1 / L2 学的是目标函数

模型只会追 loss。你换 loss，就是在换“你要求模型追什么”。

L2/MSE 和 PSNR 更一致；L1 有时视觉结构更自然。没有哪个永远正确，要结合数据和目标看。

### 14.4 Patch size 学的是上下文和代价

更大的 patch 给模型更多空间上下文，也给验证更多图像结构；但计算成本明显增加。

这对应真实训练中的常见取舍：

```text
更大 patch / 更大 batch / 更深模型
  -> 可能更好
  -> 也更慢、更吃显存
```

### 14.5 噪声模型学的是实验公平性

如果 Gaussian 输入本来更脏，shot/read 输入本来更干净，那么直接比较训练后指标是不公平的。

所以要先测：

```text
PSNR(noisy, clean)
SSIM(noisy, clean)
```

这一步训练前就能做。

### 14.6 Paired RGB dataset 学的是工程边界

进入真实数据时，最容易出错的是数据格式：

- noisy 和 clean 文件是否配对；
- 尺寸是否一致；
- crop 是否对齐；
- train / val 是否混在一起。

`PairedImageDenoiseDataset` 把这些问题集中到 dataset 层，训练主循环就不用重写。

## 15. 看三联图时的检查清单

每次打开 `vis/step_*.png`，都按这个顺序看：

1. noisy 的噪声强度是否合理；
2. output 是否比 noisy 更干净；
3. output 是否接近 clean；
4. 边缘有没有被抹掉；
5. 纹理有没有变成假纹理；
6. 颜色有没有偏；
7. 指标提升是否能在图上看出来。

如果 PSNR 提升但图像看起来更差，不要盲信指标。

## 16. Week 1 的通过标准

学完 Week 1 后，不只是“跑过命令”，而是要能把每一步为什么做讲清楚。下面是参考回答。

### 16.1 为什么先跑 TinyCNN？

因为 TinyCNN 足够简单，适合先验证训练链路，而不是追求最终效果。

在图像恢复项目里，一开始最容易出问题的不是模型不够强，而是基础链路没有跑通：

```text
dataset -> dataloader -> model -> loss -> backward -> optimizer -> validation -> visualization
```

TinyCNN 的价值在于：

- 结构简单，出问题时容易定位；
- 训练快，适合做 10 / 50 / 100 step probe；
- 能检查 loss 是否下降；
- 能检查 validation 是否正常；
- 能检查 noisy / output / clean 三联图是否生成；
- 能先建立“step 变多，output 逐渐接近 clean”的直觉。

所以 TinyCNN 不是最终目标，而是第一块试金石。

如果 TinyCNN 都跑不通，直接上 DnCNN、UNet 或 NAFNet 只会让问题更难定位。

### 16.2 为什么 DnCNN residual 更适合去噪？

去噪任务里，noisy 和 clean 的关系通常可以近似理解为：

```text
noisy = clean + noise
```

也就是说，noisy 本来就包含大部分正确图像内容，和 clean 并不是完全不同的东西。模型真正需要处理的是“哪些部分是噪声，应该去掉”。

Residual denoise 的写法是：

```text
noise_pred = net(noisy)
denoised = noisy - noise_pred
```

这让模型学习的是 noisy 和 clean 之间的差值，也就是 noise。

相比直接生成整张 clean 图，预测噪声更贴近任务本质：

- 输入 noisy 已经接近 clean；
- 噪声通常是较小的残差；
- 模型只需要学习该减掉什么；
- 优化难度更低；
- 输出更容易保留原图结构。

所以 DnCNN residual 在当前 toy RGB 去噪里比 direct clean 更自然。

### 16.3 为什么 direct clean 更难？

Direct clean 的形式是：

```text
denoised = net(noisy)
```

模型要直接回答：

```text
这张干净图应该长什么样？
```

这比 residual 更难，因为模型不仅要去掉噪声，还要重建整张 clean 图的颜色、边缘、纹理和结构。

从任务角度看，direct clean 没有显式利用这个事实：

```text
noisy 已经很接近 clean
```

它把问题变成“从 noisy 生成 clean”，而 residual 把问题变成“从 noisy 里估计 noise 并减掉”。

实验里也能看到这个差异：

| 模型 | steps | final val PSNR | final val SSIM |
|---|---:|---:|---:|
| DnCNN residual | 300 | 31.15 | 0.8985 |
| DnCNN direct clean | 300 | 28.23 | 0.8876 |
| DnCNN residual long | 1000 | 33.13 | 0.9355 |
| DnCNN direct clean long | 1000 | 31.23 | 0.9144 |

direct clean 训练久了也会变好，但在这个任务里 residual 更容易优化。

### 16.4 L1 和 L2/MSE 分别偏向什么？

L1 和 L2/MSE 都是在衡量 output 和 clean 的差距，但惩罚方式不同。

L1：

```text
loss = mean(abs(output - clean))
```

L2/MSE：

```text
loss = mean((output - clean)^2)
```

直觉上：

- L1 对误差的惩罚更线性；
- L2/MSE 会更重地惩罚较大的误差；
- PSNR 和 MSE 直接相关，所以 L2/MSE 往往更利于 PSNR；
- L1 有时更容易保留结构和边缘，但不是绝对规律。

当前 toy 结果：

| Loss | final val PSNR | final val SSIM | 解读 |
|---|---:|---:|---|
| L1 | 31.1470 | 0.89850 | SSIM 略高 |
| L2/MSE | 31.5874 | 0.89452 | PSNR 略高 |

注意：L1 loss 和 L2 loss 的数值不能直接比较，因为它们不是同一把尺子。

### 16.5 patch 64 和 128 的取舍是什么？

Patch 是从图像里切出来的小块。patch size 决定模型一次看到多大的局部区域。

Patch 64 的优点：

- 训练快；
- 显存占用少；
- 适合快速 sanity check；
- 适合先确认代码、loss、验证和可视化都能跑通。

Patch 128 的优点：

- 模型看到的上下文更多；
- 能包含更多结构信息；
- 在当前 toy 实验里最终 PSNR / SSIM 更高。

实验结果：

| Patch size | wall time | final val PSNR | final val SSIM |
|---:|---:|---:|---:|
| 64 | 15.86s | 31.5874 | 0.89452 |
| 128 | 51.40s | 33.4745 | 0.93176 |

结论是：

```text
patch 64 用来快速检查；
patch 128 用来做更正式的 toy 对比；
真实数据上要结合显存、速度和效果决定。
```

### 16.6 为什么 shot/read noise 更接近 sensor？

Gaussian noise 的形式比较简单：

```text
noisy = clean + gaussian_noise
```

它默认噪声强度和图像内容关系不大。但真实 sensor 噪声不完全是这样。

更接近 sensor 的简化模型是：

```text
noisy = clean + shot_noise(clean) + read_noise
```

其中：

- shot noise 和信号强度有关，亮的地方可能噪声更明显；
- read noise 更像传感器读出过程中的固定电子噪声底；
- 这比纯 Gaussian 更接近相机成像里的噪声来源。

这一步不是说 shot/read 已经等于真实相机噪声，而是比固定 Gaussian 多了一层物理直觉。

所以它是从 toy synthetic noise 走向真实 sensor noise 的中间台阶。

### 16.7 为什么要先测 noisy 输入 baseline？

因为如果两个实验的输入噪声强度不同，直接比较训练后 PSNR / SSIM 是不公平的。

比如：

```text
模型 A 的输入本来很脏
模型 B 的输入本来比较干净
```

最后模型 B 指标更高，不一定代表模型 B 更强，也可能只是输入更容易。

所以训练前要先测：

```text
input PSNR = PSNR(noisy, clean)
input SSIM = SSIM(noisy, clean)
```

当前校准结果：

| 配置 | 噪声 | Input PSNR | Input SSIM |
|---|---|---:|---:|
| Gaussian | Gaussian | 24.2068 | 0.46247 |
| 校准后 shot/read | shot/read | 24.2036 | 0.45582 |

这样输入难度接近，后面比较模型输出才更有意义。

核心原则：

```text
先比较输入难度，再比较模型能力。
```

### 16.8 paired RGB 文件夹数据为什么是通往真实数据的关键一步？

toy RGB 数据是在代码里生成的：

```text
clean patch -> synthetic noise -> noisy patch
```

但真实数据通常是文件：

```text
noisy image file + clean image file
```

所以如果训练代码只能用 toy dataset，后面接 SIDD 这类真实数据时就会卡住。

paired RGB 文件夹数据的目标结构是：

```text
train/noisy/pair_00001.png
train/clean/pair_00001.png
val/noisy/pair_00001.png
val/clean/pair_00001.png
```

这一步的关键意义是把数据格式和训练逻辑分开：

- dataset 负责读 noisy/clean pair；
- training loop 继续负责 model、loss、optimizer、validation；
- 模型代码不用因为换真实数据而重写。

所以 paired RGB dataset adapter 是从 toy 任务走向真实数据的工程入口。

### 16.9 `metrics.csv`、checkpoint、三联图分别有什么用？

这三个产物回答的是不同问题。

`metrics.csv` 记录训练过程里的数字：

```text
step, train_loss, val_psnr, val_ssim
```

它用来观察：

- loss 是否下降；
- PSNR / SSIM 是否提升；
- 哪一步开始变慢或停滞；
- 不同实验之间如何对比。

checkpoint 保存模型参数：

```text
checkpoints/last.pth
checkpoints/best_psnr.pth
```

它用来：

- 恢复训练；
- 保存当前最好模型；
- 后续做推理或比较；
- 避免训练完模型却没有留下参数。

三联图通常是：

```text
noisy | output | clean
```

它用来判断：

- output 是否真的比 noisy 干净；
- output 是否接近 clean；
- 是否过度平滑；
- 是否有颜色偏移；
- 指标提升是否能在视觉上解释。

简单说：

```text
metrics.csv 看数字；
checkpoint 留模型；
三联图看图像质量。
```

三个都要看，不能只看其中一个。

### 16.10 为什么当前还不急着上 NAFNet / SID / RAW low-light？

因为当前阶段的目标不是追最强模型，而是建立可靠的学习和实验链路。

NAFNet、SID、RAW low-light 都更复杂：

- NAFNet 是更强的图像恢复模型，但结构和训练细节更复杂；
- SID 是 RAW low-light 数据，涉及 RAW 格式、曝光、黑电平、颜色处理等问题；
- RAW low-light 不只是去噪，还包含低光增强、动态范围、颜色映射等问题；
- 真实数据的配对、裁剪、归一化、评估都更容易出错。

如果还不能清楚解释 TinyCNN、DnCNN residual、loss、patch、baseline 和 paired RGB dataset，直接上这些会变成“模型名堆叠”，很难判断问题出在哪里。

当前更合理的顺序是：

```text
Toy RGB denoise
  -> paired RGB smoke
  -> tiny real paired RGB subset
  -> larger real RGB denoise
  -> stronger models
  -> RAW / low-light
```

所以不是不学 NAFNet / SID / RAW low-light，而是现在还没到最合适的位置。

## 17. Week 1 的最终通过标准

如果你能用自己的话讲清楚上面 10 个问题，Week 1 就不是“跑了一堆实验”，而是完成了从训练基础到真实数据入口前的完整准备。

真正通过 Week 1 的标志是：

```text
你知道每个实验为什么做；
你知道每个指标怎么看；
你知道每个产物有什么用；
你知道下一步为什么该进入真实 paired RGB 数据。
```

## 18. 关键词与核心参数验收表

| 关键词/参数 | 本周含义 | 调节方向与风险 | 公平验证方法 |
|---|---|---|---|
| direct clean | 网络直接预测干净图 | 任务直观，但需要同时学习低频内容与噪声修正 | 与 residual 使用相同数据、预算和 loss |
| residual denoise | 网络预测噪声/残差，再由输入减去 | 更聚焦高频修正，但 residual 符号写反会彻底错误 | 用 identity/零残差小样例验证语义 |
| `patch_size=64/128` | 训练 crop 的空间尺寸，单位 pixel | 大 patch 上下文多但显存/算力高；小 patch 样本多但上下文有限 | batch/step 不同时需说明总像素预算变化 |
| `depth=5` / `features=32` | DnCNN 层数 / 中间特征通道数 | 增大提升容量也增加参数、激活和 latency | 先 overfit 小样本，再做同协议消融 |
| L1 / MSE | 绝对误差 / 平方误差 | MSE 更重罚大误差，L1 对离群值更稳健 | 同 checkpoint 选择规则并看 PSNR、SSIM、纹理 |
| Gaussian sigma | 与信号无关的噪声标准差 | 越大任务越难；必须声明输入 `[0,1]` 或 `[0,255]` | 先测 noisy baseline，再评价模型 gain |
| shot/read noise | 随信号变化 / 近似信号无关的噪声项 | 更接近 Sensor 直觉，但本周仍是合成 RGB | 扫描亮度分桶的 variance/mean 关系 |

## 19. Week 1 面试五问

1. 为什么第一个实验选 TinyCNN/toy data，而不是直接上大模型和真实 RAW？
2. residual learning 在去噪中学什么，若残差符号弄反会怎样？
3. patch 变大为什么不等于结果必然更好，怎样控制总训练预算？
4. L1 与 MSE 对大误差、平滑和 PSNR 倾向有何差异？
5. 为什么必须先保存 noisy baseline、checkpoint、metrics.csv 和三联图？

参考回答应落到本周实际链路：toy 数据只证明训练闭环；它不证明 SIDD、RAW 或真实手机噪声上的泛化。

## 20. 教程闭环卡：先学任务表达，再学模型名字

本周输入、GT 和输出都是 `float32` RGB tensor，训练布局为 NCHW、数值范围为
`[0,1]`。toy noisy 由 clean 人工加噪得到，因此 GT 对齐是构造保证；它不是相机实拍
噪声。模型输出语义必须与配置一致：direct 模式预测 `clean`，residual 模式若预测噪声
`n_hat`，最终输出为 `clip(noisy-n_hat,0,1)`。

公平消融固定：数据/split、seed、训练 step、验证样本、metric 实现和 checkpoint 规则；
每次只改 model、loss、patch 或 noise 中一个因素。patch 从64增至128时，每样本像素变为4倍，
不能只固定 step 就声称算力预算相同；还要报告 batch、总像素和耗时。

调试顺序：先让1～5张图 overfit，再看 output/range，再查 residual 符号，最后才调容量。
关键权衡（trade-off）是：更强去噪通常会损失纹理；大 patch 提供上下文但增加显存；MSE 重罚大
误差但更可能趋向平均。本周证据为 `verified_synthetic`/toy smoke，paired 文件夹 smoke
只证明数据接口，Week 2 才进入公开真实 paired sRGB。

独立验收：手算一个2×2 residual 例子；预测 sigma、patch 和 loss 改变的方向；故意写反
residual 符号并解释图像/metric；最后用“背景—合同—实验—结果—边界”两分钟复述。
