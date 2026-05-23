# Soft-ISP 阶段一 — RAW 基础与传统 ISP Pipeline

[English Version](README.md)

从零构建一个可解释的 Python Soft-ISP Pipeline。本项目读取真实 RAW/DNG 文件，逐步实现完整的传统 ISP 处理链 —— 黑电平校正、坏点校正、镜头暗角校正、去马赛克、自动白平衡、色彩校正矩阵、Gamma/色调映射 —— 并为每个模块提供统计信息、可视化图表以及与 rawpy 参考输出的对比分析。

## 项目定位

大多数 ISP 教程止步于理论，或依赖不透明的"黑盒"库调用。本项目要求你：

- 读取真实传感器数据，理解 RAW 文件中每个数值的物理含义。
- 亲手实现每个 ISP 模块，能解释其数学原理、核心假设、失败模式和参数影响。
- 将输出与 rawpy/LibRaw 参考结果逐项对比，说清每一处差异的成因。
- 养成撰写结构化实验报告（而不只是堆代码）的习惯，形成面试可讲的材料。

## 目录结构

```
soft_isp_stage1/
├── configs/
│   └── default.yaml              # Pipeline 模块开关与参数配置
├── data/
│   ├── raw/                      # 输入 DNG/RAW 文件（不提交到 Git）
│   └── references/               # rawpy 处理的 sRGB 参考图
├── materials/
│   ├── stage1_start_here.md      # 6 周路线图与每日指引
│   ├── module_study_template.md  # 每个 ISP 模块的学习模板
│   ├── raw_sample_manifest.md    # RAW 样张登记表（含下载链接）
│   ├── resources.md              # 论文/课程/数据集/开源项目总索引
│   ├── books/                    # 参考书目列表
│   ├── datasets/                 # FiveK 索引 + 自动生成的元数据表
│   ├── notes/                    # 论文阅读模板
│   ├── open_source/              # OpenISP / Infinite-ISP 学习指南
│   ├── papers/                   # 核心论文（Karaimer & Brown, HDR+, SID 等）
│   └── slides/                   # Stanford EE367、Cornell CS6640 课件
├── notebooks/                    # Jupyter notebooks（预留）
├── reports/
│   ├── stage1_report.md          # 阶段总报告模板
│   ├── README.md                 # 报告导航
│   ├── week1/                    # 第 1 周：RAW 统计、ROI、总结
│   ├── week2/                    # 第 2 周：BLC、DPC、总结
│   ├── week3/                    # 第 3 周：Demosaic、AWB、总结
│   ├── interview/                # 面试题与复习材料
│   ├── figures/                  # 生成的直方图 + ROI 预览图
│   └── raw_stats/                # 每张样张的 JSON 元数据
├── scripts/
│   ├── 01_inspect_raw.py         # 导出 RAW 元数据与通道统计为 JSON
│   ├── 02_generate_rawpy_references.py  # 生成 rawpy sRGB 参考图
│   ├── 03_dump_raw_metadata_table.py    # 生成 Markdown 元数据汇总表
│   ├── 04_plot_raw_histogram.py  # 绘制双栏 RAW + Bayer 通道直方图
│   ├── 05_analyze_raw_roi.py     # 自动选取暗部/中间调/高光 ROI 并分析
│   └── download_fivek_starter.ps1  # 下载 5 张 MIT-Adobe FiveK 入门样张
├── soft_isp/
│   ├── __init__.py               # 包初始化
│   └── stats.py                  # 核心工具：Bayer 推断、统计、通道拆分
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 环境配置

```bash
# 进入项目目录
cd soft_isp_stage1

