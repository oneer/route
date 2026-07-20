# Week 6 阶段毕业实验：综合验收与故障诊断

## 本周学习闭环

| 项目 | 要求 |
|---|---|
| 目标 | 把模块对比、局部诊断、证据边界和独立实现组织成一次阶段毕业验收 |
| 前置 | Week 1–5 的预测、练习和单元测试已完成；不是第一次阅读现成答案 |
| 运行前预测 | 为 DPC、Demosaic、AWB、CCM、Tone 各写一个最可能失败的场景和检查方法 |
| 最小实验 | 先对 T01/T08/T13 运行补强实验，再在新目录完成独立毕业任务 |
| 验收 | 35 项仓库测试通过；独立实现至少 6 项测试；有参数实验、失败案例和 Git 迭代 |

```powershell
python -m unittest discover -s tests -v
python scripts/16_close_mastery_gaps.py `
  data/raw/T01_a0006-IMG_2787.dng `
  data/raw/T08_a0022-IMG_2380.dng `
  data/raw/T13_a0035-dgw_048.dng `
  --out-dir outputs/tutorial/week6 `
  --report outputs/tutorial/week6/mastery_gap_closure_report.md
```

最后完成[独立毕业任务](../../exercises/final_project.md)。本报告是参考验收结果，不替代学习者自己的实现和失败记录。

本报告把 `module_mastery_matrix.md` 中标记为“缺实验”的能力点集中补齐。它不替代 Week1-5 的主报告，而是作为补充验证层：每个缺口都对应一个可运行实验、一个结果表或一组可视化。

为了让 DPC、多个 demosaic、DeltaE 和 ROI 指标能在 14 张样张上快速复现，本报告默认使用保持 Bayer 对齐的中心 RAW crop 进行实验。它用于学习和对比模块行为，不替代全分辨率产品评价。

## 1. 本周补齐了什么

| 缺口 | 本次补法 | 输出 |
|---|---|---|
| DPC 静态 defect map | 从动态候选中抽取固定坐标，构造静态 defect map 修复 | dynamic/static 数量和 mask 图 |
| LSC flat-field / mesh LUT | 构造合成 flat-field，按 tile 估计 mesh gain | true gain / estimated mesh / error 图 |
| Demosaic OpenCV / 方向对比 | 对比本项目 bilinear、OpenCV bilinear、OpenCV edge-aware | 指标表和对比图 |
| AWB white patch / ROI | 对比 Gray World、White Patch、Gray ROI | gain 表、指标和对比图 |
| CCM Lab / DeltaE | 比较 no-CCM 与 CCM 到 rawpy reference 的 DeltaE | DeltaE 表和差异放大图 |
| Gamma/Tone S-curve | 对比 pow gamma、sRGB OETF、S-curve LUT | 曲线图和指标表 |
| IQA ROI + 主观标签 | 自动选 center/dark/highlight/texture/corner ROI | ROI 指标和标签表 |

## 2. DPC：动态检测 vs 静态 defect map

| 样张 | 动态候选数 | 静态 defect map 点数 | 说明 |
|---|---:|---:|---|
| T01 | 100 | 58 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T02 | 0 | 0 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T03 | 0 | 0 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T04 | 35 | 35 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T05 | 2 | 2 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T06 | 0 | 0 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T07 | 16 | 16 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T08 | 7907 | 100 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T09 | 0 | 0 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T10 | 490 | 100 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T11 | 0 | 0 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T12 | 140 | 55 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T13 | 1018 | 83 | 静态表只修固定坐标，动态检测依赖当前图像统计 |
| T14 | 13057 | 100 | 静态表只修固定坐标，动态检测依赖当前图像统计 |

动态 DPC 适合发现当前帧中的异常点，但会受 ISO、温度、纹理和高光边缘影响；静态 defect map 来自工厂标定，稳定但只能修已知坐标。产品里常把两者结合：先用静态表修已知坏点，再用动态检测兜底。

## 3. LSC：合成 flat-field 与 mesh gain

| 样张 | mesh gain MAE ↓ | 说明 |
|---|---:|---|
| T01 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T02 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T03 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T04 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T05 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T06 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T07 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T08 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T09 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T10 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T11 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T12 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T13 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |
| T14 | 0.0525 | tile 越小越贴近真实 gain，但越容易带来块状边界和噪声 |

这里用合成 flat-field 验证 LSC 标定流程：先构造一张带暗角的均匀场，再按 tile 估计 gain。它不等于真实镜头标定，但补上了“flat-field / mesh LUT 是怎么来的”这块理解。

## 4. Demosaic：Bilinear / OpenCV / Edge-aware 对比

| 变体 | 平均 PSNR ↑ | 平均 SSIM ↑ | 平均 Mean Abs Diff ↓ |
|---|---:|---:|---:|
| ours_bilinear | 16.6710 | 0.7585 | 0.1542 |
| opencv_bilinear | 16.6836 | 0.7586 | 0.1539 |
| opencv_edge_aware | 16.6984 | 0.7565 | 0.1537 |

OpenCV edge-aware 是一个独立的边缘感知 baseline，不是 AHD，也不能替代 AHD/Malvar 的实现与验证。这里的对比只说明：加入边缘方向信息后，结果可能与纯 bilinear 不同；是否更好仍需结合统一 ROI、伪影和指标判断。

## 5. AWB：Gray World / White Patch / Gray ROI

| 变体 | 平均 PSNR ↑ | 平均 SSIM ↑ | 平均 Mean Abs Diff ↓ |
|---|---:|---:|---:|
| gray_world | 15.4041 | 0.7373 | 0.1838 |
| white_patch | 16.0154 | 0.7397 | 0.1815 |
| gray_roi | 16.3721 | 0.7474 | 0.1709 |

| 样张 | Gray World gain | White Patch gain | Gray ROI gain | ROI 覆盖率 |
|---|---|---|---|---:|
| T01 | [1.9746999740600586, 1.0, 1.657099962234497] | [2.094399929046631, 1.0, 1.4265999794006348] | [1.9854999780654907, 1.0, 1.654099941253662] | 0.7000 |
| T02 | [1.0817999839782715, 1.0, 1.7661000490188599] | [1.2314000129699707, 1.0, 1.615399956703186] | [1.1339000463485718, 1.0, 1.2617000341415405] | 0.0032 |
| T03 | [2.0978000164031982, 1.0, 1.322700023651123] | [2.1184000968933105, 1.0, 1.3698999881744385] | [2.0880000591278076, 1.0, 1.319000005722046] | 0.7000 |
| T04 | [2.011899948120117, 1.0, 1.4359999895095825] | [2.2265000343322754, 1.0, 1.2446000576019287] | [1.1289000511169434, 1.0, 1.1296000480651855] | 0.0006 |
| T05 | [2.461400032043457, 1.0, 1.0503000020980835] | [2.5274999141693115, 1.0, 1.03410005569458] | [2.468899965286255, 1.0, 1.0420000553131104] | 0.7000 |
| T06 | [1.6267000436782837, 1.0, 1.614300012588501] | [1.5484000444412231, 1.0, 1.725600004196167] | [1.6332000494003296, 1.0, 1.6140999794006348] | 0.7000 |
| T07 | [2.086899995803833, 1.0, 1.9365999698638916] | [1.9874000549316406, 1.0, 2.0151000022888184] | [2.0929999351501465, 1.0, 1.924299955368042] | 0.7000 |
| T08 | [2.978800058364868, 1.0, 1.4371999502182007] | [2.1445999145507812, 1.0, 1.6689000129699707] | [1.1456999778747559, 1.0, 1.104099988937378] | 0.0001 |
| T09 | [1.4701999425888062, 1.0, 2.0941998958587646] | [1.3997000455856323, 1.0, 2.0915000438690186] | [1.4780000448226929, 1.0, 2.069999933242798] | 0.7000 |
| T10 | [0.7150999903678894, 1.0, 6.146100044250488] | [0.9404000043869019, 1.0, 1.5082999467849731] | [0.9531999826431274, 1.0, 1.0017000436782837] | 0.0001 |
| T11 | [1.2131999731063843, 1.0, 2.3106000423431396] | [1.5994999408721924, 1.0, 1.7833000421524048] | [1.1783000230789185, 1.0, 2.3915998935699463] | 0.7000 |
| T12 | [1.6651999950408936, 1.0, 4.1041998863220215] | [1.559399962425232, 1.0, 3.6875998973846436] | [1.6366000175476074, 1.0, 4.118299961090088] | 0.7000 |
| T13 | [1.50409996509552, 1.0, 1.2785999774932861] | [2.212899923324585, 1.0, 0.9699000120162964] | [1.0865999460220337, 1.0, 1.1577999591827393] | 0.1620 |
| T14 | [1.3832999467849731, 1.0, 1.6950000524520874] | [1.0, 1.0, 1.0] | [1.1167999505996704, 1.0, 1.1345000267028809] | 0.0030 |

White Patch 更相信最亮区域，容易被彩色高光或饱和区域带偏；Gray ROI 会先找较中性的候选像素，更接近工程 AWB 的灰点筛选思路。

## 6. CCM：Lab / DeltaE 与差异放大

| 样张 | no CCM DeltaE ↓ | CCM DeltaE ↓ | DeltaE 改善 | 说明 |
|---|---:|---:|---:|---|
| T01 | 12.0056 | 12.0668 | -0.0612 | 正数表示 CCM 更接近 rawpy reference |
| T02 | 22.3797 | 22.7232 | -0.3434 | 正数表示 CCM 更接近 rawpy reference |
| T03 | 21.2793 | 20.4510 | 0.8283 | 正数表示 CCM 更接近 rawpy reference |
| T04 | 13.7499 | 14.2427 | -0.4928 | 正数表示 CCM 更接近 rawpy reference |
| T05 | 7.0862 | 6.9093 | 0.1768 | 正数表示 CCM 更接近 rawpy reference |
| T06 | 11.0779 | 11.1558 | -0.0779 | 正数表示 CCM 更接近 rawpy reference |
| T07 | 26.6697 | 26.1729 | 0.4968 | 正数表示 CCM 更接近 rawpy reference |
| T08 | 19.9615 | 22.1306 | -2.1691 | 正数表示 CCM 更接近 rawpy reference |
| T09 | 19.0539 | 18.6787 | 0.3752 | 正数表示 CCM 更接近 rawpy reference |
| T10 | 19.2873 | 19.7796 | -0.4923 | 正数表示 CCM 更接近 rawpy reference |
| T11 | 12.8963 | 13.3163 | -0.4200 | 正数表示 CCM 更接近 rawpy reference |
| T12 | 20.1182 | 20.3513 | -0.2331 | 正数表示 CCM 更接近 rawpy reference |
| T13 | 23.6789 | 22.5894 | 1.0895 | 正数表示 CCM 更接近 rawpy reference |
| T14 | 10.5576 | 10.9244 | -0.3668 | 正数表示 CCM 更接近 rawpy reference |

DeltaE 仍然是相对 rawpy reference 的近似评价，不是色卡标准答案。但它比单纯看整图更适合回答“CCM 到底有没有改变颜色关系”。

## 7. Gamma / Tone：pow gamma、sRGB OETF、S-curve LUT

![Gamma/Tone curves](../figures/week6_gamma_tone_curves.png)

| 变体 | 平均 PSNR ↑ | 平均 SSIM ↑ | 平均 Mean Abs Diff ↓ |
|---|---:|---:|---:|
| reinhard_pow_gamma | 16.2595 | 0.7432 | 0.1463 |
| gamma_only | 15.7146 | 0.7210 | 0.1769 |
| srgb_oetf | 15.7719 | 0.7216 | 0.1769 |
| s_curve_lut | 15.4820 | 0.6687 | 0.1604 |

这补上了之前缺的 sRGB OETF 和 S-curve。pow gamma 是最小教学版，sRGB OETF 更接近标准显示编码，S-curve LUT 更接近产品 tuning 的曲线工作流。

## 8. ROI IQA 与主观标签

| 样张 | ROI | PSNR ↑ | SSIM ↑ | Mean Abs Diff ↓ | DeltaE ↓ | 主观标签 |
|---|---|---:|---:|---:|---:|---|
| T01 | center | 22.5951 | 0.8796 | 0.0594 | 12.2196 | color_shift |
| T01 | dark | 22.8925 | 0.7975 | 0.0613 | 9.8516 | acceptable |
| T01 | highlight | 15.3608 | 0.7420 | 0.1561 | 13.7868 | structure_gap, luminance_gap, color_shift |
| T01 | texture | 18.3603 | 0.8013 | 0.1031 | 12.8732 | luminance_gap, color_shift |
| T01 | corner | 23.1362 | 0.8820 | 0.0578 | 12.0569 | color_shift |
| T02 | center | 14.2443 | 0.7158 | 0.1773 | 23.2592 | structure_gap, luminance_gap, color_shift |
| T02 | dark | 13.9862 | 0.5371 | 0.1908 | 21.3829 | structure_gap, luminance_gap, color_shift |
| T02 | highlight | 14.9439 | 0.8074 | 0.1487 | 20.9879 | luminance_gap, color_shift |
| T02 | texture | 14.2784 | 0.7106 | 0.1768 | 20.6853 | structure_gap, luminance_gap, color_shift |
| T02 | corner | 13.3818 | 0.6298 | 0.2014 | 23.4287 | structure_gap, luminance_gap, color_shift |
| T03 | center | 13.8223 | 0.9000 | 0.2026 | 21.3218 | luminance_gap, color_shift |
| T03 | dark | 12.8999 | 0.8291 | 0.2246 | 21.8226 | luminance_gap, color_shift |
| T03 | highlight | 14.5980 | 0.9298 | 0.1853 | 15.8943 | luminance_gap, color_shift |
| T03 | texture | 12.8999 | 0.8291 | 0.2246 | 21.8226 | luminance_gap, color_shift |
| T03 | corner | 12.7819 | 0.8837 | 0.2288 | 22.4390 | luminance_gap, color_shift |
| T04 | center | 17.1100 | 0.8034 | 0.1360 | 13.9776 | luminance_gap, color_shift |
| T04 | dark | 16.2514 | 0.6333 | 0.1523 | 13.2390 | structure_gap, luminance_gap, color_shift |
| T04 | highlight | 18.2852 | 0.7788 | 0.1094 | 13.1464 | luminance_gap, color_shift |
| T04 | texture | 16.5900 | 0.6775 | 0.1399 | 14.5884 | structure_gap, luminance_gap, color_shift |
| T04 | corner | 16.2514 | 0.6333 | 0.1523 | 13.2390 | structure_gap, luminance_gap, color_shift |
| T05 | center | 16.9673 | 0.8316 | 0.1141 | 9.6920 | luminance_gap |
| T05 | dark | 24.6906 | 0.8009 | 0.0557 | 6.1866 | acceptable |
| T05 | highlight | 12.3292 | 0.8634 | 0.2248 | 14.1442 | luminance_gap, color_shift |
| T05 | texture | 16.3648 | 0.8125 | 0.1144 | 9.8152 | luminance_gap |
| T05 | corner | 25.6991 | 0.8478 | 0.0486 | 5.4639 | acceptable |
| T06 | center | 19.8778 | 0.7478 | 0.0733 | 12.2888 | structure_gap, color_shift |
| T06 | dark | 21.8887 | 0.8264 | 0.0709 | 9.5735 | acceptable |
| T06 | highlight | 16.7495 | 0.7742 | 0.1217 | 14.6614 | luminance_gap, color_shift |
| T06 | texture | 19.4684 | 0.6999 | 0.0813 | 12.9797 | structure_gap, color_shift |
| T06 | corner | 21.0051 | 0.8262 | 0.0726 | 10.0137 | acceptable |
| T07 | center | 11.6092 | 0.5608 | 0.2581 | 24.5495 | structure_gap, luminance_gap, color_shift |
| T07 | dark | 12.7641 | 0.4579 | 0.2271 | 19.9851 | structure_gap, luminance_gap, color_shift |
| T07 | highlight | 10.9319 | 0.7044 | 0.2786 | 27.6849 | structure_gap, luminance_gap, color_shift |
| T07 | texture | 11.1678 | 0.4885 | 0.2671 | 25.1922 | structure_gap, luminance_gap, color_shift |
| T07 | corner | 10.6113 | 0.7182 | 0.2910 | 29.5938 | structure_gap, luminance_gap, color_shift |
| T08 | center | 13.6032 | 0.6402 | 0.1739 | 21.2890 | structure_gap, luminance_gap, color_shift |
| T08 | dark | 15.5323 | 0.6619 | 0.1429 | 19.4140 | structure_gap, luminance_gap, color_shift |
| T08 | highlight | 11.5801 | 0.5439 | 0.2274 | 25.2502 | structure_gap, luminance_gap, color_shift |
| T08 | texture | 12.2289 | 0.5319 | 0.2046 | 23.9594 | structure_gap, luminance_gap, color_shift |
| T08 | corner | 14.1937 | 0.6604 | 0.1740 | 21.5594 | structure_gap, luminance_gap, color_shift |
| T09 | center | 14.5553 | 0.6219 | 0.1849 | 17.7533 | structure_gap, luminance_gap, color_shift |
| T09 | dark | 14.7018 | 0.5625 | 0.1819 | 17.1421 | structure_gap, luminance_gap, color_shift |
| T09 | highlight | 15.3213 | 0.7947 | 0.1591 | 16.4991 | luminance_gap, color_shift |
| T09 | texture | 14.2244 | 0.6935 | 0.1903 | 18.7107 | structure_gap, luminance_gap, color_shift |
| T09 | corner | 13.2972 | 0.6565 | 0.2140 | 20.5248 | structure_gap, luminance_gap, color_shift |
| T10 | center | 18.3761 | 0.6185 | 0.0931 | 17.7418 | structure_gap, color_shift |
| T10 | dark | 20.5110 | 0.6327 | 0.0790 | 15.9314 | structure_gap, color_shift |
| T10 | highlight | 13.9448 | 0.7490 | 0.1656 | 25.5168 | structure_gap, luminance_gap, color_shift |
| T10 | texture | 14.5252 | 0.6428 | 0.1492 | 21.8587 | structure_gap, luminance_gap, color_shift |
| T10 | corner | 18.6053 | 0.6641 | 0.0991 | 18.4105 | structure_gap, color_shift |
| T11 | center | 17.2045 | 0.8563 | 0.1087 | 17.6127 | luminance_gap, color_shift |
| T11 | dark | 22.3750 | 0.3892 | 0.0738 | 6.7395 | structure_gap |
| T11 | highlight | 16.7913 | 0.8226 | 0.1146 | 18.9199 | luminance_gap, color_shift |
| T11 | texture | 18.6193 | 0.8470 | 0.0939 | 13.9375 | color_shift |
| T11 | corner | 20.1916 | 0.9223 | 0.0792 | 13.5242 | color_shift |
| T12 | center | 17.5414 | 0.6004 | 0.0977 | 18.4481 | structure_gap, color_shift |
| T12 | dark | 19.5916 | 0.5847 | 0.0870 | 13.6349 | structure_gap, color_shift |
| T12 | highlight | 13.2553 | 0.5625 | 0.1851 | 31.5719 | structure_gap, luminance_gap, color_shift |
| T12 | texture | 13.5506 | 0.5024 | 0.1671 | 22.1992 | structure_gap, luminance_gap, color_shift |
| T12 | corner | 13.6559 | 0.5677 | 0.1689 | 27.8119 | structure_gap, luminance_gap, color_shift |
| T13 | center | 13.0698 | 0.7774 | 0.2201 | 21.3801 | luminance_gap, color_shift |
| T13 | dark | 13.4102 | 0.6075 | 0.2117 | 20.0789 | structure_gap, luminance_gap, color_shift |
| T13 | highlight | 12.5100 | 0.7698 | 0.2269 | 25.3351 | luminance_gap, color_shift |
| T13 | texture | 12.4335 | 0.7041 | 0.2328 | 24.7257 | structure_gap, luminance_gap, color_shift |
| T13 | corner | 12.2612 | 0.6841 | 0.2421 | 23.0099 | structure_gap, luminance_gap, color_shift |
| T14 | center | 15.9900 | 0.7786 | 0.1221 | 15.1623 | luminance_gap, color_shift |
| T14 | dark | 21.8322 | 0.7477 | 0.0766 | 7.7375 | structure_gap |
| T14 | highlight | 12.7825 | 0.8445 | 0.2138 | 19.9884 | luminance_gap, color_shift |
| T14 | texture | 16.4639 | 0.6830 | 0.1128 | 14.2223 | structure_gap, luminance_gap, color_shift |
| T14 | corner | 22.3740 | 0.8810 | 0.0663 | 8.7020 | acceptable |

## 9. 代表性可视化

### T01

![T01 dpc](../figures/T01_a0006-IMG_2787_week6_dpc_static_dynamic.png)

![T01 lsc](../figures/T01_a0006-IMG_2787_week6_lsc_mesh.png)

![T01 demosaic](../figures/T01_a0006-IMG_2787_week6_demosaic_compare.png)

![T01 awb](../figures/T01_a0006-IMG_2787_week6_awb_compare.png)

![T01 ccm](../figures/T01_a0006-IMG_2787_week6_ccm_deltae.png)

![T01 tone](../figures/T01_a0006-IMG_2787_week6_tone_curves.png)

### T08

![T08 dpc](../figures/T08_a0022-IMG_2380_week6_dpc_static_dynamic.png)

![T08 lsc](../figures/T08_a0022-IMG_2380_week6_lsc_mesh.png)

![T08 demosaic](../figures/T08_a0022-IMG_2380_week6_demosaic_compare.png)

![T08 awb](../figures/T08_a0022-IMG_2380_week6_awb_compare.png)

![T08 ccm](../figures/T08_a0022-IMG_2380_week6_ccm_deltae.png)

![T08 tone](../figures/T08_a0022-IMG_2380_week6_tone_curves.png)

### T09

![T09 dpc](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week6_dpc_static_dynamic.png)

![T09 lsc](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week6_lsc_mesh.png)

![T09 demosaic](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week6_demosaic_compare.png)

![T09 awb](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week6_awb_compare.png)

![T09 ccm](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week6_ccm_deltae.png)

![T09 tone](../figures/T09_a0023-07-06-02-at-15h06m48-s_MG_1489_week6_tone_curves.png)

### T13

![T13 dpc](../figures/T13_a0035-dgw_048_week6_dpc_static_dynamic.png)

![T13 lsc](../figures/T13_a0035-dgw_048_week6_lsc_mesh.png)

![T13 demosaic](../figures/T13_a0035-dgw_048_week6_demosaic_compare.png)

![T13 awb](../figures/T13_a0035-dgw_048_week6_awb_compare.png)

![T13 ccm](../figures/T13_a0035-dgw_048_week6_ccm_deltae.png)

![T13 tone](../figures/T13_a0035-dgw_048_week6_tone_curves.png)

## 10. 本周结论

1. DPC 已经补上动态检测与静态 defect map 的差异：动态看当前帧，静态看标定坐标。
2. LSC 已经补上 flat-field / mesh LUT 的来源，但仍需真实均匀白场才能做产品级结论。
3. Demosaic 已经有 OpenCV baseline 和 edge-aware 对照，下一步可以接 OpenISP Malvar 或 AHD 实作。
4. AWB 已经从 Gray World 扩展到 White Patch 和 Gray ROI，能解释不同假设的失败场景。
5. CCM 已经有 DeltaE 和差异放大图，能回答“视觉上不明显但数值上如何评价”。
6. Gamma/Tone 已经补上 sRGB OETF 和 S-curve LUT，和 OpenISP GAC 的 LUT 思路接上了。
7. IQA 已经从全图指标推进到 ROI 指标 + 主观标签，后续可以手工固定更有语义的肤色、天空、高光、暗部 ROI。

## 11. 深度补强：Week6 之后还差什么

Week6 已经补了很多短板，但它仍然是学习版补强，不是产品级验证闭环。下面这些限制必须明确写出来。

### 11.1 合成 flat-field 不能替代真实标定

当前 LSC mesh 实验使用 synthetic flat-field，因此所有样张上的 mesh gain MAE 相同。这说明它验证的是：

```text
mesh gain 估计流程能跑通
```

而不是：

```text
真实镜头 shading 已被准确校正
```

产品级 LSC 仍需要：

- 真实均匀光源；
- 多帧平均；
- R/Gr/Gb/B 四通道独立 mesh；
- 中心、边缘、四角残差验证；
- 噪声放大检查。

### 11.2 DeltaE 仍然不是标准色卡 DeltaE

Week6 的 DeltaE 是相对 rawpy reference 的学习版评价。它有价值，但必须说明边界：

| 当前 DeltaE | 标准 DeltaE |
|---|---|
| 输出图 vs rawpy reference | 色卡实测值 vs 标准 Lab |
| 衡量是否接近 rawpy | 衡量颜色是否准确 |
| 适合学习趋势 | 适合产品色彩标定 |

后续如果要真正评价 CCM，需要 ColorChecker：

```text
拍色卡 -> 提取 24 色块 -> 转 Lab -> 计算 CIEDE2000 DeltaE
```

### 11.3 主观标签需要定义标准

当前标签如 `acceptable`、`color_shift`、`structure_gap`、`luminance_gap` 已经比只看指标更好，但还需要固定判定标准。

建议：

| 标签 | 建议定义 |
|---|---|
| acceptable | 无明显偏色、结构破坏或亮度错误 |
| color_shift | 中性区域明显偏色，或 DeltaE 明显偏高 |
| structure_gap | 边缘/纹理相对 reference 明显模糊或错位 |
| luminance_gap | 局部亮度与 reference 差异明显 |
| artifact | 可见假彩、拉链、摩尔纹、halo 或坏点残留 |

### 11.4 时序稳定性暂未覆盖

当前所有实验都是单帧图像。视频或连拍 ISP 还需要考虑：

- AWB gain 是否帧间跳动；
- DPC 动态检测是否忽隐忽现；
- tone mapping 是否闪烁；
- LSC / CCM 参数是否随场景异常变化。

这部分不是 Stage1 必须完成，但报告中应说明：单帧 IQA 不能代表视频稳定性。

### 11.5 性能基准还没有建立

产品级 ISP 还关心运行时间和内存。

建议后续增加 per-module benchmark。下表是尚未实测的计划模板，不属于当前完成证据：

| 模块 | 运行时间 ms | 内存 MB | 是否易并行 | 备注 |
|---|---:|---:|---|---|
| BLC | 待填写 | 待填写 | 是 | 像素级操作 |
| DPC | 待填写 | 待填写 | 部分 | 邻域操作 |
| LSC | 待填写 | 待填写 | 是 | gain map 乘法 |
| Demosaic | 待填写 | 待填写 | 是 | 卷积/插值 |
| AWB | 待填写 | 待填写 | 是 | 统计 + gain |
| CCM | 待填写 | 待填写 | 是 | 3x3 矩阵 |

## 12. 下一轮最值得做的三个实验

如果继续完善 Stage1，建议优先做：

1. **DPC 注入坏点参数扫描。** 现有数据即可做，能补 recall / false positive。
2. **Demosaic 伪影 crop 库。** 选斜边、纹理、树枝、文字区域，专门看 zipper / false color / moire。
3. **语义 ROI IQA。** 手工固定 skin / sky / dark / highlight / texture crop，替代完全自动 ROI。

ColorChecker 和真实 flat-field 也非常重要，但它们需要额外标准数据。没有数据时，报告应写清楚流程和需求，不要把 synthetic 或 rawpy reference 包装成产品级 ground truth。

## 13. 综合调试参数地图

| 现象 | 首查数据/参数 | 原因 | 不应直接做的事 |
|---|---|---|---|
| 暗部整体发灰或死黑 | per-channel black level、0 附近比例 | BLC 是后续所有暗部统计的零点 | 先调 Tone 掩盖错误 |
| 孤立彩点或小十字 | DPC mask、`min_delta`、`mad_k` | 坏点经 Demosaic 会跨像素/通道扩散 | 只在最终 RGB 模糊 |
| 角落偏色且噪声更强 | LSC 四通道 gain、edge gain | gain 同时补偿信号并放大噪声 | 用 AWB 全局 gain 修位置问题 |
| 斜边 zipper/false color | CFA、border、Demosaic crop | 插值方向或 pattern 解释错误 | 只看全图 PSNR |
| 全局偏色 | neutral ROI、AWB gain、CCM 方向 | 统计假设或颜色空间约定错误 | 同时乱调 AWB 与 CCM |
| 高光平、主体暗 | Tone percentile/curve、per-channel clip | 动态范围分配不合适 | 只改 Gamma 期待恢复已丢细节 |

调试遵循第一发散点原则：保存每个阶段的 shape、dtype、range、直方图和固定 ROI；从第一个与预期不一致的阶段开始，而不是从最终 PNG 反向猜测。

## 14. 毕业实验执行手册

### 14.1 从哪里开始、怎样结束

Week6 不是再增加一个算法，而是把整个 Stage 1 组织成可审计的工程闭环：

```text
确认环境与测试
  -> 选 T01 做单样张 smoke test
  -> 逐阶段保存 shape/dtype/range/linear 状态
  -> 对 T01/T08/T13 做代表性模块对照
  -> 对异常样张执行第一发散点诊断
  -> 冻结输入与参数做单变量 sweep
  -> 记录接受方案、拒绝方案及副作用
  -> 在干净目录完成独立毕业任务
