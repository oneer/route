# Week 8：Failure Case 和局部 Crop 分析

Week8 的目标是从“看整体指标”升级到“看失败细节”。

## 0. 输入输出合同与前后依赖

Week 4/7 先交付冻结 run 的 `vis/step_XXXX.png` 三联图，本周只做诊断，不重新训练模型。脚本按宽度三等分读取：

```text
输入：RGB uint8 PNG，HWC，[0,255]，水平排列 noisy/low | output | clean
处理：转 RGB -> 三等分 -> output/clean 转 float32 [0,1]
      -> 按局部 mean(|output-clean|) 选 top-error ROI 或 center ROI
输出：四列 crop sheet（input/output/clean/error×6）
      + CSV（run、图片、模式、x/y、roi_size、crop_mae）
```

三列必须同高、每列等宽且像素对齐；`crop_size` 不得大于单个 panel，超出时当前实现会缩到可用尺寸并在 CSV 记录实际大小。这里的 MAE 来自已保存的 8-bit 可视化，不是未量化 float tensor 的严格后端对齐指标；它适合选取 failure 候选，不能替代 Week 4 的正式 evaluation。Week 9 接收本周经人工确认并完成对照实验的 regression case，而不是直接接收“模型名 = 根因”的猜测。

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
python stage2_ai_isp/scripts/10_make_failure_case_crops.py --runs stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l1_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_patch64_2000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_unet_l1_1000 stage2_ai_isp/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 stage2_ai_isp/runs/low_light_sidd_tiny_unet_l1_300 --output-dir stage2_ai_isp/reports/figures/week8_failure_case_crops --crop-size 96 --zoom 3 --crop-mode top_error
```

输出文件：

```text
stage2_ai_isp/reports/figures/week8_failure_case_crops/failure_case_crop_sheet.png
stage2_ai_isp/reports/figures/week8_failure_case_crops/failure_case_crop_metrics.csv
```

扩展后的 crop MAE：

| Run | Vis image | Crop MAE |
|---|---|---:|
| DnCNN L2 2000 | `step_2000.png` | 0.030962 |
| DnCNN L1 2000 | `step_2000.png` | 0.029725 |
| DnCNN L2 patch64 2000 | `step_2000.png` | 0.031930 |
| UNet L1 1000 | `step_1000.png` | 0.036859 |
| NAFNet-lite L1 1000 | `step_1000.png` | 0.031238 |
| Low-light UNet L1 300 | `step_0300.png` | 0.037169 |

新版脚本从 error map 中寻找误差最大的 ROI，而不是固定裁中心。对于只有 64×64
可视化的 patch64 run，会使用完整 64×64 ROI，再统一缩放显示。它仍只定位“哪里错得多”，
不能自动证明“为什么错”。

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
最新表由 `figures/week8_failure_taxonomy/week8_failure_taxonomy.md` 自动生成。普通去噪
run 只按 top-error crop 相对中位数标记为 high/moderate/lower local error，不再根据
`dncnn/unet/nafnet` 文件名自动编造原因。低光任务单独标记，因为它确实改变曝光目标。

### 7.4 怎么用这张表

这张表不是为了给模型“打分”，而是为了指导下一步实验：

```text
自动脚本负责定位高误差 ROI 和严重程度；
学习者人工判断它属于 flat / edge / texture / dark / color / alignment 哪一类；
只有在人工标签和对照实验之后，才能提出数据、loss 或模型原因。
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
| 原因假设 | 自动脚本不生成；需人工标注后填写 |
| 下一步建议 | 已补充 |
| 能区分 denoise 和 low-light failure | 已补充 |

后续可扩展 top-k 非重叠 ROI；当前 top-error ROI 已解决固定中心 crop 可能完全错过
失败区域的问题。

### 7.6 人工 failure case 记录模板

自动 CSV 只负责“定位”和“量化”，每个代表案例还要人工补完：

| 字段 | 必填内容 |
|---|---|
| ROI | 图片名、坐标、crop size |
| 现象 | 残余亮噪/色噪、过平滑、伪纹理、色偏、边缘/棋盘格、高光、domain shift 或部署误差 |
| 数值 | input/output 的 ROI MAE、PSNR 或任务专属指标 |
| 原因假设 | 数据、退化、模型、loss、训练、配准或部署中的一类 |
| 验证实验 | 一次只改变一个变量，并写出预期结果 |
| 结论 | 实验支持、反驳，还是证据不足 |

没有人工语义标签和对照实验时，只能写“高误差 ROI”，不能把模型名直接翻译成失败原因。

## 9. Failure 分析关键词验收表

| 关键词 | 含义 | 正确用法 | 常见误判 |
|---|---|---|---|
| top-error crop | 按局部误差排序选出的 ROI | 快速找到模型最不一致区域 | 高误差不自动等于某种 artifact |
| failure taxonomy | 预先声明的失败类别和判据 | 统一记录、统计和决定下一实验 | 用模型名或主观印象代替判据 |
| symptom vs cause | 可见/可测现象与根因假设 | 先记录 symptom，再设计对照验证 cause | 一看到平滑就断言模型容量不足 |
| threshold | 触发诊断的量化门限 | 由 baseline、噪声和业务容忍度确定 | 为了凑案例事后移动阈值 |
| local metric | ROI 上的误差、纹理、颜色或 clipping | 补充全图平均值 | 自动 ROI 可能选中不相关内容 |
| regression test | 固定失败样本与判据 | 防止修一个问题又引入旧问题 | 只保存截图、不保存输入和参数 |

## 10. Week 8 面试五问

1. 为什么 top-error ROI 只能定位“哪里错”，不能直接解释“为什么错”？
2. 怎样把 over-smoothing、color shift、edge loss 和 residual noise 写成可执行判据？
3. 阈值应怎样从 baseline 和任务容忍度得到，而不是看完结果后决定？
4. 如何用单变量实验验证“模型容量不足”这一根因假设？
5. failure case 怎样转化为固定回归集和下一轮训练决策？

## 11. Failure 分析流程与边界

```text
固定 evaluation 输出
  -> 计算 per-pixel/local error
  -> 选择 top-error ROI
  -> 人工记录 symptom
  -> 提出 cause 假设
  -> 单变量对照实验
  -> 证据支持后才写入 taxonomy
  -> 固定为 regression case
```

自动 crop 和阈值只能定位候选失败区域；没有人工语义确认和对照实验时，报告边界仍是“高误差 ROI”，不能把它写成已证明的纹理、颜色或模型结构根因。

## 12. 教程闭环卡：从可见现象走到可证伪根因

Week 4/7 交付冻结评估输出，本周不训练新模型，而是把 error map 转为可操作的回归样本；
Week 9 再使用这些证据决定项目结论和下一实验。完整 RCA 链是：

```text
symptom（看见什么） -> metric/ROI（量化哪里） -> hypothesis（可能原因）
-> controlled experiment（只改一项） -> result（支持/反驳/不确定）
-> regression case（固定输入、阈值、预期）
```

例如“纹理区域 output MAE 高”只是现象；对比提高容量与更换 loss 两个独立实验后，才可能
区分欠拟合和目标函数偏向。阈值应在看最终结果前，依据 noisy baseline、历史波动和业务
容忍度确定。自动 top-error 容易偏向高对比边缘，需同时保留语义 ROI 或分层采样。

自动 top-error 的效率与语义 ROI 的覆盖之间存在权衡。本周自动化证据为
`verified_partial`：定位/数值已执行，语义根因仍需人工与对照验证。独立
验收是完成一张 failure card，包含坐标、现象、数值、两个竞争假设、单变量实验和回归门限。
