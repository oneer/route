# 基于 Week 0-9 周报的阶段二升级说明

这份文档不是替代原来的周报，而是把原周报升级成更适合社招 3 年口径的项目叙事。

原周报的价值是“学习过程完整”；升级后的价值应该是“项目闭环完整、实验判断清楚、
工程落地方向明确”。

## 总体升级原则

```text
学习记录 -> 项目交付
模型训练 -> 算法对比
指标结果 -> 工程判断
RGB demo -> AI-ISP 场景
Python 实验 -> 部署验证
```

写简历和面试时，不要逐周流水账式复述，而要把 Week 0-9 收束成下面 5 个模块：

| 模块 | 对应周报 | 对外表达 |
|---|---|---|
| 数据与任务定义 | Week 1-2 | 构建 noisy-clean paired 图像恢复任务 |
| 模型 baseline | Week 1, 3, 5 | 建立 DnCNN / UNet / NAFNet-lite 对比 |
| 评估体系 | Week 4, 8 | PSNR/SSIM + triplet + error map + failure crop |
| AI-ISP 连接 | Week 6, 7 | pseudo RAW/RGGB、low-light enhancement |
| 工程升级 | 新增 Week 10+ | ONNX/C++、参数量、latency、IQ 指标 |

## Week 0：训练基础

原内容：理解神经网络训练、loss、optimizer、validation。

升级表达：

```text
梳理图像恢复训练闭环，明确 noisy、clean、output、loss、metric 的关系，
为后续 paired RGB 和 RAW-like restoration 实验建立统一训练入口。
```

更有含金量的补法：

- 把训练闭环画成 `data -> model -> loss -> metric -> checkpoint -> visualization`。
- 在报告里解释为什么图像恢复不能只看 loss，还要看 PSNR/SSIM 和局部图。
- 强调配置驱动训练，而不是手改脚本。

## Week 1：Toy RGB Denoise

原内容：toy RGB 去噪、TinyCNN、DnCNN、L1/L2、patch size、noise type。

升级表达：

```text
先用可控 synthetic noise 跑通训练链路，并通过 TinyCNN -> DnCNN、L1/L2、
patch size 对比验证模型容量、损失函数和输入裁剪策略对恢复质量的影响。
```

更有含金量的补法：

- 将 L1/L2、patch size、noise type 汇总成 ablation 表。
- 把 DnCNN residual 的任务假设讲清楚：学习噪声残差，而不是直接生成 clean。
- 把 toy 实验定位为“训练系统校准”，不要当成最终项目成果。

## Week 2：真实 Paired RGB 数据

原内容：准备 SIDD tiny paired RGB，检查 noisy/clean 对齐，测 noisy baseline。

升级表达：

```text
从 synthetic toy 迁移到真实 SIDD paired RGB 数据，完成 noisy-clean 对齐检查、
80/20 train-val subset 构建和 noisy input baseline，为真实图像恢复实验建立
数据入口和评价基准。
```

更有含金量的补法：

- 明确 paired 数据必须像素对齐，否则 PSNR/SSIM 没有意义。
- 报告数据规模、crop size、train/val 划分和 baseline 指标。
- 增加数据检查图，证明不是随便拿两张图训练。

## Week 3：真实 RGB 模型实验

原内容：DnCNN、UNet、NAFNet-lite 在 SIDD tiny 上训练。

升级表达：

```text
在真实 paired RGB 子集上建立多模型 baseline，对比 residual CNN、encoder-decoder
和现代 restoration block 在有限数据和训练步数下的效果差异。
```

更有含金量的补法：

- 不只报结果，还解释“为什么 DnCNN 当前最强”。
- 把模型复杂度、训练步数、loss 和 PSNR/SSIM 放在同一张表。
- 对 NAFNet-lite 不要说失败，而要说“结构跑通，但需要扩数据和长训”。

## Week 4：Metric 和可视化

原内容：PSNR/SSIM、三联图、error map、多模型评估。

升级表达：

```text
建立从数值指标到视觉诊断的评估体系：PSNR 衡量像素误差，SSIM 衡量结构相似，
triplet 用于主观对比，error map 和 crop 用于定位局部失败区域。
```

更有含金量的补法：

- 给 PSNR/SSIM 差异写解释，而不是只贴表。
- 增加 failure pattern：纹理区域、暗部、边缘、色偏。
- 把评估脚本作为工程产物，而不是只作为辅助脚本。

