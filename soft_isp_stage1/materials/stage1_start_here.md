# 从这里开始

## 本阶段成功标准

阶段 1 不是追求商业 ISP 效果，而是建立可解释的数据流：

1. 输入一张真实 RAW / DNG，能输出可观看 RGB。
2. 每个模块能单独打开/关闭，并保存中间结果。
3. 至少处理 5 张不同场景 RAW：日光、室内、低光、高动态范围、纹理/纯色。
4. 每张图都有 rawpy 或 Lightroom 参考输出。
5. 能解释你的 pipeline 和参考输出之间至少 5 类差异。

## 今天先做什么

1. 找 1 张 DNG 放入 `data/raw/`。
2. 安装依赖：`pip install -r requirements.txt`。
3. 运行：

```bash
python scripts/01_inspect_raw.py data/raw/your_sample.dng
```

4. 把输出中的 metadata 和统计结论填到 `materials/raw_sample_manifest.md`。
5. 写第一篇笔记：`reports/week1/raw_statistics.md`。

## 6 周路线

| 周期 | 主题 | 交付物 |
|---|---|---|
| Week 0.5 | 环境、数据和项目骨架 | 依赖、样张、metadata 检查脚本 |
| Week 1 | RAW / Sensor 数据直觉 | 四通道统计、histogram、ROI 分析 |
| Week 2 | BLC / DPC / LSC | 前端校正模块和 before/after |
| Week 3 | Demosaic / AWB | Bayer 到 RGB、白平衡实验 |
| Week 4 | CCM / Gamma / Tone | 色彩映射和显示映射 |
| Week 5 | IQA / 模块消融 / 报告 | 指标、对比图、阶段报告 |

## 每个模块都回答这 7 个问题

1. 输入是什么？
2. 输出是什么？
3. 解决什么问题？
4. 核心假设是什么？
5. 参数怎么调？
6. 怎么验证？
7. 失败场景是什么？
