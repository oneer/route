# 阶段二最终项目报告：AI-ISP 图像恢复与部署验证

## 1. 背景

阶段二的目标不是追求单个 SOTA 模型，而是围绕 AI-ISP 岗位常见的图像恢复、
低光增强、客观评估和工程部署要求，建立一个可复现、可解释、可继续扩展的
实验闭环。

项目从 toy RGB denoise 起步，逐步接入真实 SIDD paired RGB 数据，并扩展到
pseudo RAW/RGGB 和 ONNX/C++ 部署验证。

## 2. 闭环设计

```text
toy denoise sanity check
-> SIDD paired RGB data
-> noisy input baseline
-> DnCNN / UNet / NAFNet-lite
-> PSNR / SSIM
-> triplet / error map / failure crop
-> pseudo RAW / low-light
-> ONNX / C++ deployment path
```

## 3. 数据

当前数据入口：

| 数据 | 用途 |
|---|---|
| toy RGB synthetic noise | 校准训练闭环 |
| SIDD Small sRGB tiny 80/20 | 真实 paired RGB denoise |
| synthetic low-light SIDD tiny | 低光增强实验 |
| pseudo RAW/RGGB pack | RAW-like AI-ISP 扩展 |

关键原则：

```text
paired noisy-clean 数据必须像素对齐，否则 PSNR/SSIM 和 supervised loss 都不可靠。
```

## 4. 模型

| 模型 | 项目作用 |
|---|---|
| TinyCNN | 快速验证训练管线 |
| DnCNN residual | 强 denoise baseline |
| UNet | encoder-decoder restoration baseline |
| NAFNet-lite | 现代 restoration block 轻量复现 |

## 5. 结果

| 任务 | 模型 | PSNR | SSIM |
|---|---|---:|---:|
| SIDD tiny RGB denoise | DnCNN residual | 35.5356 | 0.88367 |
| SIDD tiny RGB denoise | NAFNet-lite | 33.3269 | 0.86223 |
| SIDD tiny RGB denoise | UNet | 30.4453 | 0.88003 |
| Synthetic low-light enhancement | UNet | 24.7821 | 0.81468 |

主要结论：

```text
在当前 SIDD tiny 设置下，DnCNN residual 是最稳的 baseline。原因是该任务
输入和 clean 的结构高度一致，差异主要是噪声，residual denoise 的任务假设
更匹配。NAFNet-lite 结构更现代，但在小数据和有限训练步数下还没有超过 DnCNN。
```

## 6. 评估体系

项目不只看单一指标，而是组合使用：

| 评估方式 | 作用 |
|---|---|
| PSNR | 像素级误差 |
| SSIM | 结构相似性 |
| triplet | noisy / output / clean 主观对比 |
| error map | 局部误差定位 |
| failure crop | 面试可解释的失败案例 |

## 7. AI-ISP 扩展

新增 pseudo RAW/RGGB 数据路径：

```text
RGB paired image
-> pseudo RGGB pack
-> 4-channel DnCNN / UNet input
-> RAW-like restoration experiment
```

这个模块的定位是 RAW-like bridge，目的是让阶段二不只停留在普通 RGB denoise，
而能连接到 AI-ISP 常见的 RAW/YUV/ISP pipeline 讨论。

## 8. 工程化升级

新增部署入口：

```text
deployment/export_onnx.py
deployment/cpp_onnx_infer/
```

目标是形成：

```text
PyTorch checkpoint
-> ONNX model
-> C++ OpenCV DNN inference
-> latency / output image / PSNR-SSIM comparison
```

当前 ONNX 导出脚本已建立，实际导出依赖 `onnx` 和 `onnxscript`。

## 9. 社招 3 年项目价值

这个项目可以证明：

```text
1. 能构建真实 paired 图像恢复任务。
2. 能建立 baseline，而不是只跑单个模型。
3. 能用指标和可视化分析模型优劣。
4. 能把 RGB restoration 连接到 AI-ISP RAW-like 场景。
5. 能向 ONNX/C++ 部署方向推进。
```

不能证明：

```text
1. 真实车载摄像头量产 tuning。
2. 高通 / MTK / 海思平台 ISP 调试经验。
3. AE/AWB/AF 量产联调经验。
4. Imatest / iQ-Analyzer 工具实操经验。
```

## 10. 下一步

优先执行：

```bash
python ai_isp_stage2/scripts/13_export_engineering_summary.py
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/pseudo_raw_sidd_tiny_dncnn_l2_300.yaml
pip install -r ai_isp_stage2/deployment/requirements.txt
python ai_isp_stage2/deployment/export_onnx.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml --checkpoint ai_isp_stage2/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth --output ai_isp_stage2/deployment/onnx/dncnn_sidd_tiny.onnx --height 128 --width 128
```

最终目标：

```text
形成一份包含 PSNR、SSIM、参数量、checkpoint 大小、C++ latency 和 failure case
的完整 AI-ISP baseline 项目报告。
```
