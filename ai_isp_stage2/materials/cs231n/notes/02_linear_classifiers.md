# Lecture 2：线性分类器进行图像分类

## 0. 这讲在讲什么

这讲从图像分类开始，讲三件事：

1. 图像分类为什么对机器很难。
2. 什么是 data-driven approach。
3. 两个最基础的分类器：kNN 和 linear classifier。

虽然这讲讲的是分类，不是去噪，但它非常重要。因为它第一次把机器学习的核心链路讲出来：

```text
data -> model -> score/output -> loss -> optimization
```

我们 Stage 2 的图像恢复也是同一条链，只是输出从“类别分数”变成了“去噪后的图像”。

## 1. 图像分类任务是什么

图像分类的输入是一张图像，输出是一个预定义类别。

例如：

```text
image -> cat / truck / airplane / dog / ...
```

人类看图时直接看到语义：猫、车、飞机。但计算机看到的是数字。

一张 800x600 的 RGB 图像，在机器里是：

```text
800 x 600 x 3 tensor
```

每个像素通常是 0 到 255 之间的数。RGB 三个通道分别表示红、绿、蓝。

这里出现了一个关键问题：

```text
人看到语义，机器看到数字矩阵。
```

这就是视觉任务的语义鸿沟。

## 2. 图像分类为什么难

同一只猫，对人来说还是同一只猫；但对机器来说，只要像素变了，它就是一个新的数字点。

常见困难：

| 困难 | 解释 | 和 AI-ISP 的关系 |
|---|---|---|
| Viewpoint variation | 相机角度一变，像素整体变化 | 拍摄角度影响图像统计 |
| Illumination | 光照变化导致 RGB 值变化 | ISP 里 AWB / tone 都在处理光照影响 |
| Scale variation | 物体大小变化 | patch 训练也会遇到尺度问题 |
| Occlusion | 物体被遮挡 | 图像恢复中也会遇到局部信息缺失 |
| Deformation | 物体形状变化 | 纹理/边缘形态不是固定模板 |
| Intra-class variation | 同类物体差异很大 | 不同 sensor / ISO 下噪声也差异很大 |
| Background clutter | 背景复杂 | 图像恢复里背景纹理可能被误当噪声 |
| Context | 上下文影响判断 | 图像质量评价也常依赖语义区域 |

课堂上用猫举例：猫换角度、换光照、被遮挡、变形、品种不同，像素都可能变化很大，但语义仍是“猫”。

对 AI-ISP 来说也一样：真实噪声、颜色、光照、纹理并不简单。手写规则很难覆盖全部场景，所以后面才需要学习式方法。

## 3. 为什么不用硬编码规则

传统算法喜欢写规则：

```text
if condition:
    do something
else:
    do something else
```

比如早期视觉方法可能先做边缘检测，再找角点、模式、形状，最后判断类别。

问题是：

1. 每个类别都要手写规则。
2. 场景变化太多，规则很难扩展。
3. 规则对光照、视角、遮挡、背景非常敏感。

所以机器学习采用 data-driven approach。

## 4. Data-driven approach 是什么

数据驱动方法分三步：

```text
1. 收集图像和标签
2. 用训练数据训练模型
3. 在新图像上预测标签
```

这和手写规则不同。我们不是告诉机器“猫有什么边缘规则”，而是给它大量猫和非猫的例子，让模型从数据中学习映射。

分类中：

```text
image -> label
```

图像恢复中：

```text
noisy image -> clean image
```

两者都是 data-driven，只是监督信号不同。

## 5. kNN：最简单的数据驱动分类器

kNN 的思想非常朴素：

```text
训练阶段：记住所有训练图像和标签
预测阶段：找到和测试图像最像的训练图像，输出它的标签
```

如果 `k=1`，就是 nearest neighbor。

如果 `k>1`，就是 k-nearest neighbors，用最近的 k 个样本投票。

## 6. 图像之间怎么比较距离

kNN 需要距离函数。课堂里讲了 L1 和 L2。

### L1 distance

L1 距离是逐像素相减，取绝对值，再求和：

