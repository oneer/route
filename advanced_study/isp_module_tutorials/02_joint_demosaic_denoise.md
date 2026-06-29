# 联合去马赛克与去噪：为什么 Demosaic 和 Denoise 不应总是串行

## 模块定位

传统 pipeline 常见顺序是：

```text
Bayer RAW -> Denoise or Demosaic -> RGB -> further denoise / sharpen
```

但真实低光和高 ISO 场景下，Demosaic 与 Denoise 强耦合。先 demosaic 会把 RAW 噪声插值到 RGB 三通道，形成彩色伪影；先强 denoise 又可能破坏 Bayer 结构和边缘。

## 传统做法

### 串行 Demosaic

传统 demosaic 根据 Bayer pattern 插值缺失颜色。简单方法有 bilinear，更复杂的有边缘感知插值。核心假设是局部颜色和亮度变化相对平滑。

### 串行 Denoise

Denoise 可以在 RAW 域做，也可以在 RGB 域做。RAW 域更接近噪声物理，但只有一个颜色采样；RGB 域视觉直观，但噪声已经被 demosaic 改变。

## 瓶颈

1. Demosaic 会把单点噪声传播到多个 RGB 像素。
2. 彩色伪影常常来自 demosaic 和噪声互相放大。
3. 低光下边缘方向判断不可靠，边缘感知 demosaic 容易选错方向。
4. 后续 sharpening 会进一步放大 demosaic 伪影。

## 当前更先进的做法

### Joint Demosaic-Denoise

联合方法把两个问题一起求解：输入 noisy Bayer，输出 clean RGB 或 clean linear RGB。网络不被固定 demosaic 算法限制，可以同时学习颜色插值和噪声抑制。

典型流程：

```text
Noisy Bayer RAW
-> pack RGGB / CFA-aware encoding
-> joint reconstruction network
-> clean RGB / linear RGB
```

### RAW-aware 网络结构

先进方法会显式保留 CFA 信息。例如 RGGB pack 成 4 通道，或者使用适配不同 CFA 的扫描/注意力机制。Retinex-RAWMamba 这类近年方法强调低光 RAW 增强中 demosaic 和 denoise 的桥接，原因就是简单两阶段方法容易忽略 demosaic 在颜色恢复中的作用。

### 无训练或少训练方法

JDD-DoubleDIP 这类方法探索单张 RAW 上的联合 demosaic+denoise，不依赖大量训练数据。它不一定是工程部署首选，但说明这个问题本身是强耦合的。

## 工程注意点

- 网络输出如果是 sRGB，就把颜色、tone、demosaic 全混在一起，调试困难。
- 网络输出如果是 linear RGB，更容易接传统 CCM/tone。
- RAW pack 顺序必须和训练一致。
- 评价不能只看 PSNR，还要看 zipper artifact、false color、边缘彩边、纹理保真。

## 和本项目对应

- stage1：已有 demosaic，可加入噪声注入观察伪影。
- stage2：可训练 packed RAW 到 clean RGB 的小模型。
- stage3：可实现传统 demosaic + denoise baseline。
- stage4：部署时重点检查 pack order 和输出颜色空间。

## 练习

1. 在 stage1 对 RAW 注入噪声，再分别做 bilinear demosaic 和 OpenCV demosaic，观察彩色噪声。
2. 在 stage3 比较“先 denoise 后 demosaic”和“先 demosaic 后 denoise”。
3. 在 stage2 构造 toy Bayer 数据，训练一个小 U-Net 从 noisy Bayer pack 输出 clean RGB。
4. 做失败案例标注：zipper、false color、edge blur、color moire。

## 你应该掌握

Demosaic 不是孤立插值问题。高 ISO、低光和 AI-ISP 场景中，Demosaic、Denoise、Color Recovery 经常需要联合考虑。

