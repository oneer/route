# Week 4：Loss / Metric / 可视化评估体系

Week 4 的目标不是再多跑一个模型，而是建立图像恢复实验的评价语言。

Week 1 学会了 L1 / L2、PSNR / SSIM 和三联图的基本读法；Week 2/3 把它们放到真实 paired RGB 数据上。Week 4 要把这些零散判断整理成一套固定流程：

```text
loss 负责训练方向；
metric 负责数字评价；
visualization 负责发现数字看不见的问题；
failure analysis 负责解释下一步该怎么改。
```

## 1. 本周要解决的问题

你需要能回答：

1. 为什么训练用的 loss 和汇报用的 metric 不是一回事？
2. 为什么 PSNR 高，图像仍然可能不好看？
3. 为什么三联图必须和指标一起看？
4. 什么情况下该怀疑数据，而不是怀疑模型？
5. 怎么把一次实验写成可复查的分析结论？

本周通过标准不是“跑出最高分”，而是能写出这样的判断：

```text
这个模型 PSNR 提升，但三联图显示纹理被抹平。
这说明当前 loss 可能偏向像素平均，下一步应保留 L1/Charbonnier 或局部 crop 对照。
```

## 2. Loss 和 Metric 的区别

Loss 是训练时反向传播用的目标。

```text
output -> loss(output, clean) -> backward -> 更新参数
```

Metric 是验证或汇报时看的评价。

```text
output -> PSNR / SSIM / LPIPS / crop visual -> 分析结果
```

它们的关系是：

| 项目 | 用在哪里 | 是否参与 backward | 例子 |
|---|---|---|---|
| Loss | 训练 | 是 | L1、L2/MSE、Charbonnier |
| Metric | 验证/汇报 | 否 | PSNR、SSIM、LPIPS |
| Visualization | 人工观察 | 否 | noisy/output/clean、error map、crop |

不要把 metric 当成 loss，也不要以为 loss 低就一定视觉好。

## 3. 常见 Loss 怎么理解

### 3.1 L1

```text
L1 = mean(abs(output - clean))
```

直觉：

```text
误差有多大，就按多大惩罚。
```

特点：

- 对大误差没有 L2 那么敏感；
- 有时边缘和纹理更自然；
- PSNR 不一定最高；
- 适合作为真实图像恢复的视觉对照。

### 3.2 L2 / MSE

```text
L2 = MSE = mean((output - clean)^2)
```

直觉：

```text
大误差会被平方放大。
```

特点：

- 更贴近 PSNR；
- 常常更容易得到高 PSNR；
- 可能倾向平滑不确定区域；
- 真实数据上要特别检查 output 是否变糊。

### 3.3 Charbonnier

Charbonnier 可以理解成平滑版 L1：

```text
Charbonnier = mean(sqrt((output - clean)^2 + eps^2))
```

直觉：

```text
接近 L1，但在 0 附近更平滑，训练可能更稳定。
```

它常用于图像恢复论文，因为它比纯 L2 更不容易过度惩罚少数异常误差，又比 L1 在数学上更平滑。

本周如果暂时没有实现 Charbonnier，也至少要知道它解决的是：

```text
L1 的结构友好性 + 更平滑的优化。
```

## 4. 常见 Metric 怎么理解

### 4.1 PSNR

PSNR 来自 MSE：

```text
MSE 越小 -> PSNR 越高
```

它主要衡量像素误差。

适合看：

- output 是否整体接近 clean；
- 模型是否超过 noisy input baseline；
- L2/MSE 训练是否有效。

不适合单独判断：

- 纹理是否自然；
- 边缘是否过度平滑；
- 颜色是否主观舒服；
- 局部伪影是否明显。

### 4.2 SSIM

SSIM 更关注结构相似度。

它比 PSNR 更接近“结构有没有保住”，但仍然不是主观画质的完整答案。

常见情况：

