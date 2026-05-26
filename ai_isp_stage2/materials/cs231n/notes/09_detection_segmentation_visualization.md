# Lecture 9：目标检测、图像分割与可视化

## 这讲在讲什么

这讲覆盖检测、分割、CNN 可视化、对抗样本、DeepDream、style transfer。对当前 AI-ISP 主线，最有用的是“可视化和理解 CNN”。

## 核心概念

| 概念 | 解释 | 和本项目的关系 |
|---|---|---|
| Object detection | 找物体类别和位置 | 非当前主线 |
| Segmentation | 像素级分类 | 和像素级输出有形式相似 |
| Feature visualization | 看网络学到了什么 | 帮助理解 CNN 不是纯黑盒 |
| Adversarial examples | 小扰动导致模型错误 | 说明模型对输入扰动敏感 |
| Style transfer | 分离内容和风格表示 | 图像生成/增强方向相关 |

## 为什么检测/分割不是当前重点

检测输出框，分割输出类别 mask。我们现在的 denoise 输出 RGB 图：

```text
noisy RGB -> clean RGB
```

所以任务目标不同。但分割和图像恢复一样，都关心空间结构和像素级输出。

## CNN 可视化为什么有用

可视化帮助你理解：

- 低层卷积常关注边缘、颜色、纹理。
- 高层特征可能更语义化。
- 模型可能依赖你没想到的图像区域。

对于去噪，未来也可以可视化：

- residual noise prediction
- output - clean error map
- ROI failure cases

## 对抗样本的启发

对抗样本说明深度网络可能对很小扰动敏感。图像恢复模型也可能出现：

- 纹理误杀。
- 噪声残留。
- 伪纹理。
- 颜色漂移。

所以不能只看平均 PSNR，要看失败案例。

## 回到项目

当前建议重点看：

- 可视化网络输出。
- 三联图 noisy / output / clean。
- residual 输出和 error map。

可暂时跳过检测模型细节。