```text
L1(I1, I2) = sum(abs(I1 - I2))
```

它也叫 Manhattan distance。

直觉：

```text
每个像素差多少，加起来
```

### L2 distance

L2 距离是平方差求和再开方：

```text
L2(I1, I2) = sqrt(sum((I1 - I2)^2))
```

直觉：

```text
大的差异会被平方放大
```

### L1 和 L2 的区别

课堂里用几何图解释：

- L1 的等距离轮廓像菱形，更依赖坐标轴方向。
- L2 的等距离轮廓像圆，对旋转更不敏感。

这说明距离函数本身会影响模型判断。

对图像恢复也有对应关系：

- L1 loss 常让结果更稳，不容易被少数大误差带偏。
- L2 / MSE 对大误差惩罚更重，常和 PSNR 关系更近，但可能更平滑。

所以后面我们做 L1 vs L2 loss 对比时，就是在延续这里的距离 / 损失函数直觉。

## 7. kNN 的计算复杂度问题

kNN 很容易理解，但工程上不理想。

训练阶段：

```text
几乎不做事，只保存数据
```

预测阶段：

```text
每张测试图都要和所有训练图比较
```

如果训练集有 N 张图，预测一张图至少要做 O(N) 次比较。

这和我们希望的系统相反。实际部署常希望：

```text
训练慢一点可以接受，预测必须快
```

AI-ISP 更是如此。相机 pipeline 需要实时处理图像，不可能每次推理都和大量训练样本逐一比较。

## 8. kNN 的决策边界和异常点

课堂里展示了二维平面上的点，每个颜色代表一个类别。

1-NN 会给每个训练点周围划一块区域。如果某个点是异常点，它可能制造一个不合理的大区域。

kNN 用多个邻居投票，可以让结果更鲁棒。但 k 太大也可能过度平滑边界。

这引出一个重要概念：超参数。

## 9. Hyperparameter 是什么

超参数是训练前由人设置的选择，不是模型自动学出来的参数。

kNN 中常见超参数：

- `k`
- distance function: L1 / L2

深度学习中也有很多超参数：

- learning rate
- batch size
- weight decay
- patch size
- model depth
- loss type

这些超参数会影响结果，需要调。

## 10. 训练集、验证集、测试集

课堂强调：不能直接用测试集调超参数。

错误做法：

```text
在测试集上试很多 k，选测试集最好的
```

这相当于作弊，因为测试集已经参与选择了。

更合理的做法：

```text
train set: 训练模型
validation set: 选择超参数
test set: 最后一次评估
```

如果数据不大，可以用 cross-validation：

```text
把训练集分成多折
每次拿一折做 validation
多次结果求平均
```

但大规模深度学习里，交叉验证太贵，所以常用一个固定 validation set。

本项目中：

```text
train_size: 参与训练
val_size: 不参与训练，只算 PSNR / SSIM
```

这就是同一个思想。

## 11. CIFAR-10 例子说明什么

课堂里用 CIFAR-10 演示 kNN。

CIFAR-10 有 10 类，例如 airplane、automobile、bird、cat、deer、dog、frog、horse、ship、truck。

kNN 可以明显超过随机猜测，但仍然错很多。原因是它按像素距离比较图像，而像素距离不等于语义距离。

例如：

```text
颜色相似的图像，像素距离可能小
但语义类别可能完全不同
```

这说明“直接在原始像素上比较距离”不是好的视觉理解方式。

对 AI-ISP 的启发：

```text
单纯像素指标也不等于主观画质
```

所以后面不仅看 PSNR / SSIM，还要看三联图和 failure case。

## 12. 为什么引入线性分类器

kNN 没有真正学习一个参数化模型，只是记住数据。

线性分类器开始学习参数：

```text
score = W x + b
```

其中：

- `x` 是输入图像拉平成的向量。
- `W` 是权重矩阵。
- `b` 是偏置。
- `score` 是每个类别的分数。

如果图像是 32x32x3，拉平成向量后长度是：

```text
32 * 32 * 3 = 3072
```

如果有 10 个类别，那么：

