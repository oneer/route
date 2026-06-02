# Week 0：神经网络训练基础

Week 0 的目标是补齐最小必要基础。这里不追求系统学完整机器学习，只服务一个问题：

```text
为什么训练能让一个图像恢复模型变好？
```

## 1. 先记住这一条链路

```text
noisy -> model -> output -> loss -> backward -> optimizer -> better model
```

![Week 0 训练 step 流程图](figures/week0_training_step_flow.png)

> 图说明：这张图把一次训练 step 拆成 `noisy -> model -> output -> loss -> backward -> optimizer`。重点看箭头方向：前半段是在生成输出，后半段是在根据错误更新模型参数。

对应到 RGB 去噪任务：

- `noisy`：带噪声的输入图；
- `clean`：希望模型接近的干净答案；
- `model`：带参数的函数；
- `output`：模型当前输出；
- `loss`：output 和 clean 的差距；
- `backward`：计算每个参数应该往哪个方向改；
- `optimizer`：真正更新参数；
- `validation`：用没参与训练的数据检查模型是否真的学到规律。

## 2. 监督学习是什么

本阶段的任务是监督学习，因为每个输入都有答案：

```text
输入：noisy image
答案：clean image
```

模型训练时不断做这件事：

```text
看 noisy -> 生成 output -> 和 clean 比较 -> 修改参数
```

你可以把它理解成反复做题和对答案。

## 3. 模型是什么

先不要把模型想得神秘。它就是一个带参数的函数：

```text
output = model(noisy, parameters)
```

训练前参数接近随机，所以输出通常不好。训练过程就是不断修改这些参数，让 output 更接近 clean。

## 4. Loss 是什么

Loss 是错误分数。

比如 L1 loss：

```text
loss = mean(abs(output - clean))
```

L2/MSE loss：

```text
loss = mean((output - clean)^2)
```

loss 越小，说明 output 和 clean 在这个定义下越接近。

注意：不同 loss 的数值不能直接比较大小。L1 的 `0.02` 和 L2 的 `0.0007` 不是同一把尺子。

## 5. Backward 和 Optimizer 是什么

训练核心代码通常长这样：

```python
output = model(noisy)
loss = criterion(output, clean)
loss.backward()
optimizer.step()
```

含义是：

- forward：用当前参数生成 output；
- loss：计算 output 错在哪里；
- backward：计算参数怎么改能让 loss 下降；
- optimizer.step：实际修改参数。

这四步就是训练闭环。

## 6. 为什么要分 train 和 validation

训练集用来更新参数。

验证集不参与更新，只用来检查模型是否真的学到了规律。

如果只看训练集，模型可能只是记住了训练样本；验证集更像小测验，能检查模型有没有泛化能力。

![train 和 validation 分工](figures/week0_train_validation_split.png)

> 图说明：这张图说明 train 和 validation 的分工。train 数据会参与 `backward` 和参数更新；validation 数据只负责检查模型在没见过的数据上表现如何，不能拿来改参数。

## 7. 图像为什么用 patch

Patch 是图像小块，比如 64x64 或 128x128。

用 patch 的原因：

- 训练更快；
- 显存占用更少；
- 一张图可以切出很多样本；
- 去噪主要依赖局部邻域，适合先从小块学起。

## 8. 学完后要能回答的问题

学完 Week 0 后，至少能回答：

1. noisy 和 clean 分别是什么？
2. model 为什么说是带参数的函数？
3. output 是什么？
4. loss 为什么能指导训练？
5. backward 在算什么？
6. optimizer 在改什么？
7. validation 为什么不能参与训练？
8. patch 为什么常用于图像训练？
9. PSNR / SSIM 是训练目标还是验证指标？
10. 为什么模型训练多 step 后可能变好？

## 9. 参考回答

### 1. noisy 和 clean 分别是什么？

`noisy` 是模型的输入，也就是带噪声、有问题的图像。

`clean` 是训练时的答案，也就是希望模型输出接近的干净图像。

在 toy RGB 去噪里，noisy 通常是从 clean 加噪声得到的：

```text
noisy = clean + noise
```

所以模型学的是：

```text
noisy -> clean
```

### 2. model 为什么说是带参数的函数？

因为模型接收输入，然后产生输出，像一个函数：

```text
output = model(noisy)
```

但它不是固定函数。模型内部有很多可以被训练修改的数字，这些数字就是参数。

更完整地说：

```text
output = model(noisy, parameters)
```

训练的本质就是不断调整 `parameters`，让模型输出越来越接近 clean。

### 3. output 是什么？