| 现象 | 可能解释 |
|---|---|
| PSNR 高，SSIM 也高 | 大概率整体恢复不错 |
| PSNR 高，SSIM 低 | 像素误差小，但结构可能不好 |
| PSNR 低，SSIM 高 | 像素值不够准，但结构可能还在 |
| 两者都低 | 模型、数据或训练设置都要查 |

### 4.3 LPIPS

LPIPS 是感知指标，通常更接近深度特征空间里的视觉差异。

本阶段可以先了解，不急着作为主指标。原因是：

- 它引入额外模型；
- 小实验里 PSNR/SSIM/三联图已经足够建立判断；
- 面试时能解释它的定位即可。

## 5. 可视化应该看什么

最基础的是三联图：

```text
noisy | output | clean
```

观察顺序：

1. output 是否比 noisy 更干净；
2. output 是否接近 clean；
3. 边缘是否变糊；
4. 纹理是否被抹掉；
5. 颜色是否偏；
6. output 和 clean 是否错位；
7. 暗部和高光是否异常。

更进一步可以做局部 crop：

| Crop 类型 | 看什么 |
|---|---|
| 平坦区域 | 噪声是否去干净，有没有色块 |
| 边缘区域 | 边缘是否被抹糊 |
| 纹理区域 | 细节是否还在 |
| 暗部区域 | 噪声是否残留，是否偏色 |
| 高光区域 | 是否 clipping 或过度平滑 |

## 6. Error Map 怎么看

error map 是：

```text
abs(output - clean)
```

它能告诉你误差集中在哪里。

建议观察：

- 误差是否集中在边缘；
- 误差是否集中在暗部；
- 是否有大面积颜色偏差；
- 是否出现周期性纹理或块状伪影；
- 是否某个通道误差特别大。

如果误差集中在边缘，说明模型可能过度平滑。

如果误差集中在暗部，说明噪声建模或曝光域可能有问题。

如果误差大面积偏一个颜色，优先检查归一化、RGB/BGR、数据配对和颜色空间。

## 7. 推荐实验

本周不一定要训练新模型，可以复用 Week3 的输出做分析。

建议做三件事：

### 实验 A：同一模型的指标和三联图对照

选择一个 DnCNN 或 UNet run：

```text
metrics.csv
vis/step_*.png
```

记录：

| Step | Val PSNR | Val SSIM | 三联图观察 | 结论 |
|---:|---:|---:|---|---|
| 200 | 待填写 | 待填写 | 待填写 | 待填写 |
| 500 | 待填写 | 待填写 | 待填写 | 待填写 |
| 1000 | 待填写 | 待填写 | 待填写 | 待填写 |

要回答：

```text
指标变好时，图像是否真的变好？
```

### 实验 B：L1 / L2 视觉差异复盘

复用 Week3 的 L1/L2 对比：

| Loss | Best PSNR | Best SSIM | 平坦区 | 边缘 | 纹理 | 结论 |
|---|---:|---:|---|---|---|---|
| L1 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| L2 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |

要回答：

```text
L2 的 PSNR 优势是否带来了肉眼可见的画质优势？
```

### 实验 C：失败案例收集

挑 3 张失败最明显的三联图，写：

| 失败类型 | 现象 | 可能原因 | 下一步 |
|---|---|---|---|
| 过平滑 | 待填写 | MSE / patch / 模型容量 | 尝试 L1 / crop 观察 |
| 偏色 | 待填写 | 归一化 / 数据域 / 配对 | 查 RGB/BGR 和数据 |
| 错位 | 待填写 | pair 错误 / crop 错误 | 回到 Week2 |

## 8. 从 run 目录到评估报告的流程

拿到一个训练输出目录后，例如：

```text
runs/paired_rgb_sidd_tiny_dncnn_l2_2000/
```

按这个顺序做评估：

```text
1. 读 config：确认模型、loss、patch、steps、数据路径
2. 读 metrics.csv：找到 best PSNR / best SSIM / 最后一步
3. 读 vis/：观察 early / middle / best / last 的三联图
4. 选 2-3 张代表图：平坦区、纹理区、暗部或边缘
5. 写 failure case：至少记录一个变好点和一个问题点
6. 写下一步：继续训练、换 loss、扩数据、查数据或换模型
```

