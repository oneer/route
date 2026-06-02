# Week 9：阶段二项目总结、简历和面试表达

Week9 的目标是把阶段二收束成一个完整项目。

不是只说“我跑过几个模型”，而是能讲成：

```text
我从 toy RGB 去噪开始，
逐步接入真实 SIDD paired RGB 数据，
建立 baseline、现代模型、评估脚本、低光增强和 failure case 分析，
最终形成一套可复现的 AI-ISP 学习项目。
```

## 1. 本周实现了什么

新增脚本：

```text
scripts/11_export_stage2_summary.py
```

它读取前面生成的 metrics summary：

```text
week4_sidd_tiny_standard_eval/metrics_summary.csv
week7_low_light_eval/metrics_summary.csv
```

输出阶段二总表：

```text
reports/figures/week9_stage2_summary/stage2_leaderboard.csv
reports/figures/week9_stage2_summary/stage2_leaderboard.png
```

运行命令：

```bash
python ai_isp_stage2/scripts/11_export_stage2_summary.py --metric-csvs ai_isp_stage2/reports/figures/week4_sidd_tiny_standard_eval/metrics_summary.csv ai_isp_stage2/reports/figures/week7_low_light_eval/metrics_summary.csv --output-dir ai_isp_stage2/reports/figures/week9_stage2_summary
```

## 2. 阶段二总榜

![Stage2 leaderboard](figures/week9_stage2_summary/stage2_leaderboard.png)

> 图说明：这张图汇总阶段二最重要的可复现实验。SIDD tiny 标准去噪中 DnCNN residual 当前最强，NAFNet-lite 标准版明显优于短训版；低光增强任务单独列出，因为它的输入输出难度和普通去噪不同。

总表：

| Task | Run | Best PSNR | Best SSIM |
|---|---|---:|---:|
| SIDD tiny denoise | DnCNN residual | 35.5356 | 0.88367 |
| SIDD tiny denoise | UNet | 30.4453 | 0.88003 |
| SIDD tiny denoise | NAFNet-lite | 33.3269 | 0.86223 |
| Synthetic low-light | UNet | 24.7821 | 0.81468 |

## 3. 阶段二你已经做完了什么

按能力拆开看：

| 能力 | 已完成证据 |
|---|---|
| 训练闭环 | TinyCNN / DnCNN / UNet / NAFNet-lite 都能训练 |
| 真实数据入口 | SIDD Small sRGB 整理成 80/20 paired subset |
| baseline 思维 | noisy input baseline、low-light input baseline |
| 模型对比 | DnCNN、UNet、NAFNet-lite 标准版对比 |
| 评估体系 | PSNR、SSIM、三联图、error map、局部 crop |
| ISP 过渡 | pseudo Bayer、RAW pack、demosaic 可视化 |
| 低光增强 | synthetic low-light -> clean UNet 实验 |
| 面试材料 | 每周报告含概念、命令、结果、问题回答 |

## 4. 可以写进简历的版本

简洁版：

```text
基于 PyTorch 搭建 AI-ISP 图像恢复实验闭环，完成 SIDD paired RGB 去噪、低光增强、NAFNet-lite 复现和评估可视化；实现 PSNR/SSIM、三联图、error map、局部 failure crop 分析，在 SIDD tiny 上 DnCNN baseline 达到 35.54 dB PSNR / 0.8837 SSIM。
```

详细版：

```text
构建 AI-ISP Stage2 学习项目：从 toy RGB denoise 到真实 SIDD Small sRGB paired 数据，编写数据整理、baseline 测量、模型训练、评估汇总和 failure case 分析脚本；对比 DnCNN residual、UNet、NAFNet-lite，并扩展 synthetic low-light enhancement 实验。形成可复现周报、结果图和面试问答，能够解释 residual denoise、RAW pack、PSNR/SSIM 差异和现代恢复模型训练不足问题。
```

## 5. 面试讲述框架

可以按这个顺序讲：

```text
1. 我先从 toy RGB 去噪跑通训练闭环；
2. 然后整理 SIDD Small sRGB 成 paired train/val；
3. 先测 noisy input baseline，避免模型把图变差；
4. 用 DnCNN residual 建立强 baseline；
5. 再对比 UNet 和 NAFNet-lite；
6. 用 PSNR/SSIM + 三联图 + error map 评价；
7. 最后做 pseudo RAW bridge 和 synthetic low-light，连接到 AI-ISP 场景。
```

## 6. 高频面试题和参考回答

**Q1：你这个项目和普通图像去噪 demo 有什么区别？**

普通 demo 往往只跑一个模型。我这里建立了完整闭环：真实 paired 数据整理、baseline 测量、多模型对比、指标曲线、三联图、error map、failure crop、周报分析和面试复述。

**Q2：为什么 DnCNN 这么简单反而最好？**

当前任务是 SIDD tiny RGB 去噪，输入和 clean 主体内容高度一致，差异主要是噪声。DnCNN residual 直接预测噪声，再从输入中减去，非常贴合任务。复杂模型如果训练不足或设置不合适，不一定立刻超过它。

**Q3：NAFNet-lite 的价值是什么？**

它让项目从基础 CNN baseline 进入现代恢复 block。短训版表现一般，但标准版从 `26.8194` PSNR 提升到 `33.3269`，说明结构能学习，只是需要足够训练和合适配置。

**Q4：为什么要做 low-light synthetic？**

它把任务从单纯去噪扩展到增强：模型要同时恢复亮度、颜色和噪声。虽然 synthetic 不能替代真实 SID RAW，但可以验证低光增强训练闭环，为后续 RAW low-light 做准备。

**Q5：你怎么判断模型真的有效？**

先看是否超过 input baseline，再看 validation PSNR/SSIM 曲线是否提升，接着看三联图是否视觉变好，最后用 error map 和局部 crop 检查失败区域。

**Q6：如果继续做，你下一步做什么？**

我会做三个方向：第一，扩大 SIDD 子集到 120/40 或更大；第二，给 NAFNet-lite 跑 2000 steps 或尝试 Charbonnier loss；第三，接入真实 RAW/SID，使用 RGGB pack 做 low-light RAW enhancement。

## 7. 阶段二通过标准

如果你能独立回答下面问题，阶段二就真正学完了：

1. noisy、clean、output、loss、metric 的关系是什么；
2. 为什么 paired 数据必须像素对齐；
3. DnCNN residual 为什么适合去噪；
4. UNet 为什么 SSIM 高但 PSNR 可能低；
5. NAFNet-lite 为什么短训不能下最终结论；
6. RAW pack 为什么是 4 通道；
7. 低光增强为什么不只是去噪；
8. error map 和 failure crop 能定位什么问题；
9. 你如何把这个项目讲成一个完整 AI-ISP 学习项目。