```

从 `stage1_soft_isp/` 运行：

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/17_run_pipeline.py data/raw/T01_a0006-IMG_2787.dng `
  --config configs/default.yaml `
  --output-dir outputs/tutorial/week6/pipeline
python scripts/16_close_mastery_gaps.py `
  data/raw/T01_a0006-IMG_2787.dng `
  data/raw/T08_a0022-IMG_2380.dng `
  data/raw/T13_a0035-dgw_048.dng `
  --max-size 1200 `
  --out-dir outputs/tutorial/week6/gaps `
  --report outputs/tutorial/week6/gaps/mastery_gap_closure_report.md
```

成功产物不只是 Markdown：还应有统一 Pipeline 的 `preview.png`、metadata/逐阶段 JSON、各对照图和可复述的失败记录。`--max-size=1200` 是保持 Bayer 对齐的中心 crop 加速协议；`0` 表示全尺寸。crop 结果不能直接冒充全分辨率延迟或角落 IQ，因为中心裁剪可能排除真实四角。

### 14.2 关键输入输出合同

| 检查点 | 必须记录 | 失败时影响 |
|---|---|---|
| DNG/RAW | hash、shape、CFA、black/white、orientation、未知 metadata | 输入变更后旧结果不可追溯 |
| RAW stages | `(H,W)`、dtype、有效范围、per-CFA statistics | BLC/DPC/LSC 的错误会传播至所有 RGB 模块 |
| RGB stages | `(H,W,3)`、Camera/target primaries、linear/encoded 标志 | AWB/CCM/Tone 责任边界混乱 |
| reference | rawpy 生成设置、尺寸/方向、文件身份 | 指标变化可能只是 reference 协议变化 |
| result | 参数快照、软件版本、输入集合、输出路径 | 无法复现或公平比较 |