```text
W shape = 10 x 3072
b shape = 10
score shape = 10
```

这就是参数化模型。

## 13. 线性分类器的三个视角

### 代数视角

```text
score = W x + b
```

输入数字向量，输出类别分数。

### 视觉模板视角

`W` 的每一行可以看作某个类别的模板。图像和模板越匹配，该类别得分越高。

课堂里展示了 CIFAR-10 上学习到的模板，例如汽车模板可能隐约像车的平均形状。

但线性模板有局限：一个类别内部变化太大时，单一模板很难表达。

### 几何视角

线性分类器在特征空间中学习超平面，把不同类别分开。

二维时是线，三维时是平面，高维时是超平面。

偏置 `b` 的作用是让分割线不必经过原点。

## 14. 线性分类器的局限

线性分类器只能画线性边界。

如果类别分布像 XOR、圆环、多块区域，线性边界就分不开。

这也是为什么后面要引入神经网络：

```text
多层线性变换 + 非线性激活
```

可以表达更复杂的边界。

对我们项目来说，TinyCNN / DnCNN 就是更复杂的可学习函数，不再只是一个 `Wx + b`。

## 15. Score、logit、probability

线性分类器输出的是 score：

```text
scores = W x + b
```

这些分数没有固定范围，可以是负数，也可以很大。

Softmax 把分数变成概率：

```text
p(class k | x) = exp(score_k) / sum_j exp(score_j)
```

这样每个类别概率都是正数，且总和为 1。

在深度学习里，Softmax 前的原始分数常叫 logits。

## 16. Softmax loss / Cross entropy

我们希望正确类别概率越大越好。

如果正确类别概率是 `p_correct`，那么 loss 常写成：

```text
loss = -log(p_correct)
```

如果模型给正确类别很高概率，loss 小。

如果模型给正确类别很低概率，loss 大。

这就是分类里的 cross entropy loss。

图像恢复里不用 Softmax loss，因为目标不是类别概率，而是输出图像。因此我们常用：

```text
L1 = mean(abs(output - clean))
L2 = mean((output - clean)^2)
```

但共同点一样：

```text
loss 衡量模型输出和目标之间的不满意程度
```

## 17. 本讲和 Stage 2 的对应关系

| Lecture 2 概念 | Stage 2 对应 |
|---|---|
| image tensor | RGB patch tensor |
| label | clean image target |
| classifier | denoise model |
| score | output image |
| loss | L1 / L2 image loss |
| hyperparameter | steps / lr / patch size / model depth |
| validation set | val PSNR / SSIM |
| linear classifier | 神经网络的基础构件 |
| Softmax loss | 分类 loss 的例子，用来理解 loss |

注意：这张表不是说分类和去噪完全一样，而是说训练思想相通。

## 18. 本讲你要真正掌握什么

1. 图像对机器来说是 tensor，不是语义。
2. 图像分类难在像素变化大但语义不变。
3. Data-driven approach 用数据训练模型，而不是手写所有规则。
4. kNN 是最简单的数据驱动方法，但预测慢、泛化有限。
5. L1 / L2 是距离函数，也能帮助理解图像恢复 loss。
6. 超参数需要用 validation set 调，不能偷看 test set。
7. 线性分类器是参数化模型：`score = W x + b`。
8. Softmax 把分数变成概率。
9. Cross entropy 衡量分类输出和正确标签的差距。
10. Stage 2 的去噪训练也遵循 `input -> model -> loss -> update`。

## 19. 回到项目

看：

- `ai_isp_stage2/ai_isp/data/toy_rgb_dataset.py`
- `ai_isp_stage2/ai_isp/models/tiny_cnn.py`
- `ai_isp_stage2/ai_isp/engine/train.py`
- `ai_isp_stage2/reports/week1b_training_loop_tinycnn.md`

问题：

1. noisy / clean 在代码里是什么 shape？
2. TinyCNN 里的可学习参数在哪里？
3. 去噪任务里的 output 和 target 分别是什么？
4. 本项目的 validation set 对应课堂里的哪个概念？
5. L1 loss 和课堂里的 L1 distance 有什么直觉联系？

