# 阶段一教程化审查与证据对应表

本表用于回答“报告中的结论由什么代码、配置、命令和产物支持”。审查范围是 `stage1_soft_isp/` 当前主链路；历史报告保留为实验档案，不作为独立掌握证明。

## 1. 审查结论

- 已完成：14 张 DNG 的 metadata/统计、BLC、动态 DPC、学习版径向 LSC、bilinear demosaic、Gray World AWB、metadata 简化 CCM、Tone/Gamma、rawpy 参考对比、Week 5 消融、Week 6 局部对比和统一配置驱动 Pipeline。
- 已验证：`python -m unittest discover -s tests -v` 运行 15 项测试并通过；`scripts/17_run_pipeline.py` 可对 T01 生成最终预览、metadata 和各阶段统计 JSON。
- 重复内容：`reports/week3_demosaic_report.md` 是早期根目录版本，主线应阅读 `reports/week3/demosaic_report.md`；前者保留归档，不再作为导航主入口。
- 只有方案、尚无实验闭环：BLC `black_level + (-10, 0, +10)` 扫描、DPC `mad_k` 扫描及 precision/recall 完整练习、真实 flat-field LSC、ColorChecker CCM、dark-frame 噪声标定。
- 证据边界：rawpy 是成熟渲染参考，不是 ground truth；OpenCV edge-aware 是独立 baseline，不是 AHD；synthetic flat-field 只验证 mesh 流程；当前 DeltaE 只衡量输出对 rawpy 参考的差异，不是标准 ColorChecker DeltaE。

## 2. 报告—实现—配置—脚本—产物—测试对应表

| 教学章节 | 核心实现 | 配置参数 | 运行脚本 | 已有证据 | 测试证据 |
|---|---|---|---|---|---|
| Week 1 RAW/metadata | `soft_isp/stats.py`、`orientation.py` | `raw.*` | `01_inspect_raw.py`、`03_dump_raw_metadata_table.py`、`04_plot_raw_histogram.py`、`05_analyze_raw_roi.py` | `reports/raw_stats/T01.json` 至 `T14.json`、histogram/ROI 图 | `test_stats_blc.py` 的 pattern 与 Bayer 拆分 |
| Week 2 BLC | `soft_isp/blc.py` | metadata 或 `raw.black_level/white_level` | `06_apply_blc.py` | `*_blc.json`、视觉与 histogram 对比 | per-position black level、无符号下溢、归一化边界 |
| Week 2 DPC | `soft_isp/dpc.py` | `parameters.dpc.min_delta/mad_k` | `07_apply_dpc.py`、`exercises/week2_dpc_injection.py` | `*_dpc.json`、mask overlay、repair crop | 人工 hot pixel 检出与修复 |
| Week 2 LSC | `soft_isp/lsc.py` | `parameters.lsc.edge_gains/power` | `14_apply_lsc.py`、`16_close_mastery_gaps.py` | `*_lsc.json`、径向对比、synthetic mesh MAE | 暂无专门 LSC 单测 |
| Week 3 Demosaic | `soft_isp/demosaic.py` | Bayer pattern 来自 metadata | `08_apply_demosaic.py`、`16_close_mastery_gaps.py` | `*_demosaic.json`、bilinear/OpenCV 对比图 | 常量 Bayer、采样值保持 |
| Week 3 AWB | `soft_isp/awb.py` | `parameters.awb.*` | `09_apply_awb.py`、`16_close_mastery_gaps.py` | `*_awb.json`、Gray World/White Patch/Gray ROI 对比 | Gray World 通道均值校正 |
| Week 4 CCM | `soft_isp/ccm.py` | DNG/rawpy 暴露矩阵的简化使用 | `10_apply_ccm.py`、`16_close_mastery_gaps.py` | CCM 对比图、相对 rawpy 的 DeltaE | identity CCM、矩阵 shape 校验 |
| Week 4 Tone/OETF | `soft_isp/tone.py`；sRGB/S-curve 对比在 `16_close_mastery_gaps.py` | `parameters.tone.method/percentile/gamma` | `11_apply_gamma.py`、`12_apply_tone_mapping.py`、`16_close_mastery_gaps.py` | 曲线图、Tone 对比、Week 5/6 JSON | Gamma 参数与 uint8 边界 |
| Week 5 IQA/消融 | `soft_isp/metrics.py` | 各模块开关 | `15_evaluate_pipeline.py` | `week5_iqa_ablation.json`、14 张消融图 | 相同图像指标 |
| Week 6 综合验收 | `soft_isp/pipeline.py` | `configs/default.yaml` | `17_run_pipeline.py` | `preview.png`、`metadata.json`、逐阶段 JSON | `tests/` 15 项合成测试 |

