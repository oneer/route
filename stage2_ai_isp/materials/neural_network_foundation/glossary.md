# 神经网络术语表

这份术语表只解释 Stage 2 当前会遇到的词。

| 术语 | 人话解释 | 本项目例子 |
|---|---|---|
| Tensor | 多维数字数组 | RGB patch 是 `(3, 64, 64)` |
| Patch | 图像小块 | 64x64 RGB 小图 |
| Dataset | 出题器 | 生成 noisy / clean |
| DataLoader | 批量取题器 | 每次取 8 张 patch |
| Model | 带参数的函数 | TinyCNN / DnCNN |
| Parameter | 模型里会被训练改变的数字 | 卷积核权重 |
| Forward | 用当前参数算输出 | `output = model(noisy)` |
| Output | 模型答案 | denoised image |
| Target | 标准答案 | clean image |
| Loss | 错误分数 | `mean(abs(output - clean))` |
| Backward | 计算参数该怎么改 | `loss.backward()` |
| Gradient | loss 对参数的变化方向 | PyTorch 自动算 |
| Optimizer | 修改参数的算法 | AdamW |
| Step | 更新一次参数 | 一次训练迭代 |
| Epoch | 训练集大致过一遍 | 本项目主要按 step 控制 |
| Batch | 一次训练用的一组样本 | batch size = 8 |
| Learning rate | 每次参数更新步子多大 | `0.001` |
| Train set | 参与参数更新的数据 | train_size |
| Val set | 不参与训练，只检查效果 | val_size |
| PSNR | 像素误差指标 | 越高通常越接近 clean |
| SSIM | 结构相似度指标 | 越高结构越像 |
| CNN | 用卷积处理图像的神经网络 | TinyCNN / DnCNN |
| Convolution | 局部可学习滤波 | `nn.Conv2d` |
| Feature map | 中间特征图 | 32 个通道的中间结果 |
| Channel | 通道维度 | RGB 是 3 通道 |
| ReLU | 非线性激活函数 | `max(0, x)` |
| Residual | 差值 / 残差 | noisy - clean 近似噪声 |

