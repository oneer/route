# 先进 ISP 模块教程

这个目录不是学习路线，也不是论文列表，而是按 ISP/AI-ISP 模块组织的教程。目标是让你知道：当前比较先进的 ISP 模块一般怎么设计，为什么传统做法不够，AI 方法替代或增强了哪一段，以及如何在本项目 stage1-stage4 中做简化练习。

## 教程组织方式

每篇教程都按同一逻辑写：

1. 这个模块在 ISP pipeline 的位置。
2. 传统 ISP 怎么做。
3. 传统做法的瓶颈。
4. 当前更先进的做法是什么。
5. 工程实现时最容易踩什么坑。
6. 和本项目 stage1-stage4 怎么对应。
7. 可以马上做的练习。

## 当前模块

| 文件 | 模块 | 重点 |
|---|---|---|
| `00_advanced_isp_pipeline_overview.md` | 先进 ISP 总览 | 从传统串行 ISP 到 Hybrid ISP / Neural ISP |
| `01_raw_frontend_correction.md` | RAW 前端校正 | BLC、DPC、LSC、噪声模型、隐式校正 |
| `02_joint_demosaic_denoise.md` | 联合去马赛克与去噪 | 为什么 Demosaic 和 Denoise 不应总是串行 |
| `03_awb_color_ccm.md` | AWB 与颜色校正 | 从灰世界/CCM 到学习式颜色恒常性 |
| `04_hdr_merge_and_tone_mapping.md` | HDR 合成与 Tone Mapping | HDR+、局部 tone、联合 tone+denoise |
| `05_ai_isp_raw_to_rgb.md` | AI-ISP RAW 到 RGB | SID、DeepISP、Learned Smartphone ISP、RAW2RGB |
| `06_real_time_edge_isp.md` | 实时端侧 ISP | HDRNet、ONNX Runtime、TensorRT、CUDA 前后处理 |
| `07_iqa_debug_and_module_validation.md` | 画质评估与模块验证 | PSNR/SSIM 之外的 ISP 调试方法 |

## 推荐使用方式

先不要通读全部。每次围绕一个模块学习：

1. 先读对应教程。
2. 回到本项目找同名 stage 报告或代码。
3. 做教程里的一个最小练习。
4. 写一页模块复盘：输入、输出、失败案例、指标、下一步改进。

## 和论文目录的关系

`advanced_study/01_*` 到 `07_*` 目录更像论文和开源项目精读库；本目录是模块教程。建议先读这里，再按教程引用去读论文。