# 安装依赖（Python 3.9+）
pip install -r requirements.txt
```

### 2. 下载 RAW 样张

**方式 A — PowerShell（Windows）：**

```powershell
.\scripts\download_fivek_starter.ps1
```

**方式 B — 手动下载：**

从 [MIT-Adobe FiveK 数据集](https://data.csail.mit.edu/graphics/fivek/) 下载 5 张 DNG 文件放入 `data/raw/`。具体文件列表与 URL 见 `materials/raw_sample_manifest.md`。

### 3. 生成参考输出

```bash
# 为所有 DNG 文件生成 rawpy sRGB 参考图
python scripts/02_generate_rawpy_references.py
```

### 4. 检查第一张 RAW

```bash
# 导出完整的元数据和通道统计（JSON 格式）
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
```

### 5. 绘制直方图

```bash
# 为一张或多张 RAW 生成双栏直方图（全局 + 分通道）
python scripts/04_plot_raw_histogram.py data/raw/*.dng
```

### 6. 分析 ROI

```bash
# 自动选取并分析暗部、中间调、高光 ROI
python scripts/05_analyze_raw_roi.py data/raw/*.dng
```

## 依赖说明

| 包 | 用途 |
|---|---|
| `numpy` | 数组运算与统计 |
| `opencv-python` | 图像读写、色彩空间转换 |
| `rawpy` | RAW/DNG 文件读取（libraw 的 Python 绑定） |
| `matplotlib` | 直方图与图表绘制 |
| `scikit-image` | SSIM 等高级图像指标 |
| `colour-science` | 色彩科学计算 |
| `pyyaml` | Pipeline 配置文件解析 |
| `imageio` | 参考图像写出 |

## 脚本说明

所有脚本位于 `scripts/`，按推荐执行顺序编号。

| 编号 | 脚本 | 输入 | 输出 | 用途 |
|---|---|---|---|---|
| 01 | `inspect_raw.py` | DNG 路径 + 可选 `--pattern` | JSON（stdout） | 完整元数据导出：黑/白电平、Bayer 排列、通道统计 |
| 02 | `generate_rawpy_references.py` | `data/raw/` 下所有 `*.dng` | `data/references/` 下的 PNG | 生成 rawpy sRGB 参考图像（"标准答案"） |
| 03 | `dump_raw_metadata_table.py` | `data/raw/` 下所有 `S*.dng` | Markdown 表格 | 数据集元数据快速索引表 |
| 04 | `plot_raw_histogram.py` | 一张或多张 DNG 路径 | `reports/figures/` 下的 PNG | 双栏对数直方图，标注黑/白电平线 |
| 05 | `analyze_raw_roi.py` | 一张或多张 DNG 路径 | PNG + JSON + MD 报告 | 自动选取暗/中/亮 ROI，生成标注预览与统计 |

## 核心库（`soft_isp/`）

`soft_isp` 包提供所有脚本共用的基础设施：

| 函数 | 所在文件 | 功能 |
|---|---|---|
| `bayer_pattern_from_rawpy()` | `stats.py` | 从 rawpy 元数据推断标准 Bayer 字符串（RGGB/BGGR/GRBG/GBRG） |
| `describe_array()` | `stats.py` | 计算数组的 shape、dtype、min、max、mean、std、p01、p50、p99 |
| `split_bayer()` | `stats.py` | 通过步长切片将 Bayer 马赛克拆分为 R、Gr、Gb、B 四个通道 |

## 学习路线（6 周）

详见 `materials/stage1_start_here.md`。

| 周次 | 重点 | 核心交付物 |
|---|---|---|
| 0.5 | 环境搭建 + 样张下载 + 首次读取 RAW | 5 张 DNG 放入 `data/raw/` |
| 1 | RAW 传感器直觉：元数据、直方图、ROI | `reports/week1/raw_statistics.md`、直方图 PNG |
| 2 | 前端校正：BLC、DPC、LSC | 逐模块笔记 + 处理前后对比 |
| 3 | 去马赛克 + 自动白平衡 | 可运行的双线性/AHD 去马赛克、灰度世界 AWB |
| 4 | CCM + Gamma + 色调映射 | 端到端 Pipeline 完整输出 |
| 5 | 画质评价、消融实验、报告 | PSNR/SSIM/DeltaE 表、rawpy 对比、失败分析 |
| 6 | 润色 + 面试准备 | 最终报告、逐模块面试问答 |

每个 ISP 模块必须回答 7 个问题（详见 `materials/module_study_template.md`）：

1. 输入的确切规格（数据域、值域、形状）是什么？
2. 输出的确切规格是什么？
3. 这个模块解决什么物理或感知问题？
4. 核心假设是什么？什么时候会失效？
5. 各参数如何影响输出（附可视化示例）？
6. 如何独立验证该模块的正确性（不依赖下游模块）？
7. 有哪些失败场景？如何检测？

## 数据约定

- **输入 RAW/DNG 文件** → `data/raw/`（不提交到 Git — 大体积二进制文件）
- **参考输出**（rawpy、Lightroom、LibRaw）→ `data/references/`
- **生成的图表**（直方图、ROI 预览、对比图）→ `reports/figures/`
- **逐张统计** → `reports/raw_stats/`
- **周报** → `reports/`

## 当前交付状态

| 交付物 | 状态 | 说明 |
|---|---|---|
| RAW 样张下载脚本 | 已完成 | 5 张 FiveK 入门 DNG 的 PowerShell 下载脚本 |
| RAW 元数据检查 | 已完成 | `01_inspect_raw.py` + 5 份 JSON 统计 |
| 参考图像生成 | 已完成 | `02_generate_rawpy_references.py` + 5 张参考 PNG |
| 元数据汇总表 | 已完成 | `03_dump_raw_metadata_table.py` → Markdown 表格 |
| 直方图绘制 | 已完成 | S01、S03、S05 直方图，带黑/白电平标注 |
| ROI 分析 | 已完成 | S01、S03、S05 的暗/中/亮 ROI，含 JSON + 预览图 |
| 第 1 周报告 | 已完成 | `reports/week1/raw_statistics.md` + `reports/week1/roi_analysis.md` |
| BLC 模块 | 待完成 | 第 2 周 |
| DPC 模块 | 待完成 | 第 2 周 |
| LSC 模块 | 待完成 | 第 2 周 |
| 去马赛克模块 | 待完成 | 第 3 周 |
| AWB 模块 | 待完成 | 第 3 周 |
| CCM 模块 | 待完成 | 第 4 周 |
| Gamma/Tone 模块 | 待完成 | 第 4 周 |
| IQA + 最终报告 | 待完成 | 第 5-6 周 |

## 许可

本项目为个人学习作品集的一部分。所有原创代码可供参考和教育用途。
