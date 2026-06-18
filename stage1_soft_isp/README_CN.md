# 阶段一：RAW 基础与可解释 Soft-ISP

[English](README.md)

阶段一用于建立 RAW 数据域、传统 ISP 主链路、模块验证和调试能力。仓库同时包含参考实现与历史实验结果，但学习目标不是重复运行这些成品，而是通过练习、测试和独立毕业任务证明自己能够解释、修改和重新实现。

## 开始前先读

1. [前置知识与自测](materials/prerequisites.md)
2. [可复现环境搭建](materials/environment_setup.md)
3. [从这里开始](materials/stage1_start_here.md)
4. [练习入口](exercises/README.md)
5. [调试手册](materials/debugging_guide.md)
6. [报告—代码—实验对应表](reports/stage1_tutorial_audit.md)

如果前置自测不能独立完成，先补 Python/NumPy，不建议直接阅读 200 行以上实验脚本。

## 学习目标

完成阶段一后，应能独立：

- 读取陌生 DNG，解释 black/white level、Bayer pattern、shape、dtype 和值域；
- 实现并验证 BLC、基础 DPC、学习版 LSC、bilinear demosaic、Gray World AWB、3×3 CCM、Gamma/Tone；
- 使用 YAML 开关模块并保存中间结果；
- 为模块设计合成测试、参数实验和失败案例；
- 解释输出为何与 rawpy 不同，以及为什么 rawpy 只是成熟参考而非 ground truth；
- 在空目录中重写一个简化 Soft-ISP。

## 目录

```text
stage1_soft_isp/
├── configs/default.yaml       # 真正被统一 Pipeline 读取
├── data/
│   ├── raw/                   # 14 张 FiveK DNG，当前由 Git LFS 跟踪
│   └── references/            # rawpy 成熟渲染参考，不是标准答案
├── exercises/                 # 无完整答案的练习与毕业任务
├── materials/                 # 前置、环境、调试、资料和学习模板
├── reports/                   # 已完成实验档案；做完练习后再参考
├── scripts/
│   ├── 01_* ... 16_*         # 历史分模块实验与报告生成脚本
│   └── 17_run_pipeline.py     # 统一配置驱动入口
├── soft_isp/
│   ├── stats.py / blc.py / dpc.py / lsc.py
│   ├── demosaic.py / awb.py / ccm.py / tone.py
│   ├── metrics.py             # PSNR / SSIM / MAD
│   └── pipeline.py            # 模块组合与中间结果
└── tests/                     # 合成单元测试
```

## 快速验证

```powershell
cd stage1_soft_isp
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
python scripts/17_run_pipeline.py data/raw/T01_a0006-IMG_2787.dng
```

统一 Pipeline 默认输出到：

```text
outputs/pipeline/T01_a0006-IMG_2787/
├── preview.png
├── metadata.json
└── <stage>.json
```

如需保存中间数组，将 `configs/default.yaml` 中 `save_numpy` 改为 `true`。

## 多文件命令

脚本 04–09 会在脚本内部展开通配符，因此下面命令可在 PowerShell 使用：

```powershell
python scripts/04_plot_raw_histogram.py "data/raw/T*.dng"
python scripts/05_analyze_raw_roi.py "data/raw/T*.dng"
python scripts/06_apply_blc.py "data/raw/T*.dng"
python scripts/07_apply_dpc.py "data/raw/T*.dng"
python scripts/08_apply_demosaic.py "data/raw/T*.dng"
python scripts/09_apply_awb.py "data/raw/T*.dng"
```

引号用于确保通配符原样交给 Python，由项目统一展开。

## 主链路和实现边界

```text
RAW -> BLC -> DPC -> learning LSC -> Bilinear Demosaic
    -> Gray World AWB -> approximate metadata CCM
    -> percentile/Reinhard Tone -> Gamma -> preview
```

- LSC 是径向学习 baseline，不是实际镜头标定结果；
- DPC 是动态同色邻域 baseline，不是工厂 defect map；
- Demosaic 主实现是 bilinear；OpenCV edge-aware 只在补强实验中作对照，不是 AHD；
- CCM 使用 rawpy metadata 的简化矩阵演示矩阵校色，不等同于完整 DNG 色彩管理或 ColorChecker 标定；
- PSNR/SSIM 只衡量与给定参考的接近程度。

## 推荐学习顺序

| 周次 | 内容 | 必做证据 |
|---|---|---|
| 0 | 环境、前置、自测 | 测试通过；解释 Python 与 pip 环境 |
| 1 | RAW metadata、Bayer、histogram、ROI | 独立完成 `week1_raw_contract.md` |
| 2 | BLC、DPC、LSC | 坏点注入、参数预测、合成测试 |
| 3 | Demosaic、AWB | 独立补全 bilinear；纯色失败案例 |
| 4 | CCM、Gamma、Tone | 单像素矩阵手算；曲线和数据域说明 |
| 5 | IQA、消融、调试 | 至少四个 Debug Challenge |
| 6 | 独立毕业项目和面试复述 | 空目录重写、测试、失败案例、Git 历史 |

## 参考答案使用规则

`soft_isp/`、`scripts/` 和 `reports/` 中已有完整实现与实验档案。推荐顺序：

```text
先读任务 -> 写预测 -> 自己实现/调试 -> 通过验收 -> 再看现有代码和报告
```

直接阅读完整答案再复述，不算完成练习。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖：

- Bayer 拆分与 pattern 推断；
- per-position BLC 和无符号下溢；
- DPC 人工 hot pixel；
- bilinear 常量图与真实采样值保留；
- Gray World、identity CCM、Gamma 边界；
- IQA 指标和 YAML 配置。

## 数据与材料

- T01–T14 来自 MIT-Adobe FiveK，列表见 [raw_sample_manifest.md](materials/raw_sample_manifest.md)。
- DNG、PNG、PDF 当前通过 Git LFS 跟踪；克隆后需安装 Git LFS 并执行 `git lfs pull`。
- `materials/open_source/README.md` 说明 OpenISP 的阅读方式。
- OpenISP 中依赖 SciPy 的参考模块使用 `requirements-openisp.txt`。

## 求职证据

历史报告可以展示项目范围，但不能单独证明本人掌握。求职前应补齐：

- 独立毕业实现；
- 模块测试和 Bug 修复；
- 参数预测与失败案例；
- 分阶段 Git 提交；
- 5 分钟 Pipeline 总览和 15 分钟模块深挖。

具体见 [Git 学习证据规范](materials/git_evidence_guide.md) 和 [毕业任务](exercises/final_project.md)。
