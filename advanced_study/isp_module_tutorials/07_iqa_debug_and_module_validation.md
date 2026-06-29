# 画质评估与模块验证：PSNR/SSIM 之外的 ISP 调试方法

## 模块定位

ISP 模块学习不能只看“输出图好像还行”。每个模块都需要验证：

```text
输入是否正确
中间结果是否合理
指标是否解释得通
失败案例是否归因清楚
```

## 传统指标

### PSNR

衡量像素误差，适合 paired 数据。但 PSNR 高不代表颜色自然，也不代表纹理真实。

### SSIM

更关注结构相似，但对颜色、暗部噪声和局部伪影仍不充分。

### Delta E

适合颜色准确性，尤其是色卡和 CCM/AWB 验证。

## ISP 更需要看的现象

1. 暗部彩噪。
2. 高光 clipping。
3. false color。
4. zipper artifact。
5. halo。
6. 过锐化 ringing。
7. 过平滑纹理。
8. 白平衡漂移。
9. 局部 tone 不连续。
10. AI hallucination。

## 模块验证方法

### RAW 前端

看黑电平后暗场是否接近 0，看坏点 mask 是否误杀真实细节，看 LSC 后边缘噪声是否放大。

### Demosaic

看高频边缘、斜线、棋盘格、彩色细纹。不要只看自然图。

### Denoise

看平坦区噪声、边缘保留、纹理保真。最好同时看 crop 和 error map。

### AWB/CCM

看灰卡、肤色、天空、绿色植物和多光源场景。颜色问题要和曝光问题分开分析。

### Tone Mapping

看直方图、高光、暗部、局部对比和 halo。

### AI-ISP

看指标、视觉、失败分类、跨相机泛化和部署精度误差。

## 和本项目对应

- stage1：每个传统模块都应有 before/after、直方图、ROI。
- stage2：训练报告需要 metrics + crops + failure taxonomy。
- stage3：C++ 模块需要 Python reference 对齐和 benchmark。
- stage4：部署需要 PyTorch/ONNX/TensorRT 数值对齐和视觉对齐。

## 练习

1. 给 stage1 每个模块建立 3 个固定 ROI：暗部、边缘、高光。
2. 给 stage2 每次训练输出 8 张失败 crop，并按失败类型标注。
3. 给 stage3 每个 C++ 算子保存 max error、mean error、runtime。
4. 给 stage4 每种后端保存 error map 和 latency matrix。

## 你应该掌握

先进 ISP 学习的关键不是堆模型，而是能定位画质问题来自哪个模块、哪个数据域、哪个部署环节。没有验证体系，任何“先进算法”都很难可靠落地。

