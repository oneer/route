# 阶段二统一升级计划：AI-ISP 图像恢复与部署验证

## 1. 文档目的

这份文档把阶段二已有的几份报告和升级建议整理成一份单独的执行计划，作为后续优化、复盘、简历包装和面试讲述的总入口。

参考来源：

```text
stage2_learning_flow.md
stage2_final_project_report.md
stage2_engineering_summary.md
stage2_upgrade_plan.md
stage2_weekly_upgrade_from_reports.md
stage2_3year_portfolio_upgrade.md
stage2_optimization_plan.md
```

这份计划不替代原周报和最终报告。它的作用是回答一个更直接的问题：

```text
阶段二现在已经做到哪里，距离“社招 3 年可讲项目”还差什么，下一步按什么顺序补。
```

## 2. 项目定位

阶段二应该定位为：

```text
AI-ISP 图像恢复与部署验证 baseline 项目
```

核心叙事是：

```text
从 toy RGB denoise 跑通训练闭环，
到 SIDD paired RGB 真实去噪实验，
再到多模型对比、客观指标、可视化诊断、pseudo RAW/RGGB bridge、
low-light enhancement 和 ONNX/C++ 部署验证入口。
```

不要把它包装成：

```text
量产 ISP tuning 项目
真实车载摄像头平台调试项目
高通 / MTK / 海思 ISP 平台项目
完整工业 RAW ISP 系统
SOTA 去噪算法项目
```

## 3. 当前已完成基线

| 模块 | 已有证据 | 说明 |
|---|---|---|
| 学习路径 | Week 0-9 报告 | 从训练基础到项目总结已经成体系 |
| 数据入口 | toy RGB、SIDD tiny、low-light、pseudo RAW/RGGB | 覆盖 synthetic、真实 paired RGB 和 RAW-like 输入 |
| 模型训练 | TinyCNN、DnCNN、UNet、NAFNet-lite | 已有基础 CNN、encoder-decoder、现代 restoration block |
| 评估体系 | PSNR、SSIM、triplet、error map、failure crop | 已具备基础画质评估和局部失败分析 |
| 工程摘要 | 参数量、checkpoint 大小、leaderboard | 已从单纯指标升级到工程表雏形 |
| 部署入口 | ONNX export、C++ OpenCV DNN 骨架 | 已建立部署方向，但还需要实际跑通和记录延迟 |

当前核心结果：

| 任务 | 模型 | PSNR | SSIM | 结论 |
|---|---|---:|---:|---|
| SIDD tiny RGB denoise | DnCNN residual | 35.5356 | 0.88367 | 当前最稳 baseline |
| SIDD tiny RGB denoise | NAFNet-lite | 33.3269 | 0.86223 | 现代 block 跑通，但还需长训和调参 |
| SIDD tiny RGB denoise | UNet | 30.4453 | 0.88003 | 结构保持尚可，像素误差不如 DnCNN |
| Synthetic low-light enhancement | UNet | 24.7821 | 0.81468 | 低光增强链路跑通 |

当前工程表已有字段：

| 模型 | Params | Checkpoint MB | PSNR | SSIM |
|---|---:|---:|---:|---:|
| DnCNN residual | 29507 | 0.351 | 35.5356 | 0.88367 |
| UNet | 118307 | 1.380 | 30.4453 | 0.88003 |
| NAFNet-lite | 104307 | 1.329 | 33.3269 | 0.86223 |

## 4. 当前主要短板

阶段二现在不是“没有项目”，而是已经有项目闭环，但社招 3 年口径还需要补强下面几块。

| 短板 | 问题 | 为什么影响项目含金量 |
|---|---|---|
| baseline 不够集中 | noisy input baseline 分散在不同报告里 | 面试时很难一眼说明模型比输入提升多少 |
| 指标偏少 | 主要是 PSNR/SSIM | 不足以说明视觉质量、噪声残留、锐度、颜色稳定 |
| 消融不够统一 | L1/L2、patch、steps、RGB/RGGB 没有总表 | 不容易体现算法判断和工程取舍 |
| pseudo RAW 还需训练结果 | 已有 preview 和 dataset 入口 | 需要 metrics 和 checkpoint 证明 RAW-like 路径可训练 |
| 部署闭环未完成 | 有 ONNX/C++ 骨架 | 缺少实际 ONNX 文件、C++ 输出图、latency |
| failure case 需要分类 | 已有 crop | 还需要失败类型、原因假设和下一步改法 |
| 最终报告需重组 | 内容完整但分散 | 需要面向项目交付而不是学习流水账 |

## 5. 升级目标

升级后的阶段二需要从：

```text
我跑了几个模型，拿到了 PSNR/SSIM
```

升级为：

```text
我构建了一个可复现的 AI-ISP restoration baseline，
能从数据、模型、指标、失败案例和部署成本几个角度判断方案是否有效。
```

最终验收形态：

```text
数据构建
-> noisy input baseline
-> DnCNN / UNet / NAFNet-lite / pseudo RGGB 对比
-> PSNR / SSIM / noise / sharpness / latency / model size
-> failure case taxonomy
-> ONNX / C++ inference smoke test
-> 一页项目总结和简历表达
```

