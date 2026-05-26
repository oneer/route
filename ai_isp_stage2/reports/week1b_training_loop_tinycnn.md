# Week 1B：TinyCNN 训练闭环

Week 1B 只用 TinyCNN，不讲复杂模型。

目标是理解：

```text
为什么 step 变多，模型输出会变好？
```

## 1. TinyCNN 先当成一个函数

先不要管 CNN 名字。把 TinyCNN 看成：

```text
output = f(noisy, parameters)
```

这里 `parameters` 是模型内部会被训练改变的数字。训练前这些数字基本是随机的，所以输出不好。

## 2. 每一步训练在干嘛

一次 step：

```text
noisy -> TinyCNN -> output
output 和 clean 比较 -> loss
根据 loss 计算参数怎么改 -> update
```

代码对应：

```python
output = model(noisy)
loss = criterion(output, clean)
loss.backward()
optimizer.step()
```

这四行就是训练闭环的核心。

## 3. loss 怎么理解

本项目用 L1 loss：

```text
loss = average(abs(output - clean))
```

它问的是：模型输出和 clean 答案平均差多少。

loss 越小，说明 output 越接近 clean。

## 4. 为什么要跑 10 / 50 / 100 step

这是为了看模型从不会到会的过程。

| step | train loss | val PSNR | val SSIM | 状态 |
|---:|---:|---:|---:|---|
| 10 | 0.170468 | 13.49 | 0.6601 | 刚开始学 |
| 50 | 0.083647 | 18.19 | 0.7377 | 学到一点 |
| 100 | 0.034625 | 26.73 | 0.8526 | 明显变好 |

这说明训练不是背模型名，而是参数被反复修正。

## 5. validation 是什么

训练集用于更新参数。验证集不更新参数，只检查模型是否真的学到规律。

如果只看训练集，模型可能只是记住题目。验证集更像小测验。

## 6. 你应该跑的命令

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_10.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

然后看：

```text
ai_isp_stage2/runs/toy_rgb_denoise_tiny_100_probe/metrics.csv
ai_isp_stage2/runs/toy_rgb_denoise_tiny_100_probe/vis/
```

## 7. 今天只需要掌握

1. 模型是带参数的函数。
2. loss 是错误分数。
3. backward 计算参数该怎么改。
4. optimizer 真正更新参数。
5. step 多了，参数有更多机会被修正。
6. 验证集用来检查模型有没有泛化。

下一步再引入 DnCNN。