独立复现需要额外记录 Python、NumPy、OpenCV、scikit-image/rawpy 版本、CPU/OS、随机种子（如使用随机注入）和命令行。当前历史数表是仓库已有执行证据；若环境版本不同，应重新生成并记录差异，不能默认末位数字完全一致。

### 14.3 综合参数百科

| 参数 | 默认/单位 | 增大后的方向 | 关键耦合 | 验收/失败现象 |
|---|---:|---|---|---|
| DPC `min_delta` | 1024 RAW code | 检测更保守 | `mad_k`、bit depth、ISO | 注入 recall 下降，强边缘误检减少 |
| DPC `mad_k` | 12，无量纲 | 对残差离散更宽容 | `min_delta`、纹理 | mask 过密/过稀都需双指标解释 |
| LSC edge gains/power | 每通道约 1.12–1.22 / 2.0 | 角落补偿/边缘集中度增强 | 噪声、clip、AWB | center/corner residual 与噪声同时检查 |
| AWB low/high percentile | 5/95% | 收紧时样本更纯但覆盖更低 | 曝光、场景颜色、max gain | gain 触顶或灰点覆盖率过低 |
| AWB `max_gain` | 8× | 允许极端校正但放大噪声/clip | Sensor 响应、统计过滤 | 暗部彩噪、高光通道截断 |
| Tone percentile | 99.5% | 主体通常更暗、高光余量增大 | 场景高光、曲线 | 主体/高光 ROI 与曲线一起判断 |
| Gamma | 2.2 | 中暗调通常更亮 | 是否已 OETF、Tone 输出 | 重复编码泛白，漏编码偏暗 |
| `max_size` | 1200 pixel | 更多空间内容、计算/内存增加 | Bayer 偶数对齐、角落覆盖 | 速度与代表性取舍，不是 IQ 参数 |

