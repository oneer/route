# Week 11：ONNX 导出与 PyTorch/ONNX 对齐

Week 11 的目标不是“得到一个 `.onnx` 文件”，而是证明冻结模型在新的执行后端中接收相同
张量，并产生数值一致的输出。只有文件，没有 checker 和对齐结果，不算完成。

## 1. 输入、处理与输出

```text
输入：Week 10 冻结的 config、checkpoint 和固定 RGB 图片
处理：构建 eval 模型 -> 导出 ONNX -> checker -> ONNX Runtime CPU 推理 -> float 对齐
输出：ONNX、alignment.json、两端输出图和 latency 记录
```

Week 10 提供冻结 checkpoint 和 tensor contract，本周输出后端无关的 ONNX 图及 Python ORT
参考证据，交给 Week 12 C++。ONNX 是算子图交换格式，不会自动携带项目中所有图片解码、
颜色、归一化和后处理语义；这些必须由合同明确。

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

## 8. ONNX 关键词与参数表

| 关键词/参数 | 定义 | 当前选择理由 | 验证方式 |
|---|---|---|---|
| opset 17 | ONNX 算子语义版本 | 当前导出器/ORT 支持的明确协议 | checker + 实际 ORT 推理；不是越新越快 |
| dummy input | tracing/export 时的示例 tensor | 提供 shape 和 dtype | 不代表动态 shape 一定可运行 |
| dynamic axes | batch/height/width 可变声明 | 全卷积模型希望支持不同空间尺寸 | 至少用 128 与 512 实测 |
| graph checker | 检查图结构与 schema 合法性 | 先排除格式错误 | 通过不等于数值对齐 |
| max/mean abs error | 后端输出逐元素绝对误差统计 | 捕捉局部最大偏差与整体偏差 | 对原始 float tensor，不比较 PNG |
| warm-up/repeats | 不计时预热 / 正式重复次数 | 避免一次性初始化污染 latency | 同时报告设备、线程、shape 和 I/O 范围 |

## 9. Week 11 面试五问

1. ONNX checker 通过与 PyTorch/ORT 数值对齐通过有什么区别？
2. opset 是什么，为什么不是数字越大性能越好？
3. 声明 dynamic axes 后为什么仍必须实测不同尺寸？
4. 为什么 8-bit PNG 不适合作为严格后端对齐证据？
5. max error 很大时，你如何依次排查 RGB/BGR、range、layout、checkpoint 和算子差异？

## 10. 本周执行流程速记

```text
frozen checkpoint -> eval model -> dummy tensor -> ONNX export
-> checker -> ORT load -> same float input -> raw tensor alignment
-> output image/JSON -> handoff to C++
```

## 11. 参数方向、耦合与工程取舍

| 参数/概念 | 改变后的影响 | 与什么耦合 | 常见失败 |
|---|---|---|---|
| opset | 改变算子语义/可用算子集合，不保证更快 | exporter、ORT/目标 backend 版本 | checker 或目标端不支持 |
| dynamic H/W | 一个图可接多尺寸 | 模型 stride、reshape、目标 backend 优化 | 声明成功但某尺寸运行失败 |
| dummy H/W | 决定跟踪示例和可能的常量折叠路径 | dynamic axes 与模型控制流 | 被误当成唯一可运行尺寸 |
| tolerance | 决定对齐是否通过 | dtype、backend、输出量级 | 太松掩盖 bug，太严拒绝正常舍入 |
| warm-up/repeats | 影响 latency 稳定性与统计成本 | 线程、shape、缓存、后台负载 | 首轮初始化污染均值 |

工程权衡包括：动态 shape 提高复用性，却可能减少编译器针对固定尺寸的优化；opset 提高兼容能力与新算子
表达，但目标平台支持可能滞后。阈值必须在看结果前声明，并同时记录 max 和 mean：max 捕捉
局部异常，mean 描述整体偏差。

## 12. 从零调试实验与证据边界

推荐故障注入顺序：①漏 `/255`；②RGB/BGR互换；③NCHW/HWC误传；④加载错误 checkpoint；
⑤用不满足 stride 的尺寸。每次保存输入 tensor、两端 raw output、误差统计和修复后回归。
若 checker 通过但误差大，优先比较进入两后端的**同一 float tensor**，而不是先怀疑 ONNX。

本周证据为 `verified_partial`：冻结 DnCNN 在 Python ORT CPU 上完成图合法性和数值对齐。
它不证明 C++ 图片 I/O、GPU/HTP/NPU、INT8、峰值内存、功耗或生产稳定性。

学习者独立验收：用128与512尺寸复验；解释一个 max/mean 冲突样例；画出 config→model
factory→export→checker→ORT→alignment JSON 的调用链；用自己的 checkpoint 重复一次，不能
仅引用现有 `2.38419e-7`。
