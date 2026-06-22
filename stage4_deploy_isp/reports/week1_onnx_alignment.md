# 第 1 周：ONNX 导出与语义对齐

## 目标

Week 1 的目标不是“能导出 ONNX 就结束”，而是证明 ONNX Runtime 的输出和 PyTorch golden output 在固定测试集上语义一致。

本周验收项：

- 导出 `models/onnx/dncnn_sidd_tiny_fp32.onnx`。
- 使用 `onnx.checker.check_model()` 做模型合法性检查。
- 记录 ONNX graph 输入、输出、opset 和算子统计。
- 使用 ONNX Runtime CPUExecutionProvider 跑固定 20 张 SIDD tiny 验证图。
- 输出 PyTorch vs ONNX Runtime 的 max abs error、mean abs error、PSNR 和 error map。

## 运行命令

```powershell
python stage4_deploy_isp/scripts/03_week1_export_validate_onnx.py --config configs/week1_onnx.yaml
```

## 核心概念

- ONNX 是模型中间表示，不是加速器。导出成功只说明 graph 可以序列化，不代表数值语义正确。
- ONNX Runtime 是第一个 correctness baseline。后续 TensorRT、NCNN、MNN 都应先和 ORT / PyTorch 对齐，再谈速度。
- 对图像任务来说，`layout`、`range`、`dtype`、`normalization` 和 `clamp` 比分类任务更容易引入可见画质问题，例如偏色、暗区噪声残留或高光 clipping。

## 输出文件

- `models/onnx/dncnn_sidd_tiny_fp32.onnx`
- `outputs/week1_onnx/onnx_graph_summary.md`
- `outputs/week1_onnx/week1_onnx_alignment.csv`
- `outputs/week1_onnx/week1_onnx_alignment_summary.csv`
- `outputs/week1_onnx/ort_outputs/`
- `outputs/week1_onnx/pytorch_vs_ort_error_maps/`

## 实验结果

| 项目 | 结果 |
|---|---:|
| 固定测试图像 | 20 对 |
| ONNX opset 版本 | 18 |
| ONNX 节点数 | 10 |
| Conv / Relu / Sub | 5 / 4 / 1 |
| ORT 与 PyTorch 最大绝对误差 | 4.17e-7 |
| ORT 与 PyTorch 平均绝对误差 | 3.40e-8 |
| ORT 与 PyTorch 对齐 PSNR | 80.00 dB |
| ORT 输出平均画质 PSNR | 32.98 dB |
| PyTorch 输出平均画质 PSNR | 32.98 dB |

结论：ONNX Runtime 与 PyTorch 输出高度一致，误差远低于 `1e-4` 验收线。这个结果说明当前 DnCNN 部署模型的 ONNX 表达没有引入可见数值语义变化，后续可以把 ORT 作为 C++、TensorRT 和 NCNN 的 correctness baseline。

ONNX graph 结构也比较适合部署：

```text
Conv x5
Relu x4
Sub x1
```

其中 `Sub` 对应 DnCNN 的残差学习：`output = input - predicted_noise`。这点对 AI-ISP / ISP 算法岗很重要，因为它能解释 AI 模块不是凭空“生成干净图”，而是在学习噪声残差。

## 工具链记录

- 当前使用新版 PyTorch ONNX exporter，实际导出需要 `onnxscript`。
- Windows PowerShell 默认 GBK 编码会被 exporter 的 UTF-8 日志字符影响；运行时设置了 `PYTHONIOENCODING=utf-8`。
- 当前 ONNX 导出产生了 `.onnx` 和 `.onnx.data` 两个文件，这是 exporter 对权重外部数据的保存形式；后续 C++ / ORT 加载时需要保证两个文件在同一目录。

## 后续判断

如果 `max_abs_error` 超过 `1e-4`，优先排查：

1. 模型是否 `eval()`。
2. 输入是否 `NCHW / float32 / [0, 1]`。
3. 输出是否做了相同的 clamp。
4. ONNX opset 是否改变算子语义。
5. 后续如果改为 dynamic shape，是否触发 padding / shape 分支差异。
