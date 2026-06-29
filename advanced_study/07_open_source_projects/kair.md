# KAIR: Image Restoration Toolbox

## 深度阅读目标

KAIR 适合学习研究型图像恢复项目如何组织实验。stage2 已经有脚本、报告和模型，但如果继续加入 DnCNN、NAFNet、SwinIR、Restormer、PromptIR，很容易脚本散乱。KAIR 的价值是配置驱动、多模型共存、训练测试流程统一。

## 研究代码最该看什么

不要只看 model 文件。一个恢复项目能不能复现，通常取决于：

```text
数据集读取是否清晰
退化生成是否可控
训练配置是否完整
checkpoint 和日志是否可追溯
测试脚本是否和训练预处理一致
metrics 是否统一
```

KAIR 的目录组织正好能作为 stage2 后续升级参考。

## 读代码的具体顺序

1. 先选择一个最熟悉的任务，比如 DnCNN denoising。
2. 找对应 options 配置，弄清楚数据路径、patch size、batch size、loss、学习率。
3. 找 data loader，看 noisy/clean pair 怎么生成或读取。
4. 找 model wrapper，看 forward、loss、optimizer、scheduler 如何组织。
5. 最后读 test script，看输出图片和 metrics 如何保存。

## 对本项目最有价值的工程点

第一是实验目录规范。每次实验应该保存 config、日志、checkpoint、metrics、可视化样例。

第二是模型注册。stage2 不应该为每个模型复制一套训练脚本，而应逐步抽象出轻量模型构建函数。

第三是退化可控。AI-ISP 学习必须知道训练噪声、低光、模糊、压缩是怎么来的，否则模型结果无法解释。

## 可迁移练习

1. 给 `stage2_ai_isp` 设计统一实验输出目录：`config.yaml`、`metrics.json`、`figures/`、`checkpoints/`。
2. 把 TinyCNN、DnCNN、NAFNet 做成统一 model factory。
3. 写一个 dataset card，记录 SIDD tiny 或 low-light subset 的来源、划分、预处理和限制。
4. 把每次测试输出固定为 full image、crop、error map、metrics csv。

## 阅读完成标准

读完后你应该能说明：图像恢复研究工程的关键不是某个网络类，而是配置、数据、训练、评估和可视化的闭环可复现。

## 项目信息
- GitHub：https://github.com/cszn/KAIR
- Star 数或活跃度：经典图像恢复研究工具箱，包含多种去噪、超分、去模糊模型；具体 Star 数以 GitHub 页面为准。
- 主要语言：Python、PyTorch

## 项目解决什么问题

KAIR 是图像恢复研究代码集合，覆盖 DnCNN、FFDNet、SRMD、USRNet、SwinIR 等方向。它适合用来学习研究型 PyTorch 项目的数据、模型、训练、测试组织方式。

## 项目目录结构解读

常见结构包括：

- `models/`：网络结构和模型封装。
- `data/`：数据集加载和退化构造。
- `options/`：YAML 配置。
- `train.py` / `main_train_*.py`：训练入口。
- `testsets/`、`results/`：测试输入和输出。

## 核心模块说明

KAIR 的重点是“实验可配置”。不同恢复任务共享数据加载、模型构建、训练循环、日志和测试框架。对 stage2 来说，它是从小脚本走向研究工程的参考。

## 如何和当前项目关联

stage2 已经有训练、评估、ONNX 导出和报告。KAIR 可以帮助你改进实验组织：统一配置、统一模型注册、统一测试输出和结果目录。

## 值得学习的工程设计

- 配置驱动实验。
- 多模型、多任务共用训练骨架。
- 结果目录和 checkpoint 管理。
- 测试脚本和可视化输出规范。

## 初学者阅读顺序

1. 先选 DnCNN 或 SwinIR 的测试脚本跑通。
2. 看 options 文件如何描述数据、模型和训练。
3. 读对应 model 文件。
4. 最后读 training loop 和日志保存逻辑。

## 可迁移到当前项目的功能点

1. 给 stage2 增加更统一的 experiment config。
2. 把模型、数据集、损失函数做轻量注册表。
3. 规范输出目录：config、checkpoint、metrics、figures 同目录归档。

## 阅读后应该掌握什么

你应该能理解：图像恢复研究工程的核心不是单个模型文件，而是让数据、配置、训练和评估可复现地协同。
