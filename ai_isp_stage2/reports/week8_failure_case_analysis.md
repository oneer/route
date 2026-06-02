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
python ai_isp_stage2/scripts/10_make_failure_case_crops.py --runs ai_isp_stage2/runs/paired_rgb_sidd_tiny_dncnn_l2_2000 ai_isp_stage2/runs/paired_rgb_sidd_tiny_unet_l1_1000 ai_isp_stage2/runs/paired_rgb_sidd_tiny_nafnet_lite_l1_1000 ai_isp_stage2/runs/low_light_sidd_tiny_unet_l1_300 --output-dir ai_isp_stage2/reports/figures/week8_failure_case_crops --crop-size 96 --zoom 3
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