不要跳过第 1 步。很多实验结论看起来奇怪，最后发现只是 config 里 patch size、loss 或 output_dir 和自己以为的不一样。

### 8.1 Metrics 复盘模板

| 字段 | 记录 |
|---|---|
| run name | 待填写 |
| config | 待填写 |
| model | 待填写 |
| loss | 待填写 |
| patch size | 待填写 |
| train steps | 待填写 |
| input baseline PSNR / SSIM | 待填写 |
| best val PSNR / step | 待填写 |
| best val SSIM / step | 待填写 |
| last val PSNR / SSIM | 待填写 |
| 是否超过 baseline | 待填写 |
| 是否出现过拟合迹象 | 待填写 |

如果 best step 和 last step 差很多，要解释：

```text
模型后期是否过拟合？
学习率是否太大？
验证集是否太小导致波动？
```

### 8.2 可视化复盘模板

| 图像 | 观察点 | 结论 |
|---|---|---|
| `step_0200.png` | 早期 output 是否偏灰/偏色/过糊 | 待填写 |
| `step_0500.png` | 是否已经超过 noisy 的视觉质量 | 待填写 |
| `best_psnr 对应 step` | 指标最好时视觉是否最好 | 待填写 |
| `last step` | 后期是否变糟或过平滑 | 待填写 |

观察时要把判断写具体：

```text
不写：效果更好。
要写：平坦区噪声减少，但窗框边缘变软，暗部仍有彩色噪声。
```

### 8.3 Failure Case 写法

一个 failure case 至少包含四句话：

```text
现象：output 在纹理区域比 noisy 更平滑，但细节也被抹掉。
证据：三联图中 clean 的细线结构在 output 里消失，PSNR 虽然上升。
可能原因：MSE 倾向平均化不确定细节，当前 patch 或模型无法区分纹理和噪声。
下一步：保留 L1 / Charbonnier 对照，并裁剪纹理 ROI 单独观察。
```

这样写出来的报告才像算法复盘，而不是训练日志。

### 8.4 已实现的自动评估脚本

为了把 Week4 的评估流程落到代码，新增脚本：

```text
stage2_ai_isp/scripts/05_evaluate_runs.py
```

它会自动做这些事：

```text
读取多个 runs/<name>/metrics.csv
  -> 汇总 best PSNR / best SSIM / last metric
  -> 生成 metrics_summary.csv
  -> 生成 metrics_plot.png
  -> 生成 noisy/output/clean contact sheet
  -> 从三联图生成 output-clean error map
  -> 写出一份 markdown 结果报告
```

smoke 评估命令：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/paired_rgb_smoke_dncnn_l2 stage2_ai_isp/runs/paired_rgb_smoke_nafnet_lite_l1 --output-dir stage2_ai_isp/reports/figures/week4_smoke_eval --report-md stage2_ai_isp/reports/week4_smoke_eval_results.md --title "Week 4 Smoke Evaluation Results"
```

已生成：

```text
reports/week4_smoke_eval_results.md
reports/figures/week4_smoke_eval/metrics_summary.csv
reports/figures/week4_smoke_eval/metrics_plot.png
reports/figures/week4_smoke_eval/triplet_contact_sheet.png
reports/figures/week4_smoke_eval/error_maps/
```

![Week4 smoke metrics](figures/week4_smoke_eval/metrics_plot.png)

> 图说明：这张图画出不同 run 的 PSNR 和 SSIM 随 step 的变化。曲线越往上通常越好；如果 train loss 下降但这里不升，说明模型可能没有真正提升验证集效果。

![Week4 smoke triplets](figures/week4_smoke_eval/triplet_contact_sheet.png)

> 图说明：这张三联图把 noisy、output、clean 放在一起比较。观察时重点看 output 是否比 noisy 更干净，同时有没有把 clean 里的边缘、颜色和纹理抹掉。

本次 smoke input baseline：

```text
input PSNR = 22.1273
input SSIM = 0.28203
```

smoke 结果：

| Run | Best PSNR | Best SSIM | 结论 |
|---|---:|---:|---|
| DnCNN residual | 32.9687 | 0.89384 | 明显超过 baseline，是当前 smoke reference |
| NAFNet-lite | 25.2235 | 0.62806 | 已超过 baseline，证明模型和训练链路可用，但短训未追上 DnCNN |

这组结果不能说明“NAFNet-lite 不如 DnCNN”。更准确的结论是：

```text
NAFNet-lite 已经接入并能学习；
当前 80-step smoke run 只是功能验证；
正式比较需要相近 steps、参数量、loss、patch 和真实数据。
```

### 8.5 SIDD Tiny 真实数据评估结果

在真实 SIDD 小子集上，已经用同一个评估脚本汇总了 DnCNN、UNet、NAFNet-lite 三组 300-step 结果。

评估命令：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_300 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_300 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_300 --output-dir stage2_ai_isp/reports/figures/week4_sidd_tiny_eval --report-md stage2_ai_isp/reports/week4_sidd_tiny_eval_results.md --title "Week 4 SIDD Tiny Evaluation Results"
```

