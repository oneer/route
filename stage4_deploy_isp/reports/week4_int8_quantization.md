# 第 4 周：INT8 量化与画质损失分析

## 目标

Week 4 关注 INT8 是否值得，而不是只关注速度。对 AI-ISP / ISP 算法岗来说，INT8 后如果暗区噪声、颜色或纹理明显变差，即使速度提升也未必可接受。

## 方法

当前使用 ONNX Runtime static quantization：

- 格式：QDQ。
- activation：QUInt8。
- weight：QInt8。
- per-channel weight quantization：开启。
- calibration：固定测试集前 10 张图。
- evaluation：固定测试集完整 20 张图。

运行命令：

```powershell
python stage4_deploy_isp/scripts/06_week4_quantization_eval.py
```

## 输出文件

- `models/onnx/dncnn_sidd_tiny_int8_qdq.onnx`
- `outputs/week4_quantization/week4_int8_metrics.csv`
- `outputs/week4_quantization/week4_int8_summary.csv`
- `outputs/week4_quantization/int8_outputs/`

## 实验结果

| 项目 | 结果 |
|---|---:|
| 评估图像数 | 20 |
| 校准图像数 | 10 |
| FP32 平均 PSNR | 32.98 dB |
| INT8 平均 PSNR | 32.89 dB |
| 平均 PSNR 损失 | 0.091 dB |
| 最大 PSNR 损失 | 0.337 dB |
| 最差样本 | pair_00005 |
| FP32 平均延迟 | 96.72 ms |
| INT8 平均延迟 | 91.83 ms |
| FP32 延迟 p50 | 93.91 ms |
| INT8 延迟 p50 | 87.06 ms |

结论：当前 DnCNN 在 ORT CPU QDQ INT8 下平均 PSNR drop 低于 `0.1dB`，最大 drop 未超过 `0.5dB` 警戒线。这个结果可以作为“初步可接受”，但还不能直接代表端侧 NPU / GPU / TensorRT INT8 的最终画质，因为不同后端的量化 kernel、scale 处理和融合策略可能不同。

最差样本是 `pair_00005`。后续需要把它纳入 failure case 分析，重点观察：

- 红色高饱和区域是否出现 banding 或偏色。
- 暗区噪声是否比 FP32 更明显。
- 背景纹理是否进一步过平滑。
- 高光边缘是否有 clipping 或 halo。

## 判断标准

- 平均 PSNR drop 小于 `0.1dB`：通常可以接受，但仍需看失败案例。
- 最大 PSNR drop 超过 `0.5dB`：必须分析最差样本，尤其看暗区、红/蓝高饱和区域、高频纹理和高光。
- 如果 INT8 在 CPU 上没有速度收益，不代表 INT8 无价值；还需要看目标后端是否有 INT8 加速单元。
