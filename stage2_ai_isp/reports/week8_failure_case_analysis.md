# Week 8：Failure Case 和局部 Crop 分析

Week8 的目标是从“看整体指标”升级到“看失败细节”。

前面已经有：

```text
PSNR / SSIM
三联图
error map
```

但真实图像恢复里，整体指标可能掩盖局部问题。Week8 通过局部 crop 放大图观察模型到底错在哪里。

## 1. 本周实现了什么

新增脚本：

```text
scripts/10_make_failure_case_crops.py
```

它读取训练输出：

```text
runs/<name>/vis/step_XXXX.png
```

从三联图里拆出：

```text
noisy/low | output | clean
```

然后裁剪中心区域，生成：

```text
noisy crop
output crop
clean crop
error x6 crop
```

## 2. 操作命令

```bash
python stage2_ai_isp/scripts/10_make_failure_case_crops.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_1000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 stage2_ai_isp/runs/low_light_sidd_tiny_unet_l1_300 --output-dir stage2_ai_isp/reports/figures/week8_failure_case_crops --crop-size 96 --zoom 3
```

## 3. 结果图

![Failure case crops](figures/week8_failure_case_crops/failure_case_crop_sheet.png)

> 图说明：每一行对应一个 run，从左到右是 noisy/low、output、clean、error x6。局部放大后可以看到整体指标看不出的细节：UNet 的局部纹理残留更明显；DnCNN 和 NAFNet-lite 更接近 clean；低光增强虽然大幅变亮，但局部仍有平滑和纹理残留。

局部 crop MAE：

| Run | Crop MAE |
|---|---:|
| DnCNN standard | 0.029846 |
| UNet standard | 0.036193 |
| NAFNet-lite standard | 0.030536 |
| Low-light UNet | 0.036040 |

这张表和图一起说明：

```text
局部 crop 上，DnCNN 和 NAFNet-lite 的误差更接近；
UNet 的整体 SSIM 很高，但局部 crop MAE 更大；
低光增强任务更难，因为它同时要增亮和去噪。
```

## 4. 为什么要做 failure case

只看平均 PSNR / SSIM 有三个风险：

1. 局部坏得很明显，但被全图平均稀释；
2. 结构指标高，但颜色或纹理不自然；
3. 模型在某类区域失败，比如暗部、边缘、平坦色块。

Failure case 分析的意义是：

```text
找到模型还不会处理的区域，
再决定下一步是改数据、改 loss、改模型，还是改训练策略。
```

## 5. 面试题和参考回答

**Q1：为什么 PSNR 高还要看 failure case？**

PSNR 是全图平均像素误差。局部区域即使有明显伪影，也可能被全图平均掩盖。failure case 可以暴露模型在暗部、边缘、纹理或颜色区域的具体问题。

**Q2：error map 怎么看？**

error map 是 `abs(output - clean)` 的可视化。越亮表示误差越大。它不能告诉你错误原因，但能告诉你错误集中在哪里。

**Q3：UNet SSIM 高但 crop MAE 大，怎么解释？**

SSIM 更关注结构相似度，局部纹理和颜色偏差可能仍然较大。crop MAE 是局部像素误差，两者关注点不同，所以可能出现 SSIM 高但局部误差大的情况。

**Q4：看到 failure case 后下一步怎么做？**

先分类错误：如果是暗部噪声残留，可能需要更多低光样本或更强 denoise；如果是过平滑，可能需要调整 loss；如果是颜色偏移，可能需要检查数据和颜色空间；如果是边缘伪影，可能需要更强结构模型或局部 crop loss。

## 6. 本周通过标准

学完 Week8 后，你应该能：

1. 从三联图里找出局部失败区域；
2. 解释 error map 亮区代表什么；
3. 说明 PSNR、SSIM 和局部 crop MAE 的区别；
4. 根据 failure case 给出下一步实验建议。

## 7. Week 8 升级：Failure Taxonomy 和下一步决策

新版阶段二路线要求 Week 8 不只生成 crop 图，还要把失败现象整理成可行动的诊断表：

```text
failure crop -> failure type -> evidence -> likely reason -> next step
```

这一步的目标不是“证明原因一定正确”，而是避免看到坏图后只说“效果不好”。更好的做法是先分类，再给出下一步实验。

### 7.1 扩展后的 crop 分析

本次重新生成了包含 6 个 run 的 failure crop sheet：

```bash
python stage2_ai_isp/scripts/10_make_failure_case_crops.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l1_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_1000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 stage2_ai_isp/runs/low_light_sidd_tiny_unet_l1_300 --output-dir stage2_ai_isp/reports/figures/week8_failure_case_crops --crop-size 96 --zoom 3
```

输出文件：