自动报告：

```text
reports/week4_sidd_tiny_eval_results.md
```

指标汇总：

| Run | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | Last PSNR | Last SSIM |
|---|---:|---:|---:|---:|---:|---:|
| DnCNN residual | 32.7717 | 250 | 0.77100 | 300 | 32.2857 | 0.77100 |
| UNet | 28.2856 | 300 | 0.85951 | 300 | 28.2856 | 0.85951 |
| NAFNet-lite | 26.8194 | 250 | 0.73509 | 300 | 26.0998 | 0.73509 |

![SIDD tiny metrics](figures/week4_sidd_tiny_eval/metrics_plot.png)

> 图说明：上图分开画了 PSNR 和 SSIM。DnCNN 的 PSNR 曲线最高，说明像素误差最小；UNet 的 SSIM 曲线最高，说明结构相似度更强；NAFNet-lite 曲线较低，说明当前轻量短训还不充分。

![SIDD tiny triplets](figures/week4_sidd_tiny_eval/triplet_contact_sheet.png)

> 图说明：这张三联图按 `noisy | output | clean` 比较不同模型和不同 step。读图时不要只看输出是否“干净”，还要看颜色是否偏、纹理是否残留、边缘是否被抹掉。

本轮最值得记住的分析：

```text
PSNR 高：不一定结构最好，但像素级误差小。
SSIM 高：结构相似度好，但可能仍有颜色或纹理残留。
三联图：用人眼检查指标有没有骗人。
error map：定位 output 和 clean 到底差在哪里。
```

所以 Week4 的真正能力是：当 DnCNN、UNet、NAFNet-lite 给出不同指标时，你能解释“为什么不是一个模型在所有指标上都赢”。

### 8.6 SIDD Tiny 标准版评估结果

为了得到更稳定的结论，又跑了一轮标准版训练：

```text
DnCNN residual: 2000 steps, L2/MSE
UNet: 1000 steps, L1
NAFNet-lite: 1000 steps, width=16, L1
```

自动报告：

```text
reports/week4_sidd_tiny_standard_eval_results.md
```

指标汇总：

| Run | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | Last PSNR | Last SSIM |
|---|---:|---:|---:|---:|---:|---:|
| DnCNN residual | 35.5356 | 1800 | 0.88367 | 1800 | 34.7538 | 0.87418 |
| UNet | 30.4453 | 1000 | 0.88003 | 1000 | 30.4453 | 0.88003 |
| NAFNet-lite | 33.3269 | 1000 | 0.86223 | 1000 | 33.3269 | 0.86223 |

![SIDD tiny standard metrics](figures/week4_sidd_tiny_standard_eval/metrics_plot.png)

> 图说明：标准版曲线比短训版更有参考价值。DnCNN 在 step 1800 达到最高点，step 2000 略回落；NAFNet-lite 持续上升到 step 1000，说明它可能还没完全收敛；UNet 的 SSIM 接近 DnCNN，但 PSNR 明显低。

