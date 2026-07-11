# 从这里开始：阶段一唯一学习入口

阶段一的目标不是把已有脚本全部重跑一遍，而是能从陌生 DNG 独立完成、验证并讲清一条基础 RAW-to-RGB Soft-ISP。已有 `reports/` 是实验档案和参考答案；先预测、动手和验证，再阅读结论。

## 先完成 15 分钟冒烟验证

```powershell
cd stage1_soft_isp
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
python scripts/17_run_pipeline.py data/raw/T01_a0006-IMG_2787.dng
```

成功时应看到 30 项合成测试通过，并在 `outputs/pipeline/T01_a0006-IMG_2787/` 得到 `preview.png`、`metadata.json` 和逐阶段统计 JSON。若失败，先看 [环境搭建](environment_setup.md) 和 [调试手册](debugging_guide.md)。

## 先建立一张完整地图

```text
RAW/DNG metadata
  -> BLC -> DPC -> 学习版 LSC
  -> Bilinear Demosaic -> Gray World AWB -> metadata 简化 CCM
  -> Tone Mapping -> Gamma / sRGB OETF -> Preview
  -> ROI IQA、消融、故障诊断
```

三条证据边界必须从第一天就记住：

- rawpy 输出是成熟渲染参考，不是 ground truth；
- OpenCV edge-aware 是独立 demosaic baseline，不是 AHD；
- synthetic flat-field 和相对 rawpy 的 DeltaE 都不是产品级标定证据。

完整的报告—代码—参数—脚本—产物—测试关系见 [教程化审查与证据对应表](../reports/stage1_tutorial_audit.md)。
规范、论文、官方 API 和开源项目来源见 [参考文献与外部资料](../reports/references.md)。

## 六周学习闭环

| 周次 | 学习目标 | 动手任务 | 产物与验收 |
|---|---|---|---|
| Week 1 | 看懂 RAW、CFA、metadata、曝光和 ROI | 完成 `exercises/week1_raw_contract.md`，手算 4×4 Bayer 拆分 | 能解释 shape/dtype/range、R/Gr/Gb/B、black/white level |
| Week 2 | 理解 BLC/DPC/LSC 的物理来源和顺序 | 完成坏点注入；预测 black level 和 LSC gain 改动 | 测试、mask/crop、参数预测、真实标定边界 |
| Week 3 | 从 Bayer 恢复 RGB 并理解 AWB 失败 | 补全 bilinear 练习；选纯色或高光场景分析 | edge/texture crop、AWB gain 与失败案例 |
| Week 4 | 区分颜色校正、动态范围压缩和显示编码 | 手算一个 CCM 像素；画 Gamma/sRGB/S-curve | 数据域表、曲线、clip 风险和矩阵方向 |
| Week 5 | 建立模块级评价而非只看最终图 | 做模块开关消融和一个参数扫描 | ROI 指标、主观标签、证据边界 |
| Week 6 | 对未见 DNG 做阶段毕业验收 | 完成 `exercises/final_project.md` | 中间结果、测试、失败案例、报告与面试复述 |

每周先读 `reports/weekN/summary.md`，再按问题进入模块报告；不要从 14 张全量结果表开始阅读。

## 每个模块按同一顺序学习

```text
直觉 -> 物理来源 -> 数据域 -> 数学与小例子
     -> 代码调用 -> 参数预测 -> 实验 -> 失败案例 -> 工程升级
```

学习记录使用 [模块学习模板](module_study_template.md)。至少回答：

1. 为什么这个问题存在，为什么放在当前位置？
2. 输入输出的域、shape、dtype、range、线性状态是什么？
3. 公式的变量、假设和边界是什么？
4. 参数增大/减小会发生什么，副作用是什么？
5. 哪段代码和哪个配置真正实现了它？
6. 图、表、JSON 支持什么结论，又没有证明什么？
7. 典型伪影如何向下游传播？
8. 学习版与产品级方法还差哪些数据和工程能力？

## 阶段完成标准

- 能对一张未见 DNG 完成 metadata 检查和基础 Pipeline；
- 能保存并解释至少三个中间结果；
- 能独立实现 BLC、bilinear demosaic、Gray World AWB 和 3×3 CCM；
- 能用测试、参数实验和局部 ROI 诊断至少一个失败案例；
- 能准确区分仓库实测、理论预期和外部方法；
- 能在 5 分钟讲清完整 Pipeline，在 15 分钟讲深一个模块。
