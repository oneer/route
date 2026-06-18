# 阶段二严格评估协议

## 1. 数据划分

```text
train: 更新模型参数
validation: 选择 checkpoint、模型和超参数
test: 方案冻结后只运行一次最终评估
```

默认 SIDD tiny 构建为 80 train、20 validation、20 test。禁止将同一 source scene
同时放入多个 split。`manifest.csv` 是数据来源审计记录。

重新生成：

```bash
python stage2_ai_isp/scripts/07_prepare_sidd_small_subset.py \
  --train-count 80 --val-count 20 --test-count 20 --crop-size 512
```

## 2. 指标口径

- 输入和输出：RGB、float32、范围 `[0, 1]`。
- PSNR：在 RGB 全部通道和像素上计算 MSE，`MAX=1`。
- SSIM：11×11 Gaussian window，sigma=1.5，逐 RGB 通道计算后平均。
- 默认 test 评估完整 512×512 图片，不使用随机 crop。
- 模型输出在指标计算前 clamp 到 `[0, 1]`。

这些指标用于本仓库内部比较。与论文或官方榜单对比前，必须额外确认：

- RGB 还是 Y 通道；
- 是否裁剪边界；
- 8-bit 量化还是 float；
- 官方数据划分；
- SSIM 实现与窗口。

> Week 0-9 已保存的历史 SSIM 来自早期简化实现。它们可用于阅读历史实验趋势，
> 但在新版协议下必须重新评估后，才能进入最终 test 表或与外部结果比较。

## 3. 模型选择

- `best_psnr.pth` 只表示 validation PSNR 最好。
- 如果目标包含结构、颜色或主观画质，需要同时检查 SSIM、triplet 和 error map。
- test 结果不能用于重新选择模型；否则 test 会退化成新的 validation。

## 4. 公平对比

比较架构时固定：

```text
data split
seed
loss
steps
patch size
batch 或总训练样本数
validation frequency
metric protocol
```

如果显存导致 batch 不同，应报告总训练 patch 数和原因。参数量、训练时间和 latency
必须与质量指标放在同一张表中。

## 5. 最终 test 命令

```bash
python stage2_ai_isp/scripts/22_evaluate_test_set.py \
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml \
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth
```

输出必须包含配置、checkpoint、样本数、PSNR、SSIM 和 CPU 单次推理时间。正式报告还需
注明机器、PyTorch 版本和线程设置。

数据划分审计：

```bash
python stage2_ai_isp/scripts/23_audit_dataset_splits.py
```
