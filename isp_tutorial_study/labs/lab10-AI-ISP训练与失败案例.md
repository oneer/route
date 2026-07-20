# Lab 10：AI-ISP 训练、评估与失败案例

对应章节：28–29。

## 目标

完成最小数据—训练—测试—失败分析闭环，并明确模型输入域、数据合同、传统基线和部署限制。

## Smoke 数据与训练

```powershell
Set-Location D:\document\route
$env:PYTHONPATH='stage2_ai_isp'
python -m unittest discover -s stage2_ai_isp/tests -v
python stage2_ai_isp/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_smoke_dncnn_l2.yaml
```

真实数据实验按 [`stage2_ai_isp/quickstart.md`](../../stage2_ai_isp/quickstart.md) 准备 SIDD 子集，不得把 smoke 合成数据结果当作真实相机结论。

## 必做检查

- train/val/test 是否按图像或场景隔离，而不是随机切 patch 泄漏。
- noisy/clean 是否对齐、值域一致、颜色处理一致。
- 至少一个传统基线与一个神经网络基线。
- PSNR/SSIM/MAE + 固定 crop + error map + failure gallery。
- 模型参数量、MAC/延迟、峰值内存和 tile seam。

## 失败矩阵

可运行现有场景评价与失败导出脚本：

```powershell
$out = 'isp_tutorial_study/lab_outputs/lab10/camera_scene_evaluation'
python stage2_ai_isp/scripts/24_evaluate_camera_scenes.py --output-dir $out
python stage2_ai_isp/scripts/25_export_scene_failure_matrix.py "$out/per_sample_metrics.csv" --output "$out/failure_matrix.csv"
```

若脚本要求先生成 manifest，按同目录的 `23_prepare_camera_scene_comparison.py` 执行并记录参数。

## 验收

- 明确模型输入是 RAW、线性 RGB 还是 sRGB。
- 不用训练集指标作为最终结论。
- 至少保留三类失败：残余噪声、过平滑/结构损失、颜色或亮度偏移。
- 说明模型失败时的 fallback、置信度或传统路径。