## Week 5：NAFNet-lite 复现

原内容：学习并实现轻量 NAFNet-like 模型。

升级表达：

```text
将项目从传统 CNN baseline 扩展到现代 image restoration block，验证轻量
NAFNet-like 结构在小数据集上的训练可行性，并分析其未超过 DnCNN 的原因。
```

更有含金量的补法：

- 解释 simple gate / residual / encoder-decoder 的设计意义。
- 对比短训版和标准版，说明训练资源和配置对现代模型很关键。
- 加参数量统计，体现部署视角。

## Week 6：Pseudo RAW / ISP Bridge

原内容：pseudo Bayer、RAW pack、demosaic 可视化。

升级表达：

```text
将 RGB restoration 结果连接到 ISP 成像链路，构建 pseudo RAW/RGGB pack
实验入口，理解 RAW-like 4 通道输入、demosaic 和 sRGB 输出之间的关系。
```

更有含金量的补法：

- 说明这是 RAW-like bridge，不是真实 sensor RAW。
- 新增 `paired_pseudo_raw_dataset`，让 pseudo RAW 不只停留在可视化，而能进入训练。
- 将 RGB baseline 和 RGGB baseline 做对比。

## Week 7：Low-light Enhancement

原内容：synthetic low-light RGB 数据和 UNet 增强实验。

升级表达：

```text
将任务从普通去噪扩展到低光增强，模型需要同时处理亮度恢复、噪声抑制和颜色保持，
更接近 AI-ISP 中夜景增强和暗光画质优化问题。
```

更有含金量的补法：

- 区分 denoise 和 low-light enhancement：后者不只是降噪。
- 报告 exposure、shot/read noise 设置。
- 增加亮度分布或过曝/欠曝比例等 IQ 指标。

## Week 8：Failure Case

原内容：局部 crop 分析。

升级表达：

```text
通过 failure crop 将模型评估从“平均指标”推进到“问题定位”，分析纹理、边缘、
暗部和色彩区域的恢复失败原因，为后续数据增强、loss 调整和模型选择提供依据。
```

更有含金量的补法：

- 每类 failure 给出原因假设和下一步改法。
- 把 crop 结果和 error map 对应起来。
- 面试时用它证明你会分析结果，不只是跑脚本。

## Week 9：阶段总结

原内容：最终 leaderboard、简历和面试表达。

升级表达：

```text
将阶段二收束为 AI-ISP restoration baseline：覆盖数据构建、模型对比、
客观评估、可视化诊断、low-light 扩展和 pseudo RAW bridge，并明确后续
ONNX/C++ 部署与 IQ 指标方向。
```

更有含金量的补法：

- 增加工程汇总表：模型、参数量、checkpoint 大小、PSNR、SSIM。
- 增加部署状态：PyTorch done、ONNX next、C++ next。
- 增加岗位匹配表：哪些能写，哪些不能吹。

## 新增 Week 10+：工程化升级

新增内容：

```text
scripts/13_export_engineering_summary.py
deployment/export_onnx.py
deployment/cpp_onnx_infer/
```

目标：

```text
把阶段二从“训练项目”升级到“训练 + 评估 + RAW-like + 部署验证项目”。
```

下一步验收：

| 项 | 验收标准 |
|---|---|
| pseudo RAW baseline | 生成 metrics.csv 和 checkpoint |
| ONNX export | 生成 `.onnx` 文件 |
| C++ inference | 输入 noisy 图，输出 restored 图并打印 latency |
| engineering summary | 生成参数量、checkpoint、PSNR/SSIM 汇总表 |

## 最终项目叙事

推荐按这个顺序讲：

```text
1. 问题背景：ISP 链路中噪声、低光、画质恢复问题。
2. 数据构建：SIDD paired RGB，检查 noisy-clean 对齐。
3. 模型设计：DnCNN residual、UNet、NAFNet-lite。
4. 实验评估：PSNR/SSIM、triplet、error map、failure crop。
5. AI-ISP 扩展：pseudo RAW/RGGB、low-light enhancement。
6. 工程升级：ONNX/C++、参数量、checkpoint、latency。
7. 项目边界：不是量产 tuning，但具备 AI-ISP baseline 能力。
```
