# Burst Photography for High Dynamic Range and Low-Light Imaging on Mobile Cameras

## 精读版学习目标

读 HDR+ 要建立一个系统观：手机夜景和 HDR 不是单个 tone mapping 函数能解决的，而是从采集策略开始就已经设计好了。它把短曝光、多帧对齐、鲁棒融合、降噪和显示映射放在同一条链路里。对当前项目来说，它是 stage1 单帧 ISP 和 stage3 HDR/LTM 之间最重要的桥。

## 为什么不用一张长曝光

小传感器在低光下最大问题是信噪比低。直觉上可以拉长曝光，但手机手持拍摄会带来手抖和运动模糊；同时高光区域容易饱和。HDR+ 的思路是拍多张短曝光 RAW：短曝光减少模糊和高光溢出，多帧融合提高信噪比。

这个思想可以用一个简单关系理解：如果多帧噪声近似独立，平均 N 帧可以让随机噪声标准差大约下降到 `1 / sqrt(N)`。但真实场景中物体会动，所以不能无脑平均。

## 对齐为什么困难

多帧融合前必须对齐。难点是手机拍摄存在手抖、局部物体运动、滚动快门、噪声和曝光差异。如果对齐错误，融合后会出现 ghosting。HDR+ 的工程价值就在于它不是为了指标而融合，而是非常谨慎地判断哪些区域可以融合，哪些区域应该少融合或回退。

## 融合为什么要鲁棒

鲁棒融合的核心是“不要相信所有帧”。静态区域可以融合多帧来降噪；运动区域如果强行融合，会产生重影。工程上常见思路是根据对齐误差、局部相似性、噪声模型给不同帧不同权重。

可以把它理解为：

```text
output = weighted_sum(aligned_frames)
权重由噪声水平、对齐可信度、运动程度决定
```

这比简单平均多了一层“可信度估计”。

## 与传统 ISP 的关系

HDR+ 不是替代 ISP，而是把多帧 RAW 处理插入传统 ISP 前段。融合结果仍然需要 demosaic、AWB、CCM、tone mapping 等步骤。也就是说，stage1 的模块并没有消失，而是输入从单帧 RAW 变成了多帧融合后的更高质量 RAW/线性图像。

## 和本项目的具体练习路线

1. 在 `stage3_cpp_isp` 用已有 HDR toy 数据做 short/long merge，写清楚 merge 前后的动态范围。
2. 人为平移一张输入图，观察 naive averaging 的 ghosting。
3. 加入简单可信度权重：如果某个像素和参考帧差异太大，就降低它的融合权重。
4. 把 merge 结果接到 local tone mapping，比较全局 Reinhard 和局部 tone mapping 的视觉差异。

## 面试级复述

可以这样复述：HDR+ 用 burst 短曝光 RAW 解决手机低光和高动态范围问题。它通过参考帧选择、局部对齐和鲁棒融合，在避免手抖/运动重影的同时提高信噪比，并保留高光信息。融合后的结果再进入传统 ISP 和 tone mapping。它的启发是，计算摄影画质来自采集、对齐、融合和显示映射的系统协同，而不是单个后处理滤镜。

## 论文信息
- 作者：Samuel W. Hasinoff 等
- 会议/期刊：ACM Transactions on Graphics / SIGGRAPH Asia
- 年份：2016
- 论文链接：https://hdrplusdata.org/hdrplus.pdf
- 数据/项目链接：https://hdrplusdata.org/

## 为什么要读这篇

这篇是计算摄影和移动相机管线的经典代表。它说明了一个重要事实：很多“画质提升”不是单帧 ISP 能完成的，而是依赖多帧采集、对齐、融合、降噪和局部色调映射。它能帮助你把 stage1 的单帧 pipeline 扩展到 stage3 的 HDR merge 和 local tone mapping。

## 背景问题：它解决了什么痛点

手机传感器小，单帧低光噪声大，高光容易过曝。传统长曝光会导致手抖和运动模糊。HDR+ 的思路是拍一组欠曝短帧，通过 burst alignment 和 merge 同时降低噪声、保留高光、减轻手抖。

## 初学者预备知识

需要理解曝光、动态范围、RAW 噪声、图像配准、加权融合、局部 tone mapping。可以先看 `stage3_cpp_isp/reports/week7_ltm_hdr_toy.md`。

## 核心思想一句话

用多张短曝光 RAW 代替一张长曝光照片，通过对齐和鲁棒融合获得低噪声、高动态范围图像。

## 方法原理详解

HDR+ 的关键不是简单平均，而是先选择参考帧，再把其他帧对齐到参考帧。对齐后，多帧融合要考虑运动区域和噪声模型：静态区域可以融合更多帧来降噪，运动区域要降低错误帧权重，避免重影。融合结果仍然是线性高动态范围图像，后面还需要颜色处理和 tone mapping 才能显示。

这篇论文对 AI-ISP 的启发是：真实相机系统常常把“采集策略 + 传统算法 + 学习模型”作为整体优化对象。只训练单张 RGB 去噪模型，无法覆盖完整计算摄影问题。

## 网络结构或算法流程

1. 连续采集多帧短曝光 RAW。
2. 选择参考帧。
3. 对其他帧做局部或块级配准。
4. 根据噪声和运动一致性做鲁棒 merge。
5. 做 demosaic、颜色处理和局部 tone mapping。
6. 输出最终 JPEG/显示图。

## 损失函数 / 数据集 / 训练方式

不属于深度学习训练论文。HDR+ 数据集提供真实 burst RAW，可用于研究多帧融合、RAW 去噪、HDR 和 tone mapping。

## 实验结果如何理解

结果重点不是某个指标，而是低光噪声、高光保留、运动伪影和手持稳定性之间的权衡。阅读时要特别注意：多帧融合能显著降噪，但错误对齐会产生比噪声更刺眼的重影。

## 优点

- 把 RAW、多帧、HDR、降噪、tone mapping 串成完整系统。
- 非常贴近手机影像工程。
- 可直接启发 stage3 的 HDR merge 和 LTM 实验。

## 局限

- 系统复杂，完整复现成本高。
- 依赖 burst RAW 数据和精细配准。
- 不直接覆盖现代神经网络融合方法。

## 和当前项目 stage1-stage4 的对应关系

- stage1_soft_isp：理解 RAW 域处理和 tone mapping 的位置。
- stage2_ai_isp：可扩展为 RAW burst denoising 或多帧恢复任务。
- stage3_cpp_isp：对应 `hdr_merge` 和 `local_tone_mapping`。
- stage4_deploy_isp：多帧系统会放大内存、延迟和吞吐约束。

## 可以在本项目中复现或简化实现的练习

1. 用 stage3 的短/长曝光 toy 数据复现一次 weighted HDR merge。
2. 在静态 synthetic burst 上比较单帧、平均融合、带权融合的噪声变化。
3. 人为平移一帧，观察错误融合产生的 ghosting，并写失败案例报告。

## 阅读后应该掌握什么

你应该能解释：HDR 和低光画质提升不仅是 tone curve 问题，更是采集、对齐、融合和显示映射共同决定的系统问题。
