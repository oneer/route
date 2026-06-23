# Week 0：固定 PyTorch Baseline

## 1. 为什么需要

部署对齐必须冻结 checkpoint、输入、预处理和评价口径，否则后端差异会与模型/数据变化混在一起。

## 2. 输入输出协议

输入 `RGB uint8/HWC → float32/NCHW/[0,1]`，shape `[1,3,512,512]`；DnCNN 输出 float NCHW，评价前 clamp `[0,1]`。完整 contract：`configs/deployment_contract.yaml`。

## 3. 链路角色

PyTorch FP32 是质量 golden baseline；后续 ORT、TensorRT、INT8 都在同一 manifest 上与它或 ORT FP32 对齐。

## 4. 核心概念/API

`model.eval()` 固定推理语义；`torch.no_grad()` 关闭梯度；GPU 测时必须同步。checkpoint、ONNX、INT8 hash 在 `outputs/audit/model_card.json`。

## 5. 对应文件

- `configs/week0_baseline.yaml`
- `scripts/01_week0_pytorch_baseline.py`
- `data/test_inputs/week0_fixed_manifest.csv`

## 6. 运行命令与环境

```powershell
python stage4_deploy_isp/scripts/01_week0_pytorch_baseline.py --config configs/week0_baseline.yaml
```

本次为 `torch 2.12.0+cpu`，20 张 512×512 RGB paired 图。

## 7. 正确输出

`week0_metrics.csv`、`week0_summary.csv`、20 张 output/triplet/error map。

## 8. 对齐指标与阈值

本周没有跨后端阈值；质量结果为 noisy `26.5687 dB/0.93383`，模型 `32.9839 dB/0.98479`，PSNR 提升 `6.4152 dB`。

## 9. 常见失败与排查

依次检查 checkpoint、source config、RGB、NCHW、`/255`、residual 行为、clamp 和 manifest。

## 10. 性能测量

每图 warmup 3、timed 10；CPU mean/p50/p90 为 `261.65/182.86/496.39 ms`。模型加载和文件 I/O不计入。

## 11. Tradeoff

DnCNN graph 简单、容易部署，但不是最先进 restoration 架构；当前选择优先保证教学闭环，而非追求最高画质。

## 12. 证据边界

这是 SIDD tiny 20 张子集和 CPU baseline，不代表完整 SIDD、移动设备、功耗或 GPU 性能。

## 13. 练习与掌握标准

修改 RGB/BGR、NCHW/NHWC、range 各一次并解释症状；能从 model card 独立恢复相同输入输出协议即达标。
