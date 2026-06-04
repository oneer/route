# 阶段二社招 3 年口径升级版项目材料

## 1. 项目定位

原阶段二是一个 AI-ISP 图像恢复学习项目，已经完成从 toy RGB denoise 到真实
SIDD paired RGB 去噪、模型对比、指标评估、可视化和 failure case 分析的闭环。

为了更适配社招 3 年左右的图像算法 / AI-ISP / ISP 软件岗位，项目表达需要从
“我跑通了训练”升级为：

```text
我能围绕 ISP 成像链路中的噪声、低光和画质问题，完成数据构建、模型设计、
实验对比、客观评估、失败案例分析，并推进到 RAW-like 输入和部署验证。
```

推荐项目名称：

```text
AI-ISP 图像恢复与部署验证项目
```

不要把它包装成：

```text
车载摄像头量产 ISP tuning 项目
高通 / MTK / 海思平台 ISP 调试项目
完整工业 RAW ISP 系统
```

## 2. 项目升级后的能力边界

| 能力项 | 当前证据 | 社招 3 年表达方式 |
|---|---|---|
| 真实数据处理 | SIDD Small sRGB 80/20 paired subset | 能构建 noisy-clean paired 数据并检查像素对齐 |
| 图像恢复训练 | DnCNN / UNet / NAFNet-lite | 能建立 baseline 并对比不同 restoration backbone |
| 评价体系 | PSNR / SSIM / triplet / error map / failure crop | 能用客观指标和局部可视化定位画质问题 |
| ISP 关联 | pseudo RAW / RGGB pack / low-light | 能把 RGB restoration 连接到 ISP RAW-like 场景 |
| 工程化升级 | ONNX export / C++ OpenCV DNN 骨架 | 能推动模型从训练侧走向部署验证 |
| 实验分析 | loss、patch、steps、模型对比已有基础 | 能解释模型、loss、训练配置和结果差异 |

## 3. 已取得的核心结果

阶段二标准实验结果：

| 任务 | 模型 | PSNR | SSIM | 结论 |
|---|---|---:|---:|---|
| SIDD tiny RGB 去噪 | DnCNN residual | 35.5356 | 0.88367 | 当前最强 baseline |
| SIDD tiny RGB 去噪 | NAFNet-lite | 33.3269 | 0.86223 | 现代 restoration block 跑通，但仍需更多训练和调参 |
| SIDD tiny RGB 去噪 | UNet | 30.4453 | 0.88003 | 结构保持尚可，像素级误差不如 DnCNN |
| Synthetic low-light 增强 | UNet | 24.7821 | 0.81468 | 低光增强训练链路跑通 |

关键解释：

```text
当前 SIDD tiny 任务中，输入 noisy 与 clean 的结构基本一致，差异主要是噪声。
DnCNN residual 直接学习噪声残差，再从输入中减去，任务假设更匹配，所以在
有限数据和训练步数下优于更复杂的 UNet / NAFNet-lite。
```

## 4. 已新增的升级内容

为了把项目从“RGB denoise baseline”升级到更像 AI-ISP 工程项目，已经新增：

```text
ai_isp/data/pseudo_raw.py
ai_isp/data/paired_pseudo_raw_dataset.py
configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
scripts/12_preview_pseudo_raw_dataset.py
deployment/export_onnx.py
deployment/cpp_onnx_infer/
deployment/README.md
reports/stage2_upgrade_plan.md
```

这些内容对应三条升级线：

| 升级线 | 作用 | 对岗位的价值 |
|---|---|---|
| pseudo RAW / RGGB | 将 RGB paired 图转换为 4 通道 RAW-like 输入 | 对齐 AI-ISP、RAW/YUV、ISP pipeline 关键词 |
| ONNX / C++ | 将 PyTorch 模型导出并用 C++/OpenCV DNN 推理 | 对齐 C/C++、部署、工程化关键词 |
| 消融与 IQ 指标计划 | 补充 loss / patch / latency / sharpness / noise 分析 | 对齐算法评审和画质调优思路 |

## 5. 社招 3 年简历写法

### 简洁版

```text
AI-ISP 图像恢复与部署验证项目 | PyTorch / SIDD / DnCNN / UNet / NAFNet-lite / ONNX / C++

基于 SIDD paired RGB 数据搭建 AI-ISP 图像恢复训练与评估闭环，完成 DnCNN、
UNet、NAFNet-lite 模型对比、PSNR/SSIM 评估、error map 和 failure crop 分析；
在 SIDD tiny 去噪任务上 DnCNN residual 达到 35.54 dB PSNR / 0.8837 SSIM，
并扩展 pseudo RAW/RGGB 输入与 ONNX/C++ 推理验证链路。
```

### 强化版

