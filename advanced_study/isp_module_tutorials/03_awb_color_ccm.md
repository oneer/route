# AWB 与颜色校正：从灰世界/CCM 到学习式颜色恒常性

## 模块定位

颜色模块通常位于 demosaic 之后、tone mapping 之前，也可能部分发生在 RAW 域：

```text
linear RGB
-> AWB gain
-> color correction matrix
-> color space transform
-> tone/gamma/display
```

颜色是 ISP 中最容易“主观”和“工程化”的部分。它不只是数学还原，还涉及相机风格、肤色、光源、显示设备和用户偏好。

## 传统做法

### AWB

AWB 估计光源颜色，然后给 RGB 通道乘 gain：

```text
R' = R * gain_R
G' = G * gain_G
B' = B * gain_B
```

简单算法包括 Gray World、White Patch、Shades of Gray。它们依赖统计假设：场景平均颜色应接近灰色，或最亮区域应接近白色。

### CCM

CCM 用 3x3 矩阵把相机 RGB 转到目标颜色空间：

```text
[R', G', B']^T = M * [R, G, B]^T
```

CCM 通常由色卡标定得到，但不同光源下可能需要不同矩阵。

## 瓶颈

1. Gray World 在大面积单色场景失败，例如草地、夕阳、舞台灯。
2. White Patch 容易被高光、反射、噪声误导。
3. 单一 CCM 难以覆盖所有光源和传感器响应。
4. Tone mapping 后再评价颜色，容易把曝光和色彩问题混在一起。

## 当前更先进的做法

### 学习式 Color Constancy

用 CNN/Transformer 从图像估计光源或 AWB gain。相比手工统计，学习方法可以利用语义和上下文，例如知道天空、皮肤、墙面更可能是什么颜色。

### 局部颜色校正

传统 CCM 是全局矩阵，但真实场景可能有混合光源。先进方法可能做局部 white balance 或局部 color transform，但工程上要谨慎，避免同一物体颜色不一致。

### Neural ISP 中的颜色分支

DeepISP、RAW2RGB 网络通常会隐式学习 AWB/CCM/tone。但如果完全隐式，失败时很难判断是白平衡错还是 tone 错。因此工程上常保留中间 linear RGB 或显式颜色约束。

## 工程注意点

- AWB 最好在线性域理解，不要在 Gamma 后估计物理光源。
- CCM 应在正确白平衡和线性 RGB 上使用。
- 评估颜色要用色卡、肤色、灰卡和多光源场景。
- AI 模型输出好看，不代表颜色准确。

## 和本项目对应

- stage1：AWB、CCM、Delta E、色卡/参考图对比。
- stage2：可训练颜色增强或 white balance correction 小模型。
- stage3：C++ 实现 CCM、色彩矩阵、固定点或 LUT。
- stage4：部署时检查 RGB/BGR、range、gamma 是否一致。

## 练习

1. 在 stage1 对同一张图比较 Gray World、White Patch 和手动 gain。
2. 选择大面积绿色/暖光图，记录 AWB 失败原因。
3. 用色卡或参考图计算 CCM 前后的 Delta E。
4. 在 stage2 训练一个小模型预测 AWB gain，而不是直接输出增强图。

## 你应该掌握

颜色模块的先进方向不是单纯“用网络调色”，而是在物理颜色恒常性、相机标定和视觉偏好之间做可控平衡。