### 14.4 一个完整 RCA 应怎样写

以“T08 动态 DPC 候选过多”为例，报告只能确认候选数异常，不能直接断言真实坏点很多。合格 RCA 依次包含：

1. **现象：** T08 动态候选 7907，明显高于多数样张。
2. **第一发散点：** BLC 后 DPC residual/mask，而不是最终 PNG。
3. **假设：** 纹理/高光、不同有效位深、噪声或阈值尺度造成误检。
4. **隔离：** 检查 metadata 和 mask 空间分布；与注入平坦区的 recall/额外检测分开评价；扫描 `min_delta × mad_k`。
5. **结果：** 只陈述重新运行得到的表和 crop；本报告现有数量不足以区分上述根因。
6. **决策：** 若候选集中在真实边缘，优先提高保护/改方向修复；代价是 hot pixel recall 可能下降。
7. **回归：** 固定 T01/T08/T13、注入集、强边缘 crop 和单元测试，防止只修一张图。

这套“现象—第一发散点—假设—隔离—结果—决策—回归”模板也适用于 AWB gain 跳变、CCM 色偏和 Tone 高光发灰。

### 14.5 证据总账与工程取舍

| 证据 | 等级 | 当前可下结论 | 明确不能外推 |
|---|---|---|---|
| 35 项合成/边界单元测试 | `verified_synthetic` | 核心数学合同和已覆盖边界通过 | 真实 Camera IQ、性能和时序 |
| 14 张公开 DNG 图表 | `verified_public` | 不同真实 RAW 文件上流程可运行 | 自采 Sensor、实验室 chart 和量产 tuning |
| rawpy/自动 ROI/DeltaE | `verified_proxy` | 相对指定 reference 的趋势与问题候选 | 绝对颜色、主观质量、标准 IQ |
| synthetic flat/坏点 | `verified_synthetic` | mesh、注入和调参方法有效 | 真实 shading/坏点分布 |
| ColorChecker、dark/flat、slanted-edge、连续序列 | `not_run` | 当前无 | DeltaE2000、PTC/DR、标准 MTF、时序稳定性 |
| per-module latency/memory/target device | `not_run` | 当前无 | 实时性、功耗、Snapdragon 性能 |

