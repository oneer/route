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

## 14. 从 Stage 2 到部署基线的完整流程

```text
Stage 2 config + checkpoint
  -> 校验文件 hash 和模型结构
  -> 固定 20 张 paired RGB manifest
  -> 解码 uint8 HWC RGB
  -> /255、转 float32、HWC→NCHW
  -> model.eval() + no_grad()
  -> clamp 输出并计算 PSNR/SSIM
  -> 保存 raw evidence、triplet、error map 和 latency
  -> 生成后端共同使用的 model/tensor contract
```

为什么先做这一周：后续任何后端误差都必须与一个不再变化的 reference 比较。若一边换 checkpoint，一边换预处理和 runtime，即使结果变化也无法归因。

## 15. 关键词与参数表

| 参数/关键词 | 当前口径 | 为什么存在 | 变化后的影响 |
|---|---|---|---|
| `max_images=20` | 固定 validation 子集 | 控制每周使用相同输入 | 样本少，结论仅代表该子集 |
| `warmup_runs=3` | 每图不计时预热 | 减少首次初始化影响 | 过少污染 latency，过多只增加运行时间 |
| `timed_runs=10` | 每图正式重复次数 | 估计分布而非单次偶然值 | 必须同时报 p50/p90 和样本组织方式 |
| `device=auto` | 由脚本选择可用设备 | 方便运行，但证据必须记录实际设备 | 不能只从 config 推断是 GPU |
| `clamp_output=true` | 评价/保存前限制到 `[0,1]` | 符合 RGB 输出合同 | 需同时关注 clamp 前越界，避免掩盖异常 |
| model hash | checkpoint/ONNX 的 SHA-256 | 证明各周使用同一资产 | 文件名相同但内容变化时可被发现 |

## 16. Week 0 面试五问

1. **为什么部署前要冻结 baseline？** 为后端比较建立唯一控制变量；模型、输入和预处理不能同时变化。
2. **`eval()` 与 `no_grad()` 各做什么？** 前者切换推理语义，后者关闭梯度记录；二者目的不同。
3. **为什么输出 clamp 不能代替 range 检查？** clamp 会隐藏越界幅度，应先统计原始输出再按合同保存。
4. **为什么 CPU latency 不能推断 GPU/移动端性能？** 算子实现、并行、内存和调度完全不同。
5. **本周 6.4152 dB 增益证明什么？** 只证明冻结模型在该 20 张公开 paired sRGB 子集上优于 noisy input，不证明完整 SIDD、RAW 或量产质量。

## 17. 学习目标、前置知识与停止条件

读完并完成本周后，学习者应能独立完成四件事：从 Stage 2 恢复确定的 checkpoint；把图像严格转换为模型输入 tensor；区分质量评价与性能评价；生成后续所有后端共同使用的冻结证据。前置知识包括 RGB/HWC/NCHW、`uint8`/`float32`、checkpoint、PSNR/SSIM 和训练/推理模式。

本周停止条件不是“脚本能结束”，而是同时满足：manifest 中每个样本可追踪；checkpoint hash 与 model card 一致；输入 tensor 的 shape/dtype/range/color 全部可打印验证；输出没有 NaN/Inf；相同输入重复运行得到相同结果；原始 tensor、可视化和指标能够互相定位。如果其中任一项不成立，不应进入 ONNX 导出。

## 18. 关键公式怎样连接到画面

归一化和布局转换可以写成：

```text
x_nchw[0,c,y,x] = image_rgb[y,x,c] / 255
```

这不是普通的数据整理步骤。遗漏 `/255` 会让输入幅度放大 255 倍；RGB/BGR 交换会让残差网络在错误通道上估计噪声；HWC/NCHW 错位会破坏空间邻域。三类错误都可能保持 shape 合法，因此必须比较 tensor，而不能只依赖 runtime 报错。

本项目使用的 PSNR 定义为：

```text
MSE  = mean((output - clean)^2)
PSNR = 10 log10(MAX^2 / MSE), MAX=1
```

PSNR 提升说明平均平方误差下降，不自动说明纹理、颜色和局部 artifact 都改善；因此还要联合 SSIM、triplet、error map 和最差 crop。`p50` 是一半运行不超过的延迟，`p90` 反映较慢尾部；mean 容易被少量慢样本拉高，三者回答的问题不同。

## 19. 代码调用链与逐步观察点

```text
week0_baseline.yaml
  -> 01_week0_pytorch_baseline.py 解析配置和 manifest
  -> 加载 Stage 2 模型定义与 checkpoint
  -> preprocess: RGB/HWC/u8 -> NCHW/f32/[0,1]
  -> model.eval() / torch.no_grad() / forward
  -> 保存 unclamped 诊断统计，再按合同 clamp
  -> 计算逐样本 quality 与 latency
  -> 写 CSV、图像和 model card
```

建议第一次学习时在四个位置打印信息：解码后图像、模型输入、模型原始输出、评价前输出。每处至少打印 shape、dtype、min/max/mean、是否连续和前三个像素。这样后续 ONNX/C++ 出现差异时，能够找到“第一处发散”，而不是从最终 PNG 倒猜。

## 20. 参数耦合与故障注入实验

| 实验 | 只改变什么 | 预期现象 | 学习目的 |
|---|---|---|---|
| RGB→BGR | 通道顺序 | 颜色和残差结构异常，shape 仍合法 | 理解颜色合同不能由 shape 检查代替 |
| 移除 `/255` | 输入 range | 输出越界或质量严重下降 | 理解模型权重依赖训练时数值尺度 |
| HWC 当 NCHW | layout | 空间/通道混叠 | 理解 stride 与维度语义 |
| 忘记 `eval()` | 推理模式 | 含 BN/Dropout 的模型可能不稳定 | 区分模型语义与梯度开关 |
| 改变 manifest | 评价样本 | 指标改变但不是后端收益 | 理解控制变量与数据冻结 |
| 只看 clamp 后输出 | 诊断位置 | 越界被隐藏 | 理解展示合同与根因诊断的差别 |

这些实验必须一次只改一个变量，并保存修改前后的输入 tensor 摘要、质量指标和一张 error map。若同时改变颜色、layout 和 range，结果无法归因。

## 21. 本周学习验收清单

- [ ] 不看代码画出 Stage 2 checkpoint 到 Week 0 evidence 的完整流程。
- [ ] 能解释 `eval()`、`no_grad()`、clamp、manifest 和 hash 分别保证什么。
- [ ] 能手算一个 `2×2×3` RGB 图像的 HWC→NCHW 索引。
- [ ] 能解释 PSNR、SSIM、mean、p50、p90 的用途和盲区。
- [ ] 能完成至少两项故障注入，并定位第一处错误 tensor。
- [ ] 能使用同一 manifest 重跑并说明哪些结果应确定、哪些 latency 会波动。
- [ ] 能用一句话准确表述证据边界：公开 sRGB 小子集上的 PyTorch CPU 部署 golden，而非 RAW、移动端或量产结论。