## 6. 升级路线总览

| 优先级 | 升级线 | 目标 | 验收物 |
|---:|---|---|---|
| P0 | baseline 重测与汇总 | 统一 noisy input、low-light input、pseudo RAW input baseline | baseline CSV + 报告 |
| P1 | 指标体系升级 | 从 PSNR/SSIM 扩展到质量、噪声、锐度、颜色、成本 | engineering summary v2 |
| P2 | 实验矩阵补齐 | 补齐 loss、patch、steps、RGB/RGGB 对比 | ablation 总表 |
| P3 | pseudo RAW 训练闭环 | 证明 RAW-like 4 通道输入可训练 | metrics.csv + checkpoint + 对比图 |
| P4 | ONNX/C++ 部署闭环 | 证明模型能离开 PyTorch | ONNX 文件 + C++ 输出图 + latency |
| P5 | failure case 升级 | 从“看图”升级到“问题归因” | failure taxonomy 报告 |
| P6 | 最终材料重组 | 面向社招项目表达 | 最终项目报告 v2 + 简历条目 |

## 7. P0：baseline 重测与汇总

### 目标

把所有模型结果都放到清楚的 baseline 上比较，避免只报模型 PSNR/SSIM。

### 必做项

| baseline | 输入 | 对比对象 | 输出 |
|---|---|---|---|
| noisy RGB baseline | SIDD noisy | SIDD clean | PSNR/SSIM、三联图、error map |
| low-light input baseline | synthetic low-light | clean | PSNR/SSIM、亮度分布 |
| pseudo RAW baseline | pseudo RGGB/demosaic | clean RGB | PSNR/SSIM、preview |

### 验收标准

```text
reports/figures/stage2_baselines/baseline_summary.csv
reports/stage2_baseline_report.md
```

baseline 表至少包含：

| Method | Data | PSNR | SSIM | Notes |
|---|---|---:|---:|---|
| Noisy Input | SIDD tiny RGB | 待测 | 待测 | 模型提升参照 |
| Low-light Input | synthetic low-light | 14.8932 | 待补 | low-light UNet 参照 |
| Pseudo RAW Input | pseudo RGGB | 待测 | 待测 | RAW-like 路径参照 |

## 8. P1：指标体系升级

PSNR 和 SSIM 保留，但新增轻量 IQ 和工程指标。

| 指标 | 类型 | 作用 |
|---|---|---|
| PSNR | 像素误差 | 衡量与 clean 的像素级接近程度 |
| SSIM | 结构相似 | 衡量结构和局部统计相似度 |
| flat noise std | 噪声残留 | 判断平坦区域是否去干净 |
| Laplacian sharpness | 细节保真 | 判断是否过度平滑 |
| channel mean / cast score | 颜色稳定 | 判断是否产生偏色 |
| params | 模型成本 | 判断模型容量 |
| checkpoint MB | 存储成本 | 判断部署体积 |
| ONNX size | 部署成本 | 判断导出模型大小 |
| latency | 推理速度 | 判断工程可用性 |

### 最低验收表

| Method | PSNR | SSIM | Noise Std | Sharpness | Params | CKPT MB | Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Noisy Input | 待测 | 待测 | 待测 | 待测 | - | - | - |
| DnCNN residual | 35.5356 | 0.88367 | 待测 | 待测 | 29507 | 0.351 | 待测 |
| UNet | 30.4453 | 0.88003 | 待测 | 待测 | 118307 | 1.380 | 待测 |
| NAFNet-lite | 33.3269 | 0.86223 | 待测 | 待测 | 104307 | 1.329 | 待测 |

## 9. P2：实验矩阵补齐

### 必做消融

| 实验 | 目的 | 验收 |
|---|---|---|
| DnCNN L1 vs L2 | 比较 loss 对 PSNR 和视觉平滑的影响 | 同数据同 steps 对比 |
| patch 64 vs 128 | 比较上下文范围影响 | 同模型同 loss 对比 |
| 300 vs 1000 vs 2000 steps | 判断训练是否收敛 | 曲线和 best/last 指标 |
| DnCNN vs UNet vs NAFNet-lite | 模型结构对比 | 统一 leaderboad |
| RGB vs pseudo RGGB | 输入形态对比 | RGB/RGGB 同表 |

### 统一实验表字段

| Run | Data | Model | Loss | Patch | Steps | Params | PSNR | SSIM | Noise Std | Sharpness | Latency |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|

## 10. P3：pseudo RAW/RGGB 训练闭环

### 目标

让 pseudo RAW/RGGB 不只停留在可视化，而是进入可训练、可评估、可对比的路径。

已有入口：

```text
ai_isp_stage2/ai_isp/data/pseudo_raw.py
ai_isp_stage2/ai_isp/data/paired_pseudo_raw_dataset.py
ai_isp_stage2/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
ai_isp_stage2/scripts/12_preview_pseudo_raw_dataset.py
```

建议命令：

```bash
python ai_isp_stage2/scripts/12_preview_pseudo_raw_dataset.py
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
```

验收标准：