![SIDD tiny standard triplets](figures/week4_sidd_tiny_standard_eval/triplet_contact_sheet.png)

> 图说明：标准版三联图显示，DnCNN 的 output 最接近 clean，NAFNet-lite 比短训版明显改善，UNet 仍保留较多纹理/颜色残留。这里要把数字和图一起看，不能只凭一个指标下结论。

标准版结论：

```text
DnCNN 是当前真实 SIDD Tiny 的最强 baseline；
NAFNet-lite 标准训练明显优于短训，值得继续加长训练；
UNet 的 SSIM 高，但视觉和 PSNR 说明它不一定是最佳去噪输出。
```

## 9. 本周输出

建议最终产出：

```text
reports/week4_loss_metric_visualization.md
```

包含：

- loss / metric 区别；
- PSNR / SSIM 的边界；
- L1 / L2 / Charbonnier 的取舍；
- 三联图和局部 crop 观察；
- 至少 3 个失败案例；
- 下一步实验建议。

## 10. 通过标准

学完 Week4 后，你应该能说清：

1. loss 和 metric 为什么不是一回事；
2. L1、L2/MSE、Charbonnier 的差异；
3. PSNR 为什么不能单独代表主观画质；
4. 三联图应该按什么顺序看；
5. error map 能帮助定位什么问题；
6. 遇到 output 过平滑、偏色、错位时先查什么；
7. 如何把一次实验写成“指标 + 视觉 + 下一步”的结论。

一句话总结：

```text
Week4 的目标是从“会跑模型”升级到“会评价模型”。
```

## 11. Week 4 升级：评估协议摘要和消融可视化

新版阶段二路线要求 Week 4 不只会解释 PSNR / SSIM / 三联图，还要把 Week 3 的模型对比结果纳入统一评估协议。也就是说，评估报告要能同时回答：

```text
模型是否超过 noisy input baseline？
PSNR 和 SSIM 的排名是否一致？
best PSNR 和 best SSIM 是否出现在同一步？
如果指标出现分歧，应该去看哪张三联图和 error map？
```

### 11.1 新增 ablation 评估

Week 3 已经补齐 DnCNN L1 和 patch64 两组实验，所以 Week 4 新增一组 ablation 评估，把它们和标准模型一起比较。

运行命令：

```bash
python stage2_ai_isp/scripts/05_evaluate_runs.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l1_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_1000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 --output-dir stage2_ai_isp/reports/figures/week4_sidd_tiny_ablation_eval --report-md stage2_ai_isp/reports/week4_sidd_tiny_ablation_eval_results.md --title "Week 4 SIDD Tiny Ablation Evaluation Results"
```

输出文件：

```text
stage2_ai_isp/reports/week4_sidd_tiny_ablation_eval_results.md
stage2_ai_isp/reports/figures/week4_sidd_tiny_ablation_eval/metrics_summary.csv
stage2_ai_isp/reports/figures/week4_sidd_tiny_ablation_eval/metrics_plot.png
stage2_ai_isp/reports/figures/week4_sidd_tiny_ablation_eval/triplet_contact_sheet.png
stage2_ai_isp/reports/figures/week4_sidd_tiny_ablation_eval/error_maps/
```

ablation 评估结果：

| Run | Best PSNR | Best PSNR Step | Best SSIM | Best SSIM Step | Last PSNR | Last SSIM |
|---|---:|---:|---:|---:|---:|---:|
| DnCNN L2 patch128 | 35.5356 | 1800 | 0.88367 | 1800 | 34.7538 | 0.87418 |
| DnCNN L1 patch128 | 35.6334 | 2000 | 0.88839 | 1800 | 35.6334 | 0.88669 |
| DnCNN L2 patch64 | 35.2304 | 1600 | 0.88455 | 1800 | 35.0176 | 0.88168 |
| UNet L1 | 30.4453 | 1000 | 0.88003 | 1000 | 30.4453 | 0.88003 |
| NAFNet-lite L1 | 33.3269 | 1000 | 0.86223 | 1000 | 33.3269 | 0.86223 |

