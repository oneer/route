# Week 9：阶段二项目总结、简历和面试表达

Week 9 的目标不是继续堆模型，而是把 Week 0-8 的训练、数据、评估、失败案例和工程化线索整理成一个能复述、能追问、能继续迭代的 AI-ISP restoration 项目。

## 1. 是否需要增加内容

需要增加。原有 Week 9 已经有 leaderboard 和面试表达，但还缺少更清晰的项目交付包：

- 简历/面试可直接引用的证据链。
- 质量指标、参数量、checkpoint 大小的工程视角汇总。
- failure taxonomy 到下一步实验的闭环表达。
- 可一键复现 Week 9 项目包的脚本和结果文件。

## 2. 新增运行命令

```bash
python ai_isp_stage2/scripts/20_export_week9_project_pack.py
```

输出文件：

- `ai_isp_stage2/reports/figures/week9_project_pack/week9_project_evidence_pack.csv`
- `ai_isp_stage2/reports/week9_stage2_project_summary.md`
- `ai_isp_stage2/reports/stage2_final_project_report.md`

## 3. 阶段二 Leaderboard

| Task | Run | Best PSNR | Best SSIM | Best Step |
| --- | --- | --- | --- | --- |
| week4_sidd_tiny_standard_eval | paired_rgb_sidd_tiny_dncnn_l2_2000 | 35.5356 | 0.88367 | 1800 |
| week4_sidd_tiny_standard_eval | paired_rgb_sidd_tiny_unet_l1_1000 | 30.4453 | 0.88003 | 1000 |
| week4_sidd_tiny_standard_eval | paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | 33.3269 | 0.86223 | 1000 |
| week7_low_light_eval | low_light_sidd_tiny_unet_l1_300 | 24.7821 | 0.81468 | 300 |

当前 SIDD tiny denoise 最强结果是 `paired_rgb_sidd_tiny_dncnn_l2_2000`，PSNR 35.5356 dB，SSIM 0.88367。

## 4. 工程视角汇总

| Run | Model | Ch | Params | Ckpt MB | PSNR | SSIM |
| --- | --- | --- | --- | --- | --- | --- |
| paired_rgb_sidd_tiny_dncnn_l2_2000 | dncnn | 3 | 29507 | 0.351 | 35.5356 | 0.88367 |
| paired_rgb_sidd_tiny_unet_l1_1000 | unet | 3 | 118307 | 1.380 | 30.4453 | 0.88003 |
| paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | nafnet_lite | 3 | 104307 | 1.329 | 33.3269 | 0.86223 |
| low_light_sidd_tiny_unet_l1_300 | unet | 3 | 118307 | 1.380 | 24.7821 | 0.81468 |

这张表用于回答社招面试里常见的工程追问：模型有多大、checkpoint 多大、RGB/RAW-like 输入通道怎么变化、后续是否能部署到 ONNX/C++。

## 5. Failure Taxonomy 到下一步实验

| Run | Failure Type | Next Step |
| --- | --- | --- |
| paired_rgb_sidd_tiny_dncnn_l2_2000 | baseline smoothing / residual local error | Compare against DnCNN L1 and crop-level visual details rather than relying only on PSNR. |
| paired_rgb_sidd_tiny_dncnn_l1_2000 | strong baseline / residual local error | Use it as the current baseline; inspect error map before deciding whether Charbonnier or more data is worthwhile. |
| paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 | context-limited denoise | Use patch64 for quick ablation, but keep patch128 for final-quality runs. |
| paired_rgb_sidd_tiny_unet_l1_1000 | local texture or color residual | Inspect texture/edge crops; compare residual-output UNet or add local/color-aware analysis. |
| paired_rgb_sidd_tiny_nafnet_lite_l1_1000 | under-trained modern block / residual noise | Extend NAFNet-lite to 2000 steps or test Charbonnier loss before judging the architecture. |
| low_light_sidd_tiny_unet_l1_300 | dark-region enhancement / over-smoothing | Add exposure/noise-specific IQ metrics, inspect dark ROI, and compare brightness/color statistics before changing model size. |

