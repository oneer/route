# Soft ISP — 从 RAW 到 RGB，逐像素理解成像管线

[English Version](README.md)

面向 ISP 算法工程师方向的自驱动学习仓库，覆盖从传感器物理到 C++ 桌面工具的完整链路。

## 仓库地图

```
route/
├── docs/
│   └── soft_isp_desktop_design.md   # C++ 桌面端 Soft ISP 工作台设计文档
├── soft_isp_stage1/                 # 阶段一：Python Soft-ISP 学习项目
├── study-roadmap/                   # 10 个月 AI-ISP 社招学习路线
└── README.md
```

### [docs/](docs/) — 设计文档

[Soft ISP 桌面工作台设计文档](docs/soft_isp_desktop_design.md) 规划了一个基于 C++ 的交互式 ISP 可视化平台：

- RAW/DNG → 分阶段执行 Pipeline → 查看每个阶段的中间结果
- 修改各阶段参数并实时观察效果
- 替换或扩展算法模块
- 导出最终 sRGB 或任意中间结果

架构覆盖：渲染图、数据模型（RAW/非线性/显示节点）、UI 布局、基于 OpenColorIO 的色彩管理、EXIF 往返、CI/测试策略（GoogleTest、OpenImageIO、感知容差比对）。一期目标为 Qt + CPU 浮点 Pipeline，预览与全分辨率分离。

### [soft_isp_stage1/](soft_isp_stage1/) — 阶段一学习项目

一个动手实践的 Python Soft-ISP Pipeline — 读取真实 DNG 文件，亲手实现每个传统 ISP 模块（BLC、DPC、LSC、去马赛克、AWB、CCM、Gamma），与 rawpy 参考输出对比，撰写结构化实验报告。

**当前状态：** 第 1 周已完成（RAW 统计、直方图、ROI 分析，覆盖 5 张 FiveK 样张）。第 2-6 周涵盖前端校正、去马赛克/AWB、色彩/色调、画质评价和最终报告。

详见 [soft_isp_stage1/README_CN.md](soft_isp_stage1/README_CN.md)。

### [study-roadmap/](study-roadmap/) — 职业学习路线

一份 10 个月、项目驱动的学习路线，面向已有 ISP 工程经验（Python/C++ Pipeline 维护、定点化、多通道重构）、需要从"会对齐输出、会改代码"升级到"能解释算法、能设计实验、能评估画质、能部署 AI-ISP 模型"的工程师。

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
python scripts/01_inspect_raw.py data/raw/S01_a0001-jmac_DSC1459.dng
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
| 未来 C++ 工作台 | C++17, Qt 6, OpenColorIO, GoogleTest, OpenImageIO |

## 后续阶段

| 阶段 | 重点 | 语言 |
|---|---|---|
| 1（当前） | 传统 ISP Pipeline 基础 | Python |
| 2 | AI 驱动的 RAW 降噪 / 暗光增强 | Python + PyTorch |
| 3 | C++ 高性能 ISP 库 | C++ |
| 4 | CUDA 加速 + TensorRT/NCNN 部署 + 桌面工作台 | C++ / CUDA |

## 许可

个人学习作品集。所有原创代码可供参考和教育用途。
