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

### 5.1 五个训练关键词速查

`forward` 是模型做一次“答题”。输入 `noisy` 之后，模型用当前参数算出 `output`。这一步只负责生成结果，还没有修改模型。

`loss` 是对答案。把 `output` 和 `clean` 比较，得到一个错误分数。分数越小，说明模型输出在这个 loss 定义下越接近干净图。

`backward` 是分析错因。它根据 loss 反向计算每个参数对错误的影响，也就是梯度。梯度告诉模型：哪些参数往哪个方向改，loss 可能会下降。

`validation` 是小测验。它用不参与训练的数据检查模型效果，只评估 PSNR、SSIM、loss 或三联图，不做 `backward`，也不更新参数。

`checkpoint` 是存档。它把当前模型参数、训练 step、最好指标等保存下来，方便后面继续训练、复现实验，或者拿最好的一版模型做推理和对比。

一轮最小训练可以理解成：

```text
forward 生成答案
loss 对答案打分
backward 分析怎么改
optimizer.step 真正修改参数
validation 用没见过的数据考试
checkpoint 保存当前或最好模型
```

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

## 16. Week 0 在阶段二项目中的位置

新版阶段二不是只学习神经网络概念，而是要逐步形成一个可复现、可评估、可解释的 AI-ISP 图像恢复项目。

所以 Week 0 的作用不是“学完整深度学习”，而是先建立后面所有实验都要遵守的工程闭环：

```text
data -> model -> loss -> metric -> checkpoint -> visualization -> analysis
```

对应到后面的阶段二：

| Week 0 概念 | 后续项目里的作用 |
|---|---|
| data | SIDD paired RGB、pseudo RAW/RGGB、low-light 数据入口 |
| model | TinyCNN、DnCNN、UNet、NAFNet-lite |
| loss | L1、L2/MSE，以及后续可能扩展的结构类 loss |
| metric | PSNR、SSIM、参数量、checkpoint 大小、latency |
| checkpoint | 保存可复现实验结果，用于评估、导出 ONNX 和 C++ 推理 |
| visualization | triplet、error map、failure crop |
| analysis | 解释为什么某个模型更好、哪里失败、下一步怎么改 |

这条链路后面会反复出现。Week 1 的 toy denoise、Week 3 的 SIDD 模型对比、Week 6 的 pseudo RGGB baseline、Week 11/12 的 ONNX/C++ 验证，本质上都在回答同一个问题：

```text
这个实验的数据、模型、指标、产物和结论是否可信？
```

## 17. 一个合格 run 应该留下什么

阶段二后续每次训练都不要只看终端里最后一行指标。一个合格的实验 run 至少应该留下这些东西：

```text
run_name/
├── config.yaml 或对应配置文件
├── metrics.csv
├── checkpoints/
│   ├── last.pth
│   └── best_psnr.pth
├── previews 或 figures/
│   ├── noisy_output_clean.png
│   ├── error_map.png
│   └── failure_crop.png
└── 训练命令和简短结论
```

每个产物回答的问题不同：

| 产物 | 回答的问题 |
|---|---|
| config | 这个实验能不能复现 |
| metrics.csv | loss、PSNR、SSIM 是否随训练变好 |
| last.pth | 能不能从最后一步继续训练 |
| best_psnr.pth | 哪个 checkpoint 最适合评估或导出 |
| triplet 图 | 输出是否真的比 noisy 更接近 clean |
| error map | 错误主要集中在哪里 |
| failure crop | 面试时能不能解释模型失败原因 |
| 训练命令 | 别人能不能复跑同一个实验 |

如果一个实验只有一张最终输出图，但没有配置、指标和 checkpoint，它就不适合作为阶段二的正式证据。

## 18. 训练异常的第一轮排查表

Week 0 还要建立一个基本调试习惯：看到异常结果时，先定位问题属于数据、模型、loss、指标，还是可视化。

| 现象 | 常见原因 | 优先排查 |
|---|---|---|
| loss 不下降 | 学习率不合适、输入输出范围错、clean/noisy 不匹配 | 打印 tensor 范围，检查 batch 图 |
| train loss 下降但 val 不涨 | 过拟合、train/val 分布不同、验证集太小 | 看 validation triplet 和 metrics 曲线 |
| PSNR 涨但图像发糊 | L2/MSE 偏向平均结果，纹理被抹掉 | 看 crop、SSIM 和 error map |
| 图像偏色或发灰 | normalize / denormalize 错误，RGB/BGR 顺序错 | 检查保存图像前的通道和范围 |
| 输出几乎等于输入 | 模型学成 identity，噪声太弱或 loss 不敏感 | 对比 noisy baseline 和 output 指标 |
| 输出出现棋盘格/边缘异常 | 上采样、padding、crop 拼接问题 | 看边缘 crop 和模型结构 |
| val 指标大幅波动 | 验证样本太少，patch 随机性太强 | 固定 val set 和随机种子 |
| checkpoint 加载失败 | 模型结构或 key 不一致 | 检查 config、model name、state_dict key |

