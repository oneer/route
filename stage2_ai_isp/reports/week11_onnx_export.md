# Week 11：ONNX 导出与 PyTorch/ONNX 对齐

Week 11 的目标不是“得到一个 `.onnx` 文件”，而是证明冻结模型在新的执行后端中接收相同
张量，并产生数值一致的输出。只有文件，没有 checker 和对齐结果，不算完成。

## 1. 输入、处理与输出

```text
输入：Week 10 冻结的 config、checkpoint 和固定 RGB 图片
处理：构建 eval 模型 -> 导出 ONNX -> checker -> ONNX Runtime CPU 推理 -> float 对齐
输出：ONNX、alignment.json、两端输出图和 latency 记录
```

当前协议：

```text
layout: NCHW
dtype : float32
color : RGB
range : [0,1]
shape : [N,3,H,W]，导出时 batch/height/width 为动态轴
mode  : model.eval() + inference/no_grad
opset : 17（默认值）
```

## 2. 安装部署依赖

```powershell
python -m pip install -r stage2_ai_isp/deployment/requirements.txt
```

主训练依赖和部署依赖分开，是为了不要求只学习 Week 0-10 的人提前安装 ONNX Runtime。

## 3. 导出

```powershell
python stage2_ai_isp/deployment/export_onnx.py `
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml `
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth `
  --output stage2_ai_isp/deployment/onnx/dncnn_sidd_tiny.onnx `
  --height 128 --width 128 --opset 17
```

脚本会执行：

1. 从 YAML 重建模型；
2. 加载冻结权重并切换到 `eval()`；
3. 用 `[1,3,128,128]` dummy tensor 跟踪导出；
4. 声明动态 batch、height 和 width；
5. 安装了 `onnx` 时运行 `onnx.checker.check_model`。

Dummy shape 是导出示例输入，不等于模型只能接收 128×128。是否真的支持其他 shape，必须
用推理实验验证，不能只看 `dynamic_axes` 声明。

## 4. 数值对齐

```powershell
python stage2_ai_isp/deployment/validate_onnx.py `
  --config stage2_ai_isp/configs/paired_rgb_sidd_tiny_dncnn_l2_2000.yaml `
  --checkpoint stage2_ai_isp/runs/paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth `
  --onnx stage2_ai_isp/deployment/onnx/dncnn_sidd_tiny.onnx `
  --input stage2_ai_isp/datasets/sidd_tiny/test/noisy/pair_00001.png `
  --warmup 5 --repeats 30
```

检查：

```text
stage2_ai_isp/deployment/outputs/onnx_alignment/alignment.json
stage2_ai_isp/deployment/outputs/onnx_alignment/pytorch_output.png
stage2_ai_isp/deployment/outputs/onnx_alignment/onnx_output.png
```

误差定义：

```text
abs_error = abs(y_onnx - y_pytorch)
max_abs   = max(abs_error)
mean_abs  = mean(abs_error)
```

若6个元素的绝对误差是 `[0, 1e-7, 2e-7, 0, 1e-7, 0]`，则最大误差为 `2e-7`，
平均误差约为 `6.67e-8`。当前实测最大误差为 `2.38419e-7`，属于 CPU 浮点算子顺序
造成的约 `1e-7` 级差异。

不要只比较8-bit PNG。PNG 量化可能隐藏小误差，也可能引入新误差；严格对齐使用 float tensor。

## 5. 排错顺序

| 现象 | 优先检查 |
|---|---|
| shape 不匹配 | NCHW/HWC、通道数、动态轴、模型下采样约束 |
| 误差非常大 | `/255`、RGB/BGR、checkpoint、residual 语义 |
| 输出稳定但颜色错误 | 图片解码与通道顺序 |
| 每次结果不同 | `eval()`、随机算子、未冻结预处理 |
| latency 波动大 | warm-up、重复次数、线程、后台负载、是否计入 I/O |

## 6. 本周边界

ONNX/PyTorch 对齐通过只证明导出图和 Python ORT backend 的数值一致性。它不证明：

- C++ 图片 I/O 正确；
- TensorRT/移动端算子全部支持；
- latency、峰值内存和功耗满足量产要求；
- INT8 量化后仍保持质量。

这些问题分别交给 Week 12 和阶段四。

## 7. 练习与验收

1. 分别用128×128和512×512输入验证动态 shape；
2. 故意漏掉 `/255`，记录误差并解释根因；
3. 故意交换 RGB/BGR，比较数值误差和颜色现象；
4. 说明 checker 通过与数值对齐通过的区别；
5. 在自己的新 checkpoint 上重复导出，禁止直接复述已有 JSON。

通过标准：ONNX checker 通过，alignment JSON 与输出图存在，误差在事先声明的阈值内，
并能解释任何未通过项是模型质量问题、数据协议问题还是 backend 问题。