```text
AI-ISP 图像恢复与部署验证项目 | PyTorch / SIDD / ONNX / C++ / OpenCV

- 构建从 SIDD paired RGB 数据准备、noisy-clean 对齐检查、模型训练，到 PSNR/SSIM
  评估和 failure case 分析的图像恢复实验闭环。
- 训练并对比 DnCNN residual、UNet、NAFNet-lite 等 restoration backbone，在 SIDD
  tiny 去噪任务上 DnCNN residual 达到 35.54 dB PSNR / 0.8837 SSIM。
- 结合传统 ISP 成像链路，扩展 pseudo RAW/RGGB pack 数据入口和 synthetic
  low-light enhancement 实验，分析 AI 恢复模型在 ISP 链路中的应用边界。
- 搭建 ONNX 导出与 C++ OpenCV DNN 推理验证骨架，推动模型从 PyTorch 训练侧
  向部署评估侧迁移，并规划 latency / 模型大小 / 画质损失对比。
```

## 6. 面试讲法

### 6.1 一分钟项目介绍

```text
这个项目的目标是把传统 ISP 里的噪声、低光和画质评估问题，用 AI 图像恢复的
方式做一个可复现实验闭环。我先用 toy RGB denoise 验证训练流程，再接入
SIDD Small sRGB paired 数据，建立 noisy input baseline，训练 DnCNN、UNet、
NAFNet-lite 并用 PSNR/SSIM、三联图、error map 和 failure crop 分析结果。

在当前 SIDD tiny 设置下，DnCNN residual 达到 35.54 dB PSNR / 0.8837 SSIM，
是最稳定的 baseline。后续我把项目扩展到 pseudo RAW/RGGB pack 和 ONNX/C++
推理验证，目的是让它更接近 AI-ISP 工程链路，而不是停留在纯 Python demo。
```

### 6.2 为什么 DnCNN 比 NAFNet-lite 更好

```text
这个结论只针对当前 tiny paired RGB 去噪实验。SIDD tiny 输入和 clean 的结构
高度一致，主要差异是噪声。DnCNN residual 的归纳偏置很适合这个任务，它学习
噪声残差再从输入扣除。NAFNet-lite 结构更现代，但数据量和训练步数有限时，
复杂模型不一定马上超过强 baseline，所以我没有把它描述成失败，而是作为后续
扩数据、长训和 loss 调优的方向。
```

### 6.3 项目和 ISP 岗位的关系

```text
它不是车载摄像头量产 tuning 项目，也没有真实平台上的 AE/AWB/AF 联调经验。
它的价值在于我理解 RAW-to-RGB 和传统 ISP 模块的基本链路，同时能用深度学习
方法处理 denoise / low-light 这类 ISP 相关画质问题，并能用客观指标和可视化
分析失败案例。现在新增的 pseudo RAW/RGGB 和 ONNX/C++ 骨架，就是为了补齐
AI-ISP 与工程部署之间的连接。
```

## 7. 对 Boss 岗位要求的匹配

| 岗位关键词 | 匹配程度 | 项目证据 | 备注 |
|---|---|---|---|
| Python / PyTorch | 高 | 训练、评估、模型对比全链路 | 可直接写 |
| 图像去噪 / 低光增强 | 高 | SIDD denoise、synthetic low-light | 可直接写 |
| PSNR / SSIM / 画质分析 | 高 | metrics、error map、failure crop | 可直接写 |
| ISP pipeline 原理 | 中 | 阶段一 + pseudo RAW bridge | 需要和阶段一一起讲 |
| RAW / YUV / sensor | 中低 | pseudo RAW/RGGB | 只能说 RAW-like 实验，不能说真实 sensor 调试 |
| C/C++ | 中低到中 | ONNX/C++ 骨架 | 需要跑通 C++ inference 后再强化 |
| AE/AWB/AF / 3A | 低 | 暂无真实 3A 调试 | 不要硬写 |
| Imatest / iQ-Analyzer | 低 | 暂无工具经验 | 可补轻量 IQ metrics，但不能冒充工具经验 |
| 车载实车调试 | 低 | 暂无 | 不要写 |

## 8. 下一步提高含金量的执行顺序

优先级按社招 3 年含金量排序：

```text
1. 跑通 pseudo RAW/RGGB 300-step baseline，形成 RGB vs RGGB 对比表。
2. 安装 onnx / onnxscript，导出 DnCNN ONNX。
3. 用 C++ OpenCV DNN 跑一张 SIDD noisy 图，记录 latency。
4. 增加参数量、模型大小、CPU latency、PSNR/SSIM 的统一 summary 表。
5. 实现轻量 IQ metrics：sharpness、noise、exposure、color cast。
6. 把最终报告改成“问题背景 -> 方法 -> 实验 -> 部署 -> 失败案例 -> 岗位匹配”。
```

完成第 1-4 步后，项目就可以从“学习型项目”升级为：

```text
具备训练、评估、RAW-like 场景和部署验证的 AI-ISP baseline 项目
```

这才是比较适合社招 3 年口径的表达。