`output` 是模型当前给出的结果。

在 RGB 去噪任务里：

```text
output = model(noisy)
```

它应该是一张去噪后的 RGB 图像。训练刚开始时，output 可能很差；训练一段时间后，output 应该逐渐接近 clean。

### 4. loss 为什么能指导训练？

loss 把“模型输出错得有多厉害”变成一个数字。

比如：

```text
loss = mean(abs(output - clean))
```

如果 output 和 clean 差得远，loss 就大；如果 output 接近 clean，loss 就小。

训练要做的事情就是让 loss 变小。只要 loss 能表达“当前输出离答案有多远”，它就能给训练提供方向。

### 5. backward 在算什么？

`backward` 在计算每个参数对 loss 的影响。

更直观地说，它在问：

```text
如果这个参数稍微变大或变小，loss 会怎么变？
```

这会得到梯度。梯度告诉模型：哪些参数该往哪个方向改，loss 才可能下降。

### 6. optimizer 在改什么？

optimizer 真正修改模型参数。

`backward` 只是算出方向，`optimizer.step()` 才是实际更新：

```python
loss.backward()
optimizer.step()
```

比如 AdamW optimizer 会根据梯度和学习率，决定每个参数这一步改多少。

### 7. validation 为什么不能参与训练？

validation 是用来检查模型有没有真的学会，而不是用来教模型。

如果 validation 也参与训练，模型就等于提前看过考题，验证结果就不再可信。

所以：

- train set：用来更新参数；
- validation set：只用来评估模型；
- test set：更晚才用，用来做最终检查。

### 8. patch 为什么常用于图像训练？

patch 是从大图里切出来的小图块，比如 64x64 或 128x128。

图像训练常用 patch，因为：

- 大图太占显存，小 patch 更容易训练；
- 一张大图能切出很多 patch，样本更多；
- 去噪、去马赛克、锐化等任务主要依赖局部邻域；
- 小 patch 能更快验证训练流程是否正确。

所以 Week 1 先用 RGB patch，而不是一上来训练整张大图。

### 9. PSNR / SSIM 是训练目标还是验证指标？

在当前项目里，PSNR / SSIM 是验证指标，不是直接训练目标。

训练时直接优化的是 loss，比如 L1 或 L2/MSE：

```text
训练目标：让 loss 变小
验证指标：看 PSNR / SSIM 是否变好
```

PSNR 和 MSE 有直接关系，所以用 L2/MSE 训练时，PSNR 往往更容易提高。

SSIM 更关注结构相似度，能补充 PSNR 只看像素误差的不足。

### 10. 为什么模型训练多 step 后可能变好？

每一个 step 都会做一次参数更新：

```text
noisy -> output -> loss -> backward -> optimizer.step()
```

step 变多，参数就有更多机会被修正。

如果数据、loss、模型和学习率设置合理，模型会逐渐学到从 noisy 到 clean 的规律，所以 output 可能越来越接近 clean。

但 step 不是越多越好。如果训练太久，模型也可能过拟合训练集，所以要看 validation 指标和可视化结果。

## 10. 通过标准

你不需要会推导公式，但要能复述：

```text
模型先用 noisy 生成 output；
loss 比较 output 和 clean；
backward 计算参数修改方向；
optimizer 更新参数；
validation 检查模型有没有真的学会。
```

能讲清楚这段，就可以进入 Week 1。

## 11. 训练闭环逐行拆解

Week 0 最重要的不是背概念，而是把训练代码看成一条能复述的流程。下面用图像去噪任务解释一次完整 step。

### 11.1 取出一批数据

训练时不是一次只看一张图，而是取一个 batch：

```python
for batch in train_loader:
    noisy = batch["noisy"]
    clean = batch["clean"]
```

这里可以理解成：

```text
noisy: [batch, 3, H, W]
clean: [batch, 3, H, W]
```

`3` 是 RGB 三个通道，`H/W` 是 patch 的高和宽。

### 11.2 前向传播

```python
output = model(noisy)
```

模型用当前参数处理 noisy，得到 output。此时模型还没有改参数，只是在“答题”。

### 11.3 计算 loss

```python
loss = criterion(output, clean)
```

loss 把 output 和 clean 的差距变成一个数字。这个数字越小，说明模型当前答案越接近标准答案。

### 11.4 清空旧梯度

```python
optimizer.zero_grad(set_to_none=True)
```

PyTorch 默认会累积梯度，所以每次新的 step 前要清掉上一轮的梯度。否则这一步的梯度会混进上一步的梯度，参数更新就不干净。