```text
RGGB preview 图存在
4-channel DnCNN 能训练
metrics.csv 生成
best_psnr.pth 生成
RGB vs RGGB 对比进入总表
```

## 11. P4：ONNX/C++ 部署闭环

### 目标

把项目从 Python 训练推进到部署验证，让它具备工程讨论价值。

已有入口：

```text
ai_isp_stage2/deployment/export_onnx.py
ai_isp_stage2/deployment/cpp_onnx_infer/
ai_isp_stage2/deployment/README.md
```

目标链路：

```text
PyTorch checkpoint
-> ONNX export
-> PyTorch / ONNX 输出一致性检查
-> C++ OpenCV DNN inference
-> 输出图保存
-> latency 统计
```

验收标准：

| 项 | 验收 |
|---|---|
| ONNX export | 生成 `dncnn_sidd_tiny.onnx` |
| 一致性 | 同输入下 PyTorch 与 ONNX 输出 MAE 可解释 |
| C++ inference | 输入 noisy 图，输出 restored 图 |
| latency | 记录 CPU 单张图或 128x128 crop 推理耗时 |
| 汇总 | latency 加入 engineering summary |

## 12. P5：failure case 升级

### 目标

把 failure crop 从“展示局部图”升级为“失败类型、原因和下一步实验”的分析材料。

| 失败类型 | 可能原因 | 下一步 |
|---|---|---|
| 纹理被抹平 | L2/MSE 倾向平均解 | 对比 L1/Charbonnier，增加 sharpness 指标 |
| 暗部残噪 | low-light 噪声复杂 | 按亮度分桶评估 |
| 边缘伪影 | patch/context 不足 | patch 128/更大模型对比 |
| 色偏 | RGB 通道统计不稳定 | 加 channel mean / cast score |
| 泛化弱 | tiny 数据规模小 | 扩大 SIDD subset |

建议输出：

```text
reports/stage2_failure_case_taxonomy.md
reports/figures/stage2_failure_taxonomy/
```

## 13. P6：最终材料重组

最终报告不要按 Week 0-9 流水账写，而要按项目交付结构组织。

推荐结构：

```text
1. 背景：AI-ISP 中的 denoise / low-light / 画质评估问题
2. 数据：toy RGB -> SIDD paired RGB -> pseudo RAW/RGGB
3. 方法：DnCNN residual / UNet / NAFNet-lite
4. baseline：noisy input / low-light input / pseudo RAW input
5. 实验：PSNR / SSIM / IQ metrics / ablation
6. 可视化：triplet / error map / failure crop
7. 工程：params / checkpoint / ONNX / C++ / latency
8. 结论：当前最优方案、失败边界、下一步优化
9. 岗位匹配：能证明什么，不能证明什么
```

## 14. 推荐执行顺序

| 顺序 | 任务 | 验收 |
|---:|---|---|
| 1 | 重新整理 noisy / low-light / pseudo RAW baseline | `stage2_baseline_report.md` |
| 2 | 扩展 engineering summary 字段 | `stage2_engineering_summary_v2.csv` |
| 3 | 跑 pseudo RAW/RGGB 300-step baseline | metrics + checkpoint |
| 4 | 补 DnCNN L1/L2、patch、steps 消融总表 | ablation CSV |
| 5 | 导出 DnCNN ONNX | `.onnx` 文件 |
| 6 | 跑通 C++ OpenCV DNN 推理 | output image + latency |
| 7 | 整理 failure case taxonomy | taxonomy 报告 |
| 8 | 更新最终项目报告和简历表达 | final report v2 |

## 15. 社招表达边界

完成 P0-P4 后，可以使用更强表达：

```text
基于 PyTorch 构建 AI-ISP 图像恢复与部署验证 baseline，完成 SIDD paired RGB
去噪、DnCNN/UNet/NAFNet-lite 对比、noisy input baseline、PSNR/SSIM 与局部
IQ 指标评估、failure case 分析，并扩展 pseudo RAW/RGGB 输入和 ONNX/C++
推理验证链路。
```

仍然不要写：

```text
负责量产 ISP tuning
熟悉高通 / MTK / 海思平台调试
负责 AE/AWB/AF 量产联调
有 Imatest / iQ-Analyzer 实操经验
完成工业级 RAW ISP 全链路
```

## 16. 最终通过标准

阶段二升级完成后，至少能用项目数据回答这些问题：

1. noisy input baseline 是多少，模型提升了多少？
2. 为什么 DnCNN residual 当前比更复杂模型更稳？
3. PSNR/SSIM 和视觉观感冲突时怎么判断？
4. 模型在平坦区、纹理区、暗部、边缘分别有什么失败模式？
5. 参数量、checkpoint 大小、ONNX size、latency 是否支持部署讨论？
6. pseudo RAW/RGGB 和普通 RGB denoise 的区别是什么？
7. ONNX/C++ 推理结果和 PyTorch 是否基本一致？
8. 下一步应该优先扩大数据、换 loss、换模型，还是优化部署？

如果这些问题都能用表格、图像和脚本结果回答，阶段二就可以作为“社招 3 年可讲的 AI-ISP 工程 baseline 项目”。
