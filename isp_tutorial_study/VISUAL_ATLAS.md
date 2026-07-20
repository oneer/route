# ISP 视觉图谱：从现象回到原因

这些图片来自本仓库已经运行过的 Stage 1、Stage 2 和 Stage 4 实验。看图时保持同一缩放、同一 crop 和同一显示变换；不能用不同曝光或不同 tone 的图片直接判断算法优劣。

## 整体 pipeline

![AWB、CCM、Tone+Gamma 与 rawpy 参考对比](assets/traditional_pipeline_compare.png)

观察顺序：先看整体曝光和白平衡，再看肤色/中性色、饱和色、暗部和高光。与 rawpy 不一致不自动表示错误，因为目标风格和参数可能不同；需要结合色卡、灰卡和数值指标。

## Black Level Correction

![BLC 前后视觉对比](assets/blc_visual_compare.png)

重点观察暗部是否抬黑、截断或产生通道不一致。BLC 错误会被 AWB、CCM 和 tone 放大，因此应优先检查 RAW 直方图和每个 CFA 相位。

## Lens Shading Correction

![LSC 前后对比](assets/lsc_compare.png)

同时检查中心、边缘和四角。四角亮度变均匀不代表完成：gain 也会放大噪声，过强校正会造成四角过亮或色彩不连续。

## Defect Pixel Correction

![DPC 局部修复](assets/dpc_repair_crop.png)

坏点验收必须看局部 crop、mask 和误检/漏检。纹理、星点和高光边缘容易被错误地当作坏点。

## Demosaic

![多种去马赛克基线](assets/demosaic_compare.png)

重点看斜线、细纹理和高反差边缘；检查 zipper、false color、moiré 和细节损失。不同实现的颜色差异还可能来自 AWB/CCM，不应全部归因于 demosaic。

## AWB 与 CCM

![AWB 对比](assets/awb_compare.png)

![CCM Delta E](assets/ccm_deltae.png)

AWB 先看中性区域是否中性；CCM 再看各色块是否落到目标。白色正确但肤色/饱和色错误，优先检查 CCM、处理域和标定光源。

## Tone curve

![Gamma 与 tone 曲线](assets/tone_curves.png)

曲线必须标出输入域、输出域、black/white level 和位深。只看“更亮”会掩盖暗部量化、高光截断和局部对比问题。

## AI-ISP failure gallery

![AI 去噪失败案例](assets/ai_failure_gallery.png)

每行包含 noisy/low、模型输出、clean reference 和放大误差。重点检查残余色噪、过平滑、结构偏移和不同模型的共同失败区域。

![AI 模型指标对比](assets/ai_metrics_plot.png)

指标只负责排序某一测试协议下的平均表现；最终判断仍需结合相同 crop、失败案例、延迟、内存和数据分布。

## 部署对齐误差

![ONNX Runtime 与 PyTorch 误差图](assets/onnx_error_map.png)

后端误差图用于检查转换和数值对齐。需要同时记录最大误差、平均误差、误差位置以及是否影响最终视觉质量。

## 读图检查单

1. 输入、曝光、white balance、tone 是否一致？
2. 是整图还是固定坐标 crop？缩放倍率是否一致？
3. 差异来自当前模块，还是前后模块/显示变换？
4. 数值指标和主观观察是否指向同一结论？
5. 有没有保留失败案例，而不仅是最好样例？