Week 8 的价值在 Week 9 里要表达成“诊断能力”：看到局部失败后，能判断是数据、loss、模型容量、训练步数还是任务定义的问题。

## 6. 简历表述

简洁版：

```text
基于 PyTorch 搭建 AI-ISP 图像恢复实验闭环，完成 SIDD paired RGB 去噪、synthetic low-light enhancement、NAFNet-lite 复现、PSNR/SSIM 评估、error map 和 failure crop 诊断；在 SIDD tiny 上 DnCNN residual baseline 达到 35.54 dB PSNR / 0.8837 SSIM，并整理参数量、checkpoint 大小和后续 ONNX/C++ 部署路径。
```

详细版：

```text
构建 AI-ISP Stage2 图像恢复项目：从 toy RGB denoise sanity check 出发，整理 SIDD Small sRGB paired train/val 数据，建立 noisy input baseline，对比 DnCNN residual、UNet、NAFNet-lite，并扩展 pseudo RAW/RGGB bridge 和 synthetic low-light enhancement。项目包含训练脚本、评估脚本、leaderboard、triplet/error map/failure crop 可视化、failure taxonomy、工程化参数汇总和面试复述材料，可解释 residual denoise、PSNR/SSIM 差异、RAW pack 输入差异和现代 restoration block 在小数据下的训练不足问题。
```

## 7. 面试讲述框架

1. 先用 toy RGB denoise 跑通 Dataset -> Model -> Loss -> Metric -> Checkpoint -> Visualization。
2. 再接入 SIDD paired RGB，先测 noisy input baseline，保证模型收益不是凭空判断。
3. 用 DnCNN residual 建强基线，再对比 UNet 和 NAFNet-lite，解释结构假设和训练代价。
4. 用 PSNR/SSIM、triplet、error map 和 failure crop 联合判断，而不是只看单一指标。
5. 用 pseudo RAW/RGGB 和 low-light enhancement 把 RGB restoration 连接到 AI-ISP 场景。
6. 最后把 failure case 分类，决定下一步是扩数据、改 loss、改模型、加训练步数还是做部署验证。

## 8. 高频追问

**Q1：为什么 DnCNN 比更复杂的结构还强？**

当前任务是小规模 paired RGB denoise，输入和 clean 的结构高度一致，主要差异是噪声。Residual DnCNN 直接学习噪声残差，任务假设更匹配；复杂模型在数据少、训练短或配置不充分时不一定占优。

**Q2：为什么 low-light 不能和 SIDD denoise 直接横向比 PSNR？**

两者任务定义不同。Denoise 主要恢复噪声，low-light 同时涉及增亮、颜色恢复和噪声控制，所以 PSNR 只能在同任务内比较，跨任务要结合视觉和任务目标解释。

**Q3：Week 8 failure case 对 Week 9 有什么价值？**

它让项目从“跑出指标”升级到“能诊断问题”。社招面试更看重你是否能根据失败区域推断数据、loss、模型或训练策略问题，并提出下一轮实验。

**Q4：这个阶段还不能证明什么？**

不能证明真实量产 ISP tuning、AE/AWB/AF 联调、平台级 ISP 调试经验或 Imatest/iQ-Analyzer 实操经验；它证明的是 AI-ISP 图像恢复方向的实验闭环、评估诊断和工程化准备能力。

## 9. Week 10-12 衔接

Week 9 之后应优先补工程化闭环：Week 10 汇总参数量、checkpoint 大小和部署候选；Week 11 导出 ONNX 并做 PyTorch/ONNX 输出对齐；Week 12 做 C++ OpenCV DNN smoke test 和 CPU latency 记录。

## 10. 自检问题

1. noisy、clean、output、loss、metric 的关系是什么？
2. 为什么 paired 数据必须像素对齐？
3. DnCNN residual 为什么适合 denoise？
4. UNet 为什么可能 SSIM 接近但 PSNR 较低？
5. NAFNet-lite 结果不如 DnCNN 时，应该先怀疑结构还是训练设置？
6. RAW pack 为什么通常是 4 通道？
7. error map 和 failure crop 分别能定位什么问题？
8. 这个项目如何讲成完整 AI-ISP restoration baseline？
