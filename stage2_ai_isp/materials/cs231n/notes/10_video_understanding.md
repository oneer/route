# Lecture 10：视频理解

## 这讲在讲什么

这讲讨论视频分类、3D CNN、two-stream networks、多模态视频理解。它处理的是时间维度上的视觉信息。

## 核心概念

| 概念 | 解释 | 和 AI-ISP 的关系 |
|---|---|---|
| Video classification | 对一段视频识别类别 | 非当前主线 |
| 3D CNN | 在 H/W/T 三个维度卷积 | 可用于视频降噪 |
| Two-stream | RGB stream + motion stream | 可类比图像内容和运动信息 |
| Temporal modeling | 建模帧间关系 | 视频 ISP 很重要 |

## 为什么当前先跳过

Stage 2 当前是单帧 RGB denoise。视频理解需要额外考虑：

- 帧间对齐。
- 运动补偿。
- 时序一致性。
- latency。
- 显存和吞吐。

这些会大幅增加复杂度。

## 和 AI-ISP 的潜在关系

后续做视频 ISP 时会遇到：

- temporal denoise
- multi-frame super-resolution
- burst photography
- video low-light enhancement
- flicker control

多帧方法可能比单帧更强，因为噪声随机但真实结构跨帧稳定。不过也会引入运动 ghosting。

## 最小带走

1. 单帧图像恢复先把 CNN / loss / validation 学稳。
2. 视频任务多了时间维度，难点是运动和一致性。
3. AI-ISP 端侧视频部署会更看重速度和延迟。