最终工程决策不能只优化一个数：更强 LSC/AWB gain 会放大噪声或 clipping；更复杂 Demosaic 可能降低伪影但增加延迟；更强 Tone 可保护范围却降低局部对比；更小 mesh/tile 更贴合 shading 也更敏感于噪声和块状边界。每次接受参数都要留下被拒方案和副作用。

### 14.6 跨阶段连接与毕业验收

Stage 1 的输出不是“最好看的 PNG”，而是三类资产：可解释的 RAW→RGB 数据合同、针对模块的验证方法、可复盘的 failure/RCA。它们分别交给后续 AI 数据准备、C++ 重写和部署数值对齐；若没有中间值和证据边界，后续只能对最终图猜错因。

- [ ] 能在干净输出目录完成 T01 的统一 Pipeline 和三张代表样张补强实验
- [ ] 能画出 Week1–6 数据流并标注 shape、dtype、range、linear/encoded
- [ ] 能独立实现至少一个模块及其 identity/边界/failure 测试
- [ ] 能完成一次单变量 sweep，保存最佳与至少一个拒绝方案
- [ ] 能按七步 RCA 模板解释一个真实失败样张
- [ ] 能把 `verified_public/proxy/synthetic/not_run` 用于每条结论
- [ ] 能回答本周五类面试题，并说明 Snapdragon/量产证据仍缺什么