## 3. 数据域总表

范围是本仓库默认实现的实际约定，不代表所有相机 ISP。

| 阶段 | shape / 通道 | dtype | 典型范围 | 线性 | clip / 归一化 |
|---|---|---|---|---|---|
| DNG visible RAW | `(H,W)` Bayer | 通常 `uint16` 容器 | black level 到 white level；有效 bit depth 由 metadata 决定 | 是 | 尚未归一化 |
| BLC | `(H,W)` Bayer | `uint16` | `0..white-black(position)` | 是 | 减逐位置 black map 后 clip |
| DPC | `(H,W)` Bayer | `uint16` | 与 BLC 相同 | 是 | 仅替换检测点，不归一化 |
| 学习版 LSC | `(H,W)` Bayer | `float32` | 可能超过输入上限，随后按 white level 限制 | 是 | 四通道径向 gain；不是实机标定 |
| Demosaic | `(H,W,3)` RGB | `float32` | 以 RAW 码值尺度为主 | 是 | 插值，不做显示归一化 |
| AWB | `(H,W,3)` RGB | `float32` | gain 后可能增大 | 是 | R/B gain 有上限，并按 white level 限制 |
| CCM | `(H,W,3)` RGB | `float32` | 可出现负值或超 white level | 是 | 当前实现按 white level clip |
| Tone normalization | `(H,W,3)` RGB | `float32` | `0..1` | 是，直到曲线应用 | percentile/Reinhard 后 clip |
| Gamma / sRGB OETF | `(H,W,3)` RGB | `float32` | `0..1` | 否，显示编码域 | 非线性编码 |
| PNG preview | `(H,W,3)` RGB | `uint8` | `0..255` | 否 | 量化并按 orientation 旋正 |

## 4. 可用现有数据补齐与必须新增数据

可直接用现有代码/合成数据补齐：

- BLC black-level 偏置扫描；
- DPC 注入坏点、`mad_k`/阈值扫描和 precision/recall；
- demosaic 统一 edge/texture crop；
- LSC strength 与 Tone 曲线参数扫描；
- 代表性样张 T01、T08、T13、T14 的图像解读。

必须新增真实采集或标准数据：

- 真实均匀光源 flat-field：验证镜头 shading、PRNU 和四通道 mesh；
- dark frame/多曝光平场：估计 read noise、shot-noise slope 和坏点稳定性；
- 标准光源下 ColorChecker：拟合 CCM 并计算标准色块 DeltaE；
- 连续 RAW 序列：评价 AWB、DPC、Tone 的时序稳定性；
- 性能目标平台：评价延迟、峰值内存和定点误差。

## 5. 学习者如何使用证据

先运行测试和一张样张的统一 Pipeline，再阅读周总结。模块报告里的全量 14 张结果用于查证，不要求逐张背诵；深入分析优先选 T01（常规样张）、T08（结构/颜色差异明显）、T13（AWB/颜色挑战）和 T14（高光与局部差异）。每个结论都应同时写出“证据支持什么”和“没有证明什么”。
