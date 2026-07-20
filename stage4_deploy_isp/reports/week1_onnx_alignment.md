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

## 14. 从 PyTorch 到 ONNX 的完整验证链

```text
恢复冻结 PyTorch 模型
  -> eval() + fixed dummy tensor
  -> export opset 18 fixed-shape graph
  -> 检查 external data 是否齐全
  -> ONNX checker + graph/shape 统计
  -> ORT CPU 加载同一 graph
  -> 对固定 manifest 逐张跑 float tensor
  -> 与 PyTorch 计算 max/mean error 和 quality
```

`checker` 只回答图是否符合 ONNX schema；runtime load 回答当前 ORT 是否能执行；float alignment 才回答语义是否一致。三者不能互相替代。

## 15. 关键词与参数表

| 参数/关键词 | 当前值/含义 | 选择与权衡 | 验证方法 |
|---|---|---|---|
| opset | 18 | 固定算子语义版本；不是越新越快 | 记录 exporter/ORT 版本并实际加载 |
| `dummy_shape` | `1×3×512×512` | 与本阶段 fixed deployment contract 一致 | 输入其他 shape 应明确拒绝或另建模型 |
| `dynamic_axes=false` | batch/H/W 固定 | 首次 TensorRT 构建更简单稳定 | 灵活性低；动态版需 optimization profile |
| constant folding | 导出时折叠可计算常量 | 减少运行时节点 | 仍需对齐，避免 exporter 改变语义 |
| external data | 大 tensor 存在 `.onnx.data` | 绕过单文件大小限制/导出策略 | ONNX 与 data 必须同目录并共同 hash/交付 |
| `max_abs_warn=1e-4` | 项目人工关注阈值 | 宽于当前 `4.17e-7` 浮点差异 | 阈值来自任务误差预算，不是行业标准 |

## 16. Week 1 面试五问

1. ONNX 是模型、图格式还是 runtime？它是中间表示，执行仍依赖 ORT/TensorRT 等 runtime。
2. checker 通过为什么仍可能数值错？layout、range、导出算子语义和预处理都可能错。
3. fixed shape 与 dynamic shape 如何取舍？前者易优化，后者灵活但需要更多 profile/shape 验证。
4. external data 丢失会怎样？图文件存在但权重不完整，加载失败；交付必须把二者视为一个资产。
5. 为什么用 float tensor 而不是 PNG 对齐？8-bit clamp/round 会隐藏小误差或引入量化误差。

## 17. 学习目标、前置知识与停止条件

本周不是“把文件后缀改成 ONNX”，而是证明 **PyTorch 语义被一个可移植计算图完整承接**。开始前应能说清 Week 0 的 RGB/NCHW/float32/`[0,1]` 合同，并能独立恢复 checkpoint。学习顺序是：先看图的输入输出和权重，再确认 runtime 可加载，最后才做逐 tensor 数值对齐。

遇到以下任一条件必须停止进入 C++/TensorRT：输入输出名或 shape 不确定、external data 缺失、checker/runtime load 失败、固定 manifest 的误差超过预算、导出前后预处理不一致。后端越多，错误定位成本越高；Week 1 的意义就是先建立唯一可信的 ONNX golden。

## 18. ONNX 图对象与数值指标

- **graph/node/op**：graph 是有向计算图，node 是一次算子调用，op type 如 `Conv`/`Relu` 定义语义。
- **initializer**：图中的常量 tensor，通常承载卷积权重和 bias；使用 external data 时，数值可能在旁路文件中。
- **opset**：一组算子 schema 版本，不是 runtime 版本，也不承诺更高 opset 更快。
- **shape inference**：传播可推断的 tensor shape；推断成功不等于数值正确。
- **checker/runtime**：checker 检查结构和 schema，runtime 真正分配内存并执行图。

对相同输入的 PyTorch 输出 `y_pt` 与 ONNX 输出 `y_onnx`，至少计算：

```text
max_abs  = max(|y_pt - y_onnx|)
mean_abs = mean(|y_pt - y_onnx|)
RMSE     = sqrt(mean((y_pt - y_onnx)^2))
align_PSNR = 20 log10(data_range / RMSE)
```

`max_abs` 对单点异常最敏感，`mean_abs` 反映整体偏移，RMSE 会放大较大误差。阈值 `1e-4` 是本项目的人工警戒线，必须结合模型输出范围、最终质量变化和最差位置制定；不能把它写成 ONNX 通用标准。

## 19. 代码导航、参数耦合与故障注入

```text
02_export_onnx.py
  -> 读取 Week 0 checkpoint 与 fixed dummy input
  -> torch.onnx.export(opset=18)
  -> onnx.checker / shape / node 统计
03_verify_onnx.py
  -> 同一 manifest 生成同一 float input
  -> 分别执行 PyTorch 与 ORT CPU
  -> 保存逐 tensor 误差、quality 和最差样本
```

| 只改变一项 | 预期结果 | 根因知识 |
|---|---|---|
| 移走 `.onnx.data` | load 失败而非精度下降 | 图结构和权重资产必须共同交付 |
| 改输入名 | `Session::Run` 拒绝 | name 也是 ABI 的一部分 |
| 输入 `256×256` | fixed graph 明确拒绝 | fixed 与 dynamic 的能力边界 |
| 导出时忘记 `eval()` | 可能得到不同训练态语义 | 导出不会自动修正模型状态 |
| 只比较 PNG | 小误差被舍入隐藏 | 对齐层应使用未 clamp 的 float tensor |
| 升级 exporter/ORT | 图或误差可能改变 | 模型 hash 相同不代表工具链行为相同 |

每次导出应把 PyTorch、ONNX、external data、manifest、配置和工具版本视为一组证据资产，记录 hash。修改 opset、shape 或 exporter 后，要从 checker 到 float alignment 完整重跑。

## 20. 本周学习验收清单

- [ ] 能画出 checkpoint、ONNX graph、external data、ORT session 的依赖关系。
- [ ] 能分别解释 checker、shape inference、runtime load 和 float alignment 的职责。
- [ ] 能手算一个小 tensor 的 max/mean/RMSE，并说明为什么要看多个指标。
- [ ] 能找到 graph 的输入输出名、shape、dtype、opset 和主要 op 统计。
- [ ] 能完成 external-data 与 fixed-shape 两项故障注入，并解释错误发生在哪一层。
- [ ] 能说明 `1e-4` 是如何与当前输出范围和质量预算联系起来的。
- [ ] 能准确陈述边界：已证明当前 fixed ONNX 在 ORT CPU 上对齐，未证明 dynamic shape、TensorRT 或移动端。