## 15. 本周面试闭环

完整参考答案见[Week 6：系统调试面试题](../interview/week6_system_debug_questions.md)。

1. **概念题：** Stage 1 的输入合同、模块验证和最终 IQ 评价为什么是三种不同证据？
2. **原理题：** 第一发散点原则为何比从最终 PNG 反向调参更可靠？
3. **参数题：** sweep 如何冻结输入、指标和其他模块，并处理耦合参数？
4. **调试题：** 指标改善但局部纹理变差时，如何做 RCA、回退和回归？
5. **系统题：** 怎样设计 ColorChecker、flat-field、slanted-edge、dark-frame 和连续序列的完整采集协议？

## 16. 高通岗位补强：从单帧 Soft ISP 到连续 Camera 系统

Stage 1 已覆盖单帧 RAW→RGB 的主要数学模块，但 Camera ISP System 面试通常还会追问 3A、连续帧、新型 Sensor 和时序稳定性。下面内容用于建立可回答的系统模型；当前仓库没有把这些设计实现为量产算法，证据均保持 `not_run/concept_only`。

### 16.1 AE/AWB/AF 为什么不是三个独立函数

3A 是跨帧闭环：第 `n` 帧生成统计，算法经过处理延迟后把 exposure、gain、WB 或 lens position 应用到第 `n+k` 帧。场景在这段时间内可能已经变化，所以只在单张图上得到“正确参数”并不保证视频稳定。

