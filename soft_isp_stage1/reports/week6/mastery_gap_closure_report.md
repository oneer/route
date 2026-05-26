# Week 6 补短板实验报告

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

OpenCV edge-aware 可以作为 AHD/方向自适应类方法的入门对照。它不等于完整产品 demosaic，但能说明：方向信息和边缘保护通常比单纯同色平均更适合高频纹理与斜边。

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
