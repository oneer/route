# 阶段 1：传统 ISP 与 RAW 基础

这个文件夹用于阶段 1 学习：从真实 RAW / DNG 输入开始，逐步完成一个可解释的 Python Soft-ISP Pipeline。

## 阶段目标

- 能读取真实 RAW / DNG，并解释 metadata、black level、white level、Bayer pattern。
- 能实现并验证基础 ISP 模块：BLC、DPC、LSC、Demosaic、AWB、CCM、Gamma / Tone。
- 能为至少 5 张不同场景 RAW 生成处理结果、参考输出、统计指标和实验报告。
- 能说清楚每个模块的输入输出、核心假设、参数影响、失败场景和验证方法。

## 建议顺序

1. 阅读 `materials/stage1_start_here.md`，明确 6 周路线和今天要做的事。
2. 按 `materials/raw_sample_manifest.md` 准备 5 张 RAW / DNG 样张。
3. 安装依赖：`pip install -r requirements.txt`。
4. 运行 `scripts/01_inspect_raw.py`，先完成 RAW metadata 和统计检查。
5. 每周把实验结论写入 `reports/`，不要只留下代码。

## 当前交付物

- `materials/resources.md`：课程、论文、开源项目、数据集入口。
- `materials/raw_sample_manifest.md`：RAW 样张登记表。
- `materials/module_study_template.md`：每个 ISP 模块的学习模板。
- `materials/notes/paper_reading_template.md`：论文阅读模板。
- `reports/stage1_report.md`：阶段总报告模板。
- `reports/week1_raw_statistics.md`：第一周报告模板。

## 数据约定

大体积 RAW / DNG 和参考图不提交到 Git：

- RAW / DNG 放到 `data/raw/`
- rawpy / Lightroom / LibRaw 参考输出放到 `data/references/`
- 报告图片放到 `reports/figures/`