```text
frame n RAW
  -> grid/histogram/face/focus statistics
  -> filter + scene/ROI decision
  -> AE/AWB/AF controller
  -> metadata request with delay k
  -> sensor/lens applies on frame n+k
  -> observe response and close loop
```

曝光的一阶近似可以写成：

```text
exposure_value ∝ exposure_time * analog_gain * digital_gain
```

相同总增益并不等价：更长曝光可能降低相对 read noise，却增加运动模糊；analog gain 改变 Sensor 信号和噪声分布；digital gain 只放大已量化信号与噪声并增加 clipping 风险。AE 需要在亮度目标、帧率、运动、噪声和防闪烁量化之间取舍。

常见时域平滑为：

```text
u_t = (1 - alpha) * u_(t-1) + alpha * u_target
```

`alpha` 大则响应快但更容易闪烁/振荡，小则稳定但场景切换拖尾。hysteresis/dead band 在误差较小时保持上一状态，避免统计噪声造成来回跳变。调试时必须把 stats frame id、decision、applied frame id 和实际 metadata 对齐，否则会把控制延迟误判为算法错误。

AWB 还要排除过暗、饱和和强色物体 ROI，并处理 CCT/illuminant 置信度；单帧 Gray World 不等于视频 AWB。AF 至少要理解 contrast AF 的 focus-value 曲线、lens sweep、峰值搜索、hysteresis 和 scene change；PDAF 还会引入相位差、置信度、遮挡与标定问题。本仓库没有 AF/PDAF 实现。