阶段二后面不要只说“模型效果不好”。更好的表达是：

```text
我先检查了数据范围和 noisy-clean 对齐；
再看 loss / PSNR / SSIM 曲线；
然后用 triplet、error map 和 crop 判断失败区域；
最后再决定是改数据、loss、模型还是训练配置。
```

## 19. Week 0 升级版通过标准

完成 Week 0 后，不要求你能推导反向传播公式，但要能做到下面这些：

1. 能手写一段最小训练伪代码，并说清每一行负责什么。
2. 能解释 `noisy`、`clean`、`output`、`loss`、`metric`、`checkpoint` 的关系。
3. 能说清 train set 和 validation set 为什么不能混用。
4. 能看懂一个 `metrics.csv`，判断训练是否在变好。
5. 能解释为什么只看 loss 不够，还要看 PSNR / SSIM / 三联图。
6. 能说清 `best_psnr.pth` 为什么后面可以用于评估、ONNX 导出和 C++ 推理。
7. 能根据异常现象做第一轮排查，而不是盲目换模型。
8. 能解释为什么 Week 1 先做 toy denoise，而不是直接上 NAFNet、Restormer 或真实 RAW。

如果这些都能讲清楚，Week 0 就不只是“神经网络基础”，而是阶段二所有训练实验的共同地基。

## 20. 关键词与训练参数验收表

| 关键词/参数 | 定义 | 为什么需要 | 调节或验证要点 |
|---|---|---|---|
| forward | 当前参数下从输入计算输出 | 建立可微的预测链路 | 检查输入/输出 shape、range 和有限性 |
| loss | 用于反向传播的标量目标 | 把“输出哪里错”转换为优化方向 | loss 下降不保证主观画质；需配 validation |
| gradient/backward | loss 对每个可训练参数的偏导 | 告诉 optimizer 参数应怎样变化 | 忘记清梯度会累积；NaN 先查输入、loss 和学习率 |
| learning rate | 每次更新的步长比例 | 控制收敛速度和稳定性 | 太大震荡/发散，太小学不动；不能脱离 optimizer 讨论 |
| batch size | 一次更新使用的样本数 | 影响梯度方差、吞吐和显存 | 改 batch 可能改变优化轨迹，公平实验需记录 |
| step / epoch | 一次参数更新 / 遍历一轮数据 | 定义训练预算 | 小数据随机采 patch 时二者不能随意等同 |
| seed | 随机数生成初始状态 | 提高数据采样和初始化的可复查性 | 单 seed 可复现不代表统计稳定，最终比较需多 seed |
| train/eval mode | 训练行为 / 推理行为 | Dropout、BatchNorm 等行为可能不同 | validation/export 前显式 `eval()` |

## 21. Week 0 面试五问

1. **Loss 与 metric 有何区别？** Loss 必须可用于优化；metric 服务评价，可能不可微。两者都不能单独替代视觉检查。
2. **为什么每步先清梯度？** PyTorch 默认累积梯度；若非有意做 gradient accumulation，会改变有效更新量。
3. **学习率过大/过小各有什么现象？** 过大表现为震荡、NaN 或质量倒退；过小表现为 loss/metric 长期几乎不动，应在相同数据和初始化下验证。
4. **为什么 validation 不参与更新？** 它用于估计未参与拟合的数据表现；若反向传播或反复按 validation 过度调参，会产生选择偏差。
5. **训练可复现需要记录什么？** 数据 manifest/split、config、seed、代码版本、环境、checkpoint 和指标实现；只记录最终 PSNR 不够。

## 22. 本周边界

Week 0 解释并验证最小训练机制，不产生真实 Camera 质量结论。Toy loss 下降只能证明代码可优化；模型泛化、SIDD 表现、RAW 物理真实性和部署性能由后续 Week 分别验收。

## 23. 从零复述卡：训练闭环为何按这个顺序

```text
Dataset 产出 noisy/clean batch
  -> model(noisy) 得到 output
  -> loss(output, clean) 把像素误差压成标量
  -> zero_grad 清除上一轮梯度
  -> backward 用链式法则求 d(loss)/d(parameter)
  -> optimizer.step 按 learning rate 更新参数
  -> validation 在 eval/no_grad 下产生独立指标与图像
```

设参数为 `θ`、学习率为 `η`，最简单的梯度下降写作
`θ_(t+1)=θ_t-η∇θL(θ_t)`。`η` 太大可能跨过低谷而震荡，太小则在固定 step
预算内几乎不动；因此 learning rate 必须与 optimizer、batch、loss 尺度一起记录。

本周建议的最小故障注入是故意删除 `zero_grad`。预期现象是梯度跨 step 累积、更新量改变；
若结果没有明显变化，继续打印 gradient norm，而不是直接断言“zero_grad 不重要”。完成后保存：
伪代码、一次正常曲线、一次故障曲线、排查结论。证据等级为
`verified_synthetic`（学习机制），不涉及 Camera 数据质量。学习权衡是更大的 batch 可降低
梯度方差却增加内存，并会改变相同 step 下看到的样本量。
