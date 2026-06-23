# Week 1：ONNX 导出与 ORT Python 对齐

## 1. 为什么需要

ONNX 只是中间表示；导出成功不等于算子语义、shape 和数值正确。

## 2. 输入输出协议

固定 `input/output`、`[1,3,512,512]`、RGB、NCHW、float32、`[0,1]`。ONNX 是 fixed shape、opset 18。

## 3. 链路角色

ONNX 承接 PyTorch 与不同 runtime；ORT CPU 是后续 C++、CUDA、TensorRT 和 QDQ 的稳定 reference。

## 4. 核心概念/API

脚本执行 `eval()`、dummy input、`torch.onnx.export`、constant folding、`onnx.checker.check_model` 和 graph 统计。当前 PyTorch 导出链路会使用新版 exporter 依赖；保留 `dynamic_axes` 配置用于教学，但本实测为 fixed shape。

shape inference、Netron 和 simplifier 的角色分别是补 shape、人工看图、简化图；未运行 simplifier，所以不写成完成成果。

## 5. 对应文件

- `configs/week1_onnx.yaml`
- `scripts/03_week1_export_validate_onnx.py`
- `models/onnx/dncnn_sidd_tiny_fp32.onnx(.data)`

## 6. 运行命令与环境

```powershell
$env:PYTHONIOENCODING='utf-8'
python stage4_deploy_isp/scripts/03_week1_export_validate_onnx.py --config configs/week1_onnx.yaml
```

## 7. 正确输出

checker 通过；graph 为 Conv×5、Relu×4、Sub×1；20 张 ORT output 和 error map。

## 8. 对齐指标与阈值

报告 max/mean/alignment PSNR 和对 clean GT 的 PSNR/SSIM。实测 max `4.17e-7`、mean `3.40e-8`，低于项目阈值 `1e-4`。

## 9. 常见失败与排查

顺序：external `.data` 是否同目录 → input name/shape → eval → layout/range → clamp → opset/unsupported op → dynamic shape。

## 10. 性能测量

Week 1 只做 correctness，不用导出耗时或 session creation 冒充 steady-state latency。

## 11. Tradeoff

fixed shape 便于首次 TensorRT 构建和稳定比较；dynamic shape 更灵活但需要 profile、更多 shape 测试和可能不同的优化图。

## 12. 证据边界

ONNX 外部权重文件是硬依赖；Netron/onnxsim 没有形成仓库内实测证据。官方 exporter 行为随 PyTorch 版本变化，访问资料日期为 2026-06-23。

## 13. 练习与掌握标准

比较 fixed/dynamic shape，故意移走 `.onnx.data`，解释 checker、runtime load 与数值对齐分别能发现什么问题。