### 11.5 反向传播

```python
loss.backward()
```

这一步不是在更新参数，而是在计算梯度。它回答的是：

```text
每个参数对当前 loss 的影响是什么？
```

梯度可以理解成“修改建议”。

### 11.6 更新参数

```python
optimizer.step()
```

optimizer 根据梯度、学习率和自己的规则真正修改参数。参数被改过后，下一次 forward 的 output 就可能不同。

### 11.7 记录和验证

训练过程中会定期：

- 打印 train loss；
- 跑 validation；
- 保存 `metrics.csv`；
- 保存 checkpoint；
- 保存 noisy / output / clean 三联图。

这些东西不是装饰，它们对应不同问题：

| 产物 | 回答的问题 |
|---|---|
| train loss | 训练集上错误有没有下降 |
| val PSNR / SSIM | 没参与训练的数据上有没有变好 |
| checkpoint | 模型参数能不能保存和恢复 |
| 三联图 | 指标变好是否真的对应视觉变好 |

## 12. 常见误解

### 误解 1：loss 越小，图像一定越好

不一定。loss 只代表某个数学定义下的误差更小。

比如 L2/MSE 更关注像素均方误差，可能带来更高 PSNR；但图像可能更平滑。图像恢复里必须同时看：

- loss；
- PSNR；
- SSIM；
- 三联图。

### 误解 2：validation 指标越高，就一定能上真实数据

不一定。validation 只代表当前验证集。如果 toy 数据和真实数据差距很大，toy validation 很好也不代表真实数据会好。

所以阶段二才会从：

```text
toy RGB -> calibrated synthetic noise -> paired RGB smoke -> real paired RGB
```

一步一步过渡。

### 误解 3：训练更多 step 一定更好

不一定。更多 step 给了模型更多修改参数的机会，但也可能让模型记住训练集细节，导致 validation 不再提升甚至下降。

判断是否继续训练，看：

- train loss 是否还在下降；
- val PSNR / SSIM 是否还在提升；
- 三联图是否出现过度平滑、颜色偏移、伪纹理。

### 误解 4：模型越大越好

不一定。更大的模型可能表达能力更强，但也更慢、更吃显存、更容易过拟合，部署也更困难。

阶段二先用 TinyCNN 和小 DnCNN，是为了把问题看清楚，而不是一开始就堆模型。

## 13. PSNR 和 SSIM 的直觉

![loss、PSNR、SSIM 和三联图分别看什么](figures/week0_metrics_visual_roles.png)

> 图说明：这张图把四种观察角度放在一起。loss 看训练误差是否下降，PSNR 看像素级误差，SSIM 看结构相似度，三联图用人眼检查 noisy、output、clean 之间的真实差别。

### 13.1 PSNR

PSNR 和 MSE 相关。MSE 越小，PSNR 通常越高。

直觉：

```text
PSNR 高 = 像素误差整体小
```

但它不一定完全符合人眼感受。两张图可能 PSNR 接近，但纹理和边缘观感不同。

### 13.2 SSIM

SSIM 更关注结构相似度。

直觉：

```text
SSIM 高 = 结构、亮度、对比度更像 clean
```

所以图像恢复里通常同时看 PSNR 和 SSIM。

### 13.3 本项目怎么用

当前项目里：

```text
训练时优化 loss
验证时记录 PSNR / SSIM
最终还要看三联图
```

不要把 PSNR / SSIM 当成唯一答案。

## 14. 你应该能手写的最小训练伪代码

学完 Week 0 后，最好能不看代码写出下面这个结构：

```python
for step, batch in enumerate(train_loader):
    noisy = batch["noisy"].to(device)
    clean = batch["clean"].to(device)

    optimizer.zero_grad(set_to_none=True)
    output = model(noisy)
    loss = criterion(output, clean)
    loss.backward()
    optimizer.step()

    if step % val_every == 0:
        metrics = validate(model, val_loader, device)
        save_checkpoint(...)
        save_triplet(noisy, output, clean, ...)
```

你不需要记住每个 API，但要知道每一行在训练闭环里负责什么。

## 15. Week 0 到 Week 1 的连接

Week 0 解决的是“训练为什么能让模型变好”。

Week 1 会把这条链路放进真实项目里：

```text
ToyRGBDenoiseDataset
  -> TinyCNN / DnCNN
  -> L1 / L2 loss
  -> train / validation
  -> PSNR / SSIM
  -> noisy / output / clean visualization
```

也就是说，Week 1 不是新开一条线，而是 Week 0 的具体落地。