![SIDD tiny ablation metrics](figures/week4_sidd_tiny_ablation_eval/metrics_plot.png)

> 图说明：这张图把 DnCNN L1/L2、patch64/128、UNet 和 NAFNet-lite 放在同一评估视角下。DnCNN L1 在当前 split 上取得最高 PSNR 和 SSIM；patch64 的 PSNR 略低但 SSIM 接近，适合作为快速实验配置。

![SIDD tiny ablation triplets](figures/week4_sidd_tiny_ablation_eval/triplet_contact_sheet.png)

> 图说明：这张三联图用于检查指标结论是否和视觉一致。特别是当 PSNR / SSIM 排名不同，或者 best PSNR / best SSIM 出现在不同 step 时，不能只看表格下结论。

### 11.2 新增评估协议摘要脚本

新增脚本：

```text
stage2_ai_isp/scripts/16_export_week4_evaluation_protocol.py
```

运行命令：

```bash
python stage2_ai_isp/scripts/16_export_week4_evaluation_protocol.py
```

输出文件：

```text
stage2_ai_isp/reports/figures/week4_evaluation_protocol/week4_evaluation_protocol.csv
stage2_ai_isp/reports/figures/week4_evaluation_protocol/week4_evaluation_protocol.md
```

它会读取已有的 `metrics_summary.csv`，自动补充：

| 字段 | 含义 |
|---|---|
| PSNR gain | 相比 noisy input baseline 的 PSNR 提升 |
| SSIM gain | 相比 noisy input baseline 的 SSIM 提升 |
| PSNR rank | 当前评估组内 PSNR 排名 |
| SSIM rank | 当前评估组内 SSIM 排名 |
| metric note | 是否存在 PSNR/SSIM 分歧，或 best step 不一致 |

本次自动摘要中的关键结论：

| Eval | Run | Best PSNR | Best SSIM | PSNR Rank | SSIM Rank | Note |
|---|---|---:|---:|---:|---:|---|
| standard | DnCNN L2 | 35.5356@1800 | 0.88367@1800 | 1 | 1 | PSNR/SSIM aligned |
| standard | UNet L1 | 30.4453@1000 | 0.88003@1000 | 3 | 2 | SSIM 接近，但 PSNR 明显低 |
| standard | NAFNet-lite L1 | 33.3269@1000 | 0.86223@1000 | 2 | 3 | 指标稳定，仍低于 DnCNN |
| ablation | DnCNN L1 | 35.6334@2000 | 0.88839@1800 | 1 | 1 | best PSNR 和 best SSIM 不同步 |
| ablation | DnCNN L2 patch64 | 35.2304@1600 | 0.88455@1800 | 3 | 2 | patch64 SSIM 接近，PSNR 略低 |

### 11.3 当前 Week 4 是否达标

按新版学习路线，Week 4 现在已经满足主要要求：

| 要求 | 当前状态 |
|---|---|
| 统一 PSNR / SSIM 评估 | 已有 `05_evaluate_runs.py` |
| triplet contact sheet | 已生成 smoke、short、standard、ablation 多组 |
| error map | 已自动生成 `error_maps/` |
| L1 / L2 可视化评估 | 已补入 DnCNN L1/L2 ablation |
| patch64 / patch128 可视化评估 | 已补入 patch ablation |
| PSNR / SSIM 分歧识别 | 已新增 `16_export_week4_evaluation_protocol.py` |
| gain vs input baseline | 已自动写入 evaluation protocol |

下一步进入 Week 5 时，不要只问“NAFNet-lite 分数为什么没最高”。更好的问题是：

```text
NAFNet-lite 的结构假设是什么？
当前数据量、训练步数、width 和 loss 是否足够支撑它？
它在 triplet 和 error map 中的失败区域，和 DnCNN 有什么不同？
```

这才是 Week 4 到 Week 5 的正确衔接。
