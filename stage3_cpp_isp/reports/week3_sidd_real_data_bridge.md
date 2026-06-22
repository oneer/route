# 第 3.5 周：SIDD Tiny sRGB 真实数据桥接

## 目标

把阶段 2 的 SIDD tiny paired dataset 接入阶段 3 传统去噪实验，用真实手机图像做
视觉与指标检查。

必须明确：这些输入已经是 sRGB noisy/GT pair，不是 sensor Bayer RAW。它比纯
synthetic noise 更接近真实手机噪声，但不能据此声称完成了真实 RAW denoise。

## 数据集

- Stage 2 source：SIDD tiny paired validation data；
- Stage 3 manifest：
  `C:/Users/10439/Desktop/route/stage3_cpp_isp/data/real_cases/sidd_tiny/manifest.csv`
- 输入域：sRGB；
- paired clean target：有；
- RAW metadata、black level、Bayer pattern：无。

## 基线结果

| 指标 | 结果 |
|---|---:|
| Noisy 平均 PSNR | 26.391 dB |
| Gaussian 平均 PSNR | 32.116 dB |
| Bilateral 平均 PSNR | 29.650 dB |

结果只说明当前参数在这批 sRGB pair 上的行为。Gaussian PSNR 更高，不代表它在
所有纹理和边缘区域主观质量都更好；仍需观察 texture smoothing、color noise 与
edge preservation。

## 工程说明

- Stage 2 与 Stage 3 通过 manifest 显式连接；
- 数据域在报告中标记为 sRGB，避免与 RAW-like synthetic 主线混淆；
- 真实数据只用于 sanity check，不替代 Python-C++ correctness fixture；
- 参数若从 `[0,1]` normalized synthetic 迁移到其他 range，必须重新解释
  `sigma_range`。

## 输出

- Metrics：
  `reports/figures/week3_sidd_real/week3_sidd_real_metrics.csv`
- Figure：
  `reports/figures/week3_sidd_real/week3_sidd_real_comparison.png`
- Data card：
  `data/real_cases/sidd_tiny/README.md`
