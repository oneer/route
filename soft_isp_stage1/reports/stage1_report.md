# 阶段 1 实验报告

## 1. 项目目标

从真实 RAW / DNG 输入开始，实现并解释一个基础 Soft-ISP Pipeline。

## 2. 样张说明

| 编号 | 场景 | 文件名 | 选择理由 |
|---|---|---|---|
| S01 | 日光室外 |  |  |
| S02 | 室内暖光 |  |  |
| S03 | 低光高 ISO |  |  |
| S04 | 高动态范围 |  |  |
| S05 | 高频纹理/纯色 |  |  |

## 3. Pipeline 结构

```text
RAW -> BLC -> DPC -> LSC -> Demosaic -> AWB -> CCM -> Tone -> sRGB
```

## 4. 模块实验

| 模块 | 输入 | 输出 | 核心参数 | 验证方法 | 失败场景 |
|---|---|---|---|---|---|
| BLC | RAW | RAW | black/white level | histogram / min-max | black level 错误 |
| DPC | RAW | RAW | threshold | 注入坏点 | 高频纹理误杀 |
| LSC | RAW | RAW | gain map | 四角亮度 / 噪声 | 边缘噪声放大 |
| Demosaic | RAW | RGB | Bayer pattern | OpenCV baseline | false color / zipper |
| AWB | RGB | RGB | R/B gain | gray world / ROI | 大面积纯色 / 混合光 |
| CCM | linear RGB | linear RGB | 3x3 matrix | Lab / DeltaE | 光源不匹配 |
| Tone | linear RGB | sRGB | gamma / curve | 亮度对比 | 高光压缩过度 |

## 5. 与参考输出差异

至少写 5 类差异，并解释可能原因。

1.
2.
3.
4.
5.

## 6. 阶段复盘

## 7. 面试复述笔记

