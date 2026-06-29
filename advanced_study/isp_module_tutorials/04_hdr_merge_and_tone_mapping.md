# HDR 合成与 Tone Mapping：从传统曲线到联合 Tone+Denoise

## 模块定位

HDR 和 Tone Mapping 处理动态范围问题：

```text
single/multi exposure linear image
-> HDR merge or exposure fusion
-> global/local tone mapping
-> display-referred image
```

在低光和高动态范围场景中，tone mapping 不只是“压亮度”，还会改变噪声可见性、局部对比度和颜色观感。

## 传统做法

### HDR Merge

多曝光或多帧输入先对齐，再融合。短曝光保高光，长曝光保暗部。融合权重通常考虑曝光是否饱和、噪声和对齐可信度。

### Global Tone Mapping

Reinhard、Filmic、ACES、S-curve 等全局曲线对所有像素使用同一映射。优点是稳定、快；缺点是局部控制弱。

### Local Tone Mapping

局部 tone mapping 根据邻域亮度调整压缩强度。可以保留局部对比，但容易产生 halo，并可能放大暗部噪声。

## 瓶颈

1. Tone mapping 会放大暗部噪声。
2. 多帧 HDR 如果对齐失败会 ghosting。
3. 全局 tone 容易让天空或暗部缺少层次。
4. 局部 tone 容易 halo 或过度 HDR 风格。

## 当前更先进的做法

### HDR+

HDR+ 代表系统级计算摄影：多张短曝光 RAW，通过对齐和鲁棒融合提升信噪比与动态范围，然后进入 tone mapping。它说明 HDR 不是单个曲线，而是采集、融合、降噪、显示协同。

### HDRNet

HDRNet 用低分辨率网络预测 bilateral grid，再对高分辨率图像做快速局部仿射变换。它的先进性在于：学习复杂增强行为，但用传统快速结构保证实时。

### Joint Tone Mapping and Denoising

近年也有联合 tone mapping 和 denoising 的 HDR enhancement 方法。动机很直接：tone mapping 会改变噪声可见性，如果先 denoise 再 tone，可能 tone 后噪声又被放大；联合优化可以让网络同时考虑压动态范围和抑噪。

## 工程注意点

- Tone mapping 前后的图像域不同，指标不能混用。
- HDR merge 要记录曝光时间、ISO、对齐方式。
- 局部 tone 要检查 halo 和暗部噪声。
- AI tone 模型必须限制输出稳定性，视频场景还要考虑时序闪烁。

## 和本项目对应

- stage1：global tone mapping、Gamma、直方图。
- stage2：可训练 low-light/tone enhancement 小网络。
- stage3：HDR merge、local tone mapping、tone LUT、性能优化。
- stage4：HDRNet 类结构适合低延迟部署。

## 练习

1. 在 stage3 比较 Reinhard、Filmic、ACES、percentile tone 的直方图变化。
2. 对低光 noisy 图先 denoise 后 tone，再先 tone 后 denoise，比较暗部。
3. 做一个简化 HDR merge，加上错误对齐，观察 ghosting。
4. 实现一个低分辨率 tone 参数预测 + 高分辨率 LUT 应用的 toy HDRNet。

## 你应该掌握

先进 HDR/Tone 模块的核心不是更花的曲线，而是把动态范围、噪声、局部对比、实时性和多帧对齐放在一起设计。

