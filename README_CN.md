# Route — AI-ISP 学习作品集

[English Version](README.md)

面向 AI-ISP 算法工程师方向的自驱动、项目驱动学习仓库，覆盖从传感器物理、传统 ISP 算法到 AI 图像恢复、最终 C++/CUDA 部署的完整链路。

## 仓库地图

```
route/
├── soft_isp_stage1/       # 阶段一：传统 ISP Pipeline（Python）
├── ai_isp_stage2/         # 阶段二：AI-ISP 图像恢复（PyTorch）
├── study-roadmap/         # 10 个月 AI-ISP 社招学习路线
├── README.md
└── README_CN.md
```

### [soft_isp_stage1/](soft_isp_stage1/) — 阶段一：传统 ISP Pipeline

一个动手实践的 Python Soft-ISP Pipeline — 读取真实 DNG 文件，亲手实现每个传统 ISP 模块（BLC、DPC、LSC、去马赛克、AWB、CCM、Gamma、Tone Mapping），与 rawpy 参考输出对比，撰写结构化实验报告。同时包含完整的 [OpenISP](https://github.com/cruxopen/openISP) 参考实现，用于逐模块对照学习。

**状态：** 已完成。所有模块均已实现，IQA 消融实验完成，Week 6 知识盲区闭合。共 16 个脚本，完整的 Pipeline 评估，以及 Week 1–6 的周报。

详见 [soft_isp_stage1/README_CN.md](soft_isp_stage1/README_CN.md)。

### [ai_isp_stage2/](ai_isp_stage2/) — 阶段二：AI-ISP 图像恢复

第二阶段从手工算法转向可学习图像恢复。当前阶段先用合成 RGB 去噪任务跑通深度学习训练闭环，验证工程链路后再推进到真实传感器数据（SIDD、SID）。

**状态：** 进行中。TinyCNN / DnCNN / UNet 三种模型的 toy RGB denoise baseline 已跑通，训练循环、配置系统和 PSNR/SSIM 评估链路均已就绪。

详见 [ai_isp_stage2/README.md](ai_isp_stage2/README.md)。

### [study-roadmap/](study-roadmap/) — 职业学习路线

一份 10 个月、4 阶段的完整学习路线，面向已有 ISP 工程经验的工程师，从"会对齐输出、会改代码"升级到"能解释算法、能设计实验、能评估画质、能部署 AI-ISP 模型"。

详见 [study-roadmap/AI-ISP 图像算法工程师 · 社招学习路线.md](study-roadmap/AI-ISP%20图像算法工程师%20·%20社招学习路线.md)。

## 项目初衷

现代相机 Pipeline 是不透明的。手机或相机内部的 ISP 是芯片厂商优化的黑盒 —— 你看不到中间阶段、无法调参、也不理解某个像素为什么最终呈现某个值。

本项目反其道而行之：每个阶段都显式、可检查、可修改。目标不是对标 Lightroom 或 Adobe Camera Raw，而是建立起足够扎实的心智模型，使你能：

- 读取 RAW 直方图，在写代码之前就诊断传感器问题
- 解释为什么去马赛克在黑电平校正之后、白平衡之前 —— 以及调换顺序会出什么问题
- 调整参数并预测哪些图像区域会如何变化
- 将输出与参考结果逐项对比，说清每一处差异的成因
- 最终用可学习模块替代传统模块时，确切知道自己替换了什么

## 快速开始

从 [soft_isp_stage1/](soft_isp_stage1/) 开始 —— Python 学习项目不需要 C++ 工具链，能立刻产生可视化输出。

```bash
cd soft_isp_stage1
pip install -r requirements.txt
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
```

如果还没有 RAW 文件，使用项目自带的下载脚本：

```powershell
.\soft_isp_stage1\scripts\download_fivek_starter.ps1
```

## 项目理念

1. **物理先于代码。** 在写任何 ISP 逻辑之前，先理解传感器到底测量了什么。
2. **实现先于引用。** 在调用库函数之前，先自己写 BLC、去马赛克、AWB。没亲手实现过的东西，你解释不清楚。
3. **一切可视化。** 直方图、ROI 叠加、差异图。看不到就没法调试。
4. **持续对比。** 每个模块的输出都与 rawpy/LibRaw 参考对比。每处差异都要说清原因。
5. **写报告而不只是写代码。** 一堆实验但没有书面结论的笔记本不算交付物。

## 技术栈

| 层次 | 工具 |
|---|---|
| RAW I/O | rawpy (libraw), imageio |
| 数组处理 | NumPy, OpenCV |
| 可视化 | Matplotlib |
| 指标 | scikit-image (SSIM), colour-science (Delta E) |
| 配置 | YAML |
| 深度学习 | PyTorch, torchvision |
| 未来 C++ 工作台 | C++17, Qt 6, OpenColorIO, GoogleTest, OpenImageIO |

## 阶段规划

| 阶段 | 重点 | 语言 | 状态 |
|---|---|---|---|
| 1 | 传统 ISP Pipeline 基础 | Python | 已完成 |
| 2 | AI 驱动的图像恢复与降噪 | Python + PyTorch | 进行中 |
| 3 | C++ 高性能 ISP 库 | C++ | 计划中 |
| 4 | CUDA 加速 + TensorRT/NCNN 部署 | C++ / CUDA | 计划中 |

## 许可

个人学习作品集。所有原创代码可供参考和教育用途。
