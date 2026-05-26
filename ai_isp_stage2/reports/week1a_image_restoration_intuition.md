# Week 1A：图像恢复最小直觉

Week 1A 不讲 DnCNN，也不讲 UNet。只讲一件事：

```text
有问题的图像 -> 一个函数 -> 更接近答案的图像
```

## 1. noisy 是什么

`noisy` 是带噪声的输入图。它不是随机垃圾图，而是在 clean 图上加了噪声：

```text
noisy = clean + noise
```

在本项目里，噪声是合成 Gaussian noise：

```text
sigma ~ Uniform(0.03, 0.12)
noisy = clamp(clean + N(0, sigma), 0, 1)
```

## 2. clean 是什么

`clean` 是标准答案，也就是模型希望输出接近的图。

因为噪声是我们自己加的，所以 clean 和 noisy 天然对齐。这叫 paired data：

```text
noisy 输入
clean 答案
```

真实数据里 clean 往往很难得到，所以先用 toy 数据学习训练逻辑。

## 3. output 是什么

`output` 是模型当前给出的答案：

```text
output = model(noisy)
```

刚开始训练时，模型参数是随机的，output 不一定像 clean。随着训练进行，output 会逐渐接近 clean。

## 4. 为什么用 patch

Patch 是图像小块，比如 64x64。

用 patch 的原因：

- 训练快。
- 占显存少。
- 一张图能切出很多样本。
- 去噪主要依赖局部邻域，适合先从小块学起。

## 5. 三联图怎么看

训练会保存：

```text
noisy / output / clean
```

看图顺序：

1. noisy：输入问题有多脏？
2. output：模型修到了什么程度？
3. clean：标准答案长什么样？

不要只看 PSNR。主观图能告诉你模型是否过平滑、偏色、残留噪声或制造假纹理。

## 6. 今天只需要掌握

1. noisy 是输入。
2. clean 是答案。
3. output 是模型当前答案。
4. 图像恢复就是让 output 接近 clean。
5. patch 是为了让训练更轻、更快。
6. 三联图比单个指标更直观。

下一步再学：训练怎么让 output 变好。

