# 第 0.5 周：部署模型与固定测试基准

## 目标

本周目标是先固定阶段四的部署对象和测试基准。阶段三尚未完全收尾，所以阶段四先采用独立的轻量 RGB restoration 部署入口，后续 Week 6 再把阶段三 C++ ISP 模块正式串入 pipeline。

## 模型选择

主部署模型选择阶段二的 `paired_rgb_sidd_tiny_dncnn_l2_300`：

- 输入：RGB 3ch，`NCHW`，`float32`，range `[0, 1]`。
- 输出：RGB 3ch，`NCHW`，`float32`，range `[0, 1]`，输出后 clamp。
- checkpoint：`stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_300/checkpoints/best_psnr.pth`。

选择 DnCNN 作为第一部署模型的原因：

- 当前阶段二指标比 300-step NAFNet-lite 更稳定。
- 结构主要由 Conv + ReLU 构成，适合 ONNX / ONNX Runtime / TensorRT / NCNN 的第一条闭环。
- 残差学习形式容易解释为“AI denoise 模块”：网络预测噪声，再从输入中减去噪声。

NAFNet-lite 保留为现代图像恢复结构参考，后续用于讲解 NAFNet / learned ISP 的先进方向和部署难点。

## 固定测试集

固定测试集使用阶段二已有的 SIDD tiny validation subset：

- noisy：`stage2_ai_isp/datasets/sidd_tiny/val/noisy`
- clean：`stage2_ai_isp/datasets/sidd_tiny/val/clean`
- 样本数：20 对 paired RGB 图像
- manifest：`stage4_deploy_isp/data/test_inputs/week0_fixed_manifest.csv`

固定测试集的作用不是追求更高排行榜指标，而是给后续所有后端建立 golden baseline：

1. PyTorch 输出作为 golden output。
2. ONNX Runtime、C++、TensorRT / NCNN 输出都和它对齐。
3. FP16 / INT8 的画质损失必须在这批固定样本上解释。

## 第 0.5 周输出

运行脚本：

```powershell
python stage4_deploy_isp/scripts/01_week0_pytorch_baseline.py --config configs/week0_baseline.yaml
```

生成内容：

- `outputs/week0_baseline/pytorch_outputs/`
- `outputs/week0_baseline/triplets/`
- `outputs/week0_baseline/error_maps/`
- `outputs/week0_baseline/week0_metrics.csv`
- `outputs/week0_baseline/week0_summary.csv`

## 实验结果

本次在当前 Python 环境中运行，`torch==2.12.0+cpu`，CUDA 对 PyTorch 不可见；机器有 RTX 4060 Ti 和 NVIDIA Driver，但 Week 0.5 baseline 先以 CPU 结果作为固定正确性基准。

| 项目 | 结果 |
|---|---:|
| 固定测试图像 | 20 对 |
| 含噪输入平均 PSNR | 26.57 dB |
| PyTorch 输出平均 PSNR | 32.98 dB |
| PSNR 提升 | +6.42 dB |
| 含噪输入平均 SSIM | 0.934 |
| PyTorch 输出平均 SSIM | 0.985 |
| SSIM 提升 | +0.051 |
| CPU 平均延迟 | 261.65 ms |
| CPU 延迟 p50 | 182.86 ms |
| CPU 延迟 p90 | 496.39 ms |

![Week 0.5 PSNR comparison](../outputs/week0_baseline/figures/week0_psnr_comparison.png)

![Week 0.5 triplet contact sheet](../outputs/week0_baseline/figures/week0_triplet_contact_sheet.png)

从可视化看，DnCNN 对 SIDD tiny 的 RGB 噪声有明显抑制，尤其在低光和红色物体区域能显著减少彩色噪声。但也能看到模型输出有轻微平滑倾向，这会成为后续 FP16 / INT8 分析的重要观察点：部署后如果进一步损失纹理或产生偏色，就不能只看 PSNR。

## 相关论文和工程背景

- DnCNN：Zhang et al. 提出用残差学习训练 CNN 去噪器，网络预测噪声分量，再从输入中减去噪声；这和本项目 `residual=true` 的部署模型一致，适合解释 AI denoise 模块的输入输出含义。论文链接：[Beyond a Gaussian Denoiser](https://arxiv.org/abs/1608.03981)。
- NAFNet：Chen et al. 提出 Nonlinear Activation Free Network，强调简单高效的图像恢复 baseline；本项目把 NAFNet-lite 保留为现代结构参考，用于后续讨论更先进 restoration 模型的部署难点，例如 LayerNorm、PixelShuffle 和动态 shape。论文链接：[Simple Baselines for Image Restoration](https://arxiv.org/abs/2204.04676)。
- SIDD / 真实噪声：真实手机噪声不是简单 AWGN，受传感器、ISO、ISP 和照明影响。阶段二的 SIDD tiny 子集用于保持 paired noisy/clean 验证闭环；后续报告会重点分析暗区、纹理和高光区域的失败案例。相关综述可参考 [NTIRE 2020 Real Image Denoising Challenge](https://arxiv.org/abs/2005.04117)。

## 当前风险

- 当前 Python 是 CPU 版 PyTorch；Week 3 若要做 GPU / TensorRT latency，需要安装或切换 CUDA 版 PyTorch，并补齐 CUDA Toolkit、CMake、TensorRT / trtexec。
- 当前环境缺 `onnx` 和 `onnxruntime`；Week 1 开始需要安装这两个依赖。
- 阶段三尚未完全收尾；Week 6 会先用阶段四自己的轻量 preprocess / postprocess 形成闭环，再把阶段三 C++ ISP 模块接入。
- 当前只用了 RGB paired denoise 任务；如果后续要更贴近 RAW-domain AI-ISP，需要追加 pseudo RAW / RGGB 输入协议和测试样本。

## 后续验收

Week 1 开始导出 ONNX。ONNX Runtime 与 PyTorch 的 max abs error 建议控制在 `1e-4` 量级；如果误差明显偏大，优先检查 layout、range、normalization、clamp 和模型 eval 状态。