```text
stage2_ai_isp/reports/figures/week8_failure_case_crops/failure_case_crop_sheet.png
stage2_ai_isp/reports/figures/week8_failure_case_crops/failure_case_crop_metrics.csv
```

扩展后的 crop MAE：

| Run | Vis image | Crop MAE |
|---|---|---:|
| DnCNN L2 2000 | `step_2000.png` | 0.029846 |
| DnCNN L1 2000 | `step_2000.png` | 0.028497 |
| DnCNN L2 patch64 2000 | `step_2000.png` | 0.014191 |
| UNet L1 1000 | `step_1000.png` | 0.036193 |
| NAFNet-lite L1 1000 | `step_1000.png` | 0.030536 |
| Low-light UNet L1 300 | `step_0300.png` | 0.036040 |

注意：这个 crop 是中心 crop，不代表全图所有局部区域。它的作用是提供一个固定、可复查的局部观察点，而不是替代全图 PSNR / SSIM。

### 7.2 新增 failure taxonomy 脚本

新增脚本：

```text
stage2_ai_isp/scripts/19_export_week8_failure_taxonomy.py
```

运行命令：

```bash
python stage2_ai_isp/scripts/19_export_week8_failure_taxonomy.py
```

输出文件：

```text
stage2_ai_isp/reports/figures/week8_failure_taxonomy/week8_failure_taxonomy.csv
stage2_ai_isp/reports/figures/week8_failure_taxonomy/week8_failure_taxonomy.md
```

### 7.3 Failure taxonomy 表

| Run | Crop MAE | Failure Type | Evidence | Likely Reason | Next Step |
|---|---:|---|---|---|---|
| DnCNN L2 2000 | 0.029846 | baseline smoothing / residual local error | DnCNN L2 全局指标强，局部仍有非零误差 | MSE 更贴近 PSNR，但可能平滑不确定纹理 | 和 DnCNN L1、error map、纹理 crop 一起看 |
| DnCNN L1 2000 | 0.028497 | strong baseline / residual local error | 当前全局指标最佳，但局部仍未完全贴近 clean | residual denoise 适合任务，但 tiny 数据和简单 loss 仍有限 | 作为当前 baseline，后续再考虑 Charbonnier 或扩数据 |
| DnCNN L2 patch64 | 0.014191 | context-limited denoise | 中心 crop MAE 低，但全图 PSNR 低于 patch128 | 小 patch 上下文较少，可能影响全图像素级恢复 | patch64 用于快速 ablation，正式结果保留 patch128 |
| UNet L1 1000 | 0.036193 | local texture or color residual | UNet SSIM 高，但 crop MAE 较高 | encoder-decoder 保结构，但 direct output 可能留下局部颜色/纹理误差 | 检查纹理/边缘 crop，考虑 residual-output UNet |
| NAFNet-lite L1 1000 | 0.030536 | under-trained modern block / residual noise | 已超过 input baseline，但仍落后 DnCNN | 简化 NAFNet-lite 数据少、步数少、缺少完整官方训练策略 | 延长到 2000 steps 或测试 Charbonnier |
| Low-light UNet L1 300 | 0.036040 | dark-region enhancement / over-smoothing | 低光任务局部误差高，且任务改变曝光 | 模型同时做增亮、去噪、颜色保持，任务比普通 denoise 更难 | 补 exposure/noise/color 指标，单独看暗部 ROI |

### 7.4 怎么用这张表

这张表不是为了给模型“打分”，而是为了指导下一步实验：

```text
如果 DnCNN 已经很强，就不要盲目换大模型；
如果 UNet 局部误差高，就要看 direct output 和颜色/纹理残留；
如果 NAFNet-lite 落后，要先排除训练不足；
如果低光增强失败，要先分开看亮度、噪声和颜色。
```

Week 8 的最终判断应该长这样：

```text
当前最稳的普通去噪 baseline 是 DnCNN L1/L2；
NAFNet-lite 仍值得继续，但需要更长训练或更合适 loss；
UNet 的结构相似度不差，但局部 crop 说明它仍有像素/颜色残留；
low-light enhancement 不能直接和普通 denoise 比，需要单独建立暗部和曝光指标。
```

### 7.5 当前 Week 8 是否达标

按新版学习路线，Week 8 现在已经满足主要要求：

| 要求 | 当前状态 |
|---|---|
| failure crop sheet | 已生成 |
| crop-level MAE | 已生成 |
| error x6 crop | 已生成 |
| failure taxonomy | 已补充 |
| 原因假设 | 已补充 |
| 下一步建议 | 已补充 |
| 能区分 denoise 和 low-light failure | 已补充 |

后续如果继续增强 Week 8，最值得补的是“多位置自动 crop mining”：从 error map 里自动找误差最大的 ROI，而不是只裁中心区域。但这可以放到后续项目增强，不阻塞进入 Week 9 总结。