### 16.2 Staggered HDR、Quad Bayer 与融合误差

Staggered HDR 在相邻或交错时序获取不同曝光。若先把各曝光换算到共同线性辐照度域，可写成简化融合：

```text
radiance_i = max(raw_i - black_i, 0) / (exposure_i * gain_i)
Y = sum(w_i * radiance_i) / max(sum(w_i), epsilon)
```

权重 `w_i` 应降低黑位附近 read-noise 主导像素、饱和像素、运动不一致像素和坏点的贡献。只按亮度做权重会在运动边缘产生 ghost；black/white level、gain 或行曝光时序不一致会形成条带与颜色错位。真实系统还需要理解 rolling-shutter row timing，而不只是两张静态图的全局 exposure ratio。

Quad Bayer 同一颜色通常以 `2×2` 子阵列排列，可用于低照度 binning，也可 remosaic 到高分辨率 Bayer。关键问题是 CFA 语义、相位、坏点/串扰、binning 与 remosaic 的分辨率—噪声权衡；不能把普通 RGGB pack 直接称为 Quad Bayer 支持。

### 16.3 TNR/MFNR 的时序质量问题

最简时域融合可以写成：

```text
Y_t = w_t * X_t + (1 - w_t) * warp(Y_(t-1))
```

静态平坦区可减小 `w_t` 以获得更多历史降噪；运动、遮挡、scene cut 和配准低置信区域应增大 `w_t`，减少 ghost/trail。需要联合关注 temporal noise、detail retention、motion ghost、flicker 和恢复时间。单帧 PSNR 提高不能证明 TNR 可用，必须使用连续序列和时域指标。

### 16.4 参数—现象—首查表

| 现象 | 首查参数/状态 | 机制与权衡 |
|---|---|---|
| 亮度来回跳 | stats delay、`alpha`、dead band | 延迟闭环和过大响应增益可能振荡 |
| AWB 色温闪烁 | ROI filter、illuminant confidence、temporal smooth | 强色物体或低置信统计驱动错误切换 |
| 低光拖影 | exposure time、motion score、TNR history weight | 更长曝光/更强历史融合换噪声但损失运动 |
| HDR ghost | exposure timing、registration、motion weight | 不同曝光没有在同一场景位置表达同一辐照度 |
| 高光偏色 | channel saturation、white level、WB-before-merge | 通道饱和状态不同，简单比值失效 |
| Quad Bayer 伪色 | CFA phase、remosaic kernel、边界 | 相位/邻域错误把颜色采样当空间纹理 |
| AF hunting | focus confidence、step、hysteresis、scene change | 峰值不稳定或控制器反复越过峰值 |

### 16.5 面试练习与证据边界

1. 画出 frame `n` stats 到 frame `n+k` 生效的 3A 时序，解释为什么日志必须带 frame id。
2. 比较 exposure time、analog gain、digital gain 对亮度、噪声、模糊和 clipping 的不同影响。
3. 设计一个 AE 场景切换实验，给出响应时间、overshoot、flicker 和稳态误差指标。
4. 说明 Staggered HDR 中 black level、exposure normalization、motion mask 和 saturation mask 的顺序。
5. 解释 Quad Bayer binning/remosaic 与当前 pseudo RGGB pack 的本质差别。
6. 设计 TNR 的静态、平移、遮挡、scene cut 四类序列，并给出 artifact reject 条件。

当前可迁移证据是单帧 ISP 合同、AWB/曝光参数方向、Toy HDR 和 failure/RCA 方法；AE/AF state machine、真实 Staggered HDR、Quad Bayer、TNR/MFNR、连续帧 metadata 时序均未实测。面试时可讲设计和验证方案，不能讲成“已在高通 Camera pipeline 完成”。
