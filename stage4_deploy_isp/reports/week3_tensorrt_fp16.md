# Week 3：TensorRT FP32/FP16

## 1. 为什么需要

验证 NVIDIA GPU 上 engine 构建、精度变化和性能收益，同时保持 engine compute 与应用端 session latency 两种口径分离。

## 2. 输入输出协议

与 Week 0 相同的 20 张 fixed-shape RGB NCHW float32 输入；FP16 指 TensorRT 内部低精度优化，输出仍以 float tensor 与 ORT CPU 比较。

## 3. 链路角色

`trtexec` 负责 parser/build/engine benchmark；ORT CUDA EP 和 TensorRT EP 负责在真实固定输入上做 correctness 与 host session timing。

## 4. 核心概念/API

ONNX parser → builder → engine → execution context；fixed shape 本次不需 optimization profile。stream、H2D/D2H 和同步决定实际 latency；engine 与 TensorRT/CUDA/GPU 架构绑定。

## 5. 对应文件

- `scripts/09_week3_trt_cuda_benchmark.py`
- `outputs/week3_backend/*.plan`
- `outputs/week3_backend/week3_trtexec_*.log`
- `outputs/week3_backend/fp16_error_maps/`
- `outputs/week3_backend/fp16_failure_cases/`

## 6. 运行命令与环境

```powershell
C:\Users\10439\.conda\envs\stage4-cuda\python.exe `
  stage4_deploy_isp/scripts/09_week3_trt_cuda_benchmark.py --runs 5
```

实测环境：RTX 4060 Ti、driver 591.74、CUDA 12.6、TensorRT 10.8.0、ORT GPU 1.21.1。

## 7. 正确输出

FP32/FP16 plan、构建日志、每次 H2D/compute/D2H JSON、20×3 backend 对齐 CSV、最差 3 张 FP16 comparison/error map。

## 8. 对齐指标与阈值

| Backend | max error vs ORT CPU | quality PSNR | quality SSIM |
|---|---:|---:|---:|
| CUDA FP32 | `3.58e-7` | `32.98387` | `0.9847913` |
| TensorRT FP32 | `5.29e-4` | `32.98247` | `0.9847891` |
| TensorRT FP16 | `1.47e-3` | `32.98200` | `0.9847886` |

FP16 平均质量 PSNR 相对 ORT CPU 仅下降约 `0.00187 dB`，低于项目 warning `0.1 dB`；阈值是项目标准，不是行业统一标准。

## 9. 常见失败与排查

DLL/版本 → ONNX external data → parser → fixed/dynamic shape/profile → provider fallback → 非有限值 → 同步与计时。必须记录 `session.get_providers()`，但 provider 列表本身仍不能证明每个节点都未 fallback。

## 10. 性能测量

| 口径 | FP32 | FP16 |
|---|---:|---:|
| `trtexec` compute mean | `1.968 ms` | `0.979 ms` |
| `trtexec` H2D mean | `1.986 ms` | `2.004 ms` |
| `trtexec` D2H mean | `2.163 ms` | `2.323 ms` |
| `trtexec` latency mean | `6.118 ms` | `5.306 ms` |
| ORT TensorRT EP session mean | `7.886 ms` | `7.458 ms` |

`trtexec` warmup 200 ms、duration 3 s；ORT 每图 warmup 5、runs 5。两行不能混成同一“推理时间”。

## 11. Tradeoff

FP16 compute 接近减半，但 copy 和 host/runtime 开销限制 session 收益；画质损失很小，显存分配日志显示 FP16 execution context 较小，但这不是完整峰值显存报告。

## 12. 证据边界

engine 只对记录环境负责；没有 C++ TensorRT runner、dynamic profile、功耗、Nsight timeline 或跨 GPU 复验。

## 13. 练习与掌握标准

解释为何 compute `0.979 ms` 而 session `7.458 ms`；移动同步点制造虚假 latency；检查最差 FP16 crop 后给出是否接受的结论。

## 14. Engine 构建与执行流程

```text
ONNX + external weights
  -> TensorRT parser
  -> builder 选择 tactic 与 precision
  -> 序列化 FP32/FP16 plan
  -> execution context + CUDA stream
  -> H2D input
  -> enqueue compute
  -> D2H output + synchronize
  -> 与 ORT CPU 做 float/quality 对齐
```

plan 不是通用模型文件：它与 TensorRT/CUDA、GPU 架构、shape 和构建设置强绑定。缓存 plan 前必须保存完整环境和源 ONNX hash。

## 15. 关键词与参数表

| 关键词/参数 | 含义 | 性能/正确性影响 | 验证 |
|---|---|---|---|
| tactic | TensorRT 为某层选择的具体 kernel 实现 | 决定速度、workspace 和数值路径 | 构建日志、相同环境复验 |
| FP16 | 允许部分计算/存储使用半精度 | 提高吞吐、减小部分内存，也引入舍入 | float error、PSNR/SSIM、最差 crop |
| workspace | builder 可用于 tactic 的临时内存预算 | 更大可能允许更快 tactic | 不是运行时总峰值显存 |
| optimization profile | dynamic shape 的 min/opt/max 范围 | 决定可接受 shape 和优化点 | 本次 fixed shape 不需要，不能声称已验证 |
| stream/sync | GPU 操作队列与完成屏障 | 同步位置错误会测到排队而非执行 | CUDA event/明确同步与 host timing 对照 |
| compute/session/e2e | kernel 图执行 / API 调用 / 完整业务链 | 数值范围不同，不能混表 | 分阶段计时并声明 I/O/copy |

## 16. Week 3 面试五问

1. 为什么 FP16 compute 近乎减半，ORT session 只小幅改善？copy、runtime 和 host 开销未同步缩小。
2. TensorRT plan 为什么不能跨 GPU/版本直接分发？tactic 和序列化 ABI 与环境绑定。
3. provider 列表里有 TensorRT 为什么仍要警惕 fallback？它不证明每个节点都由目标 EP 执行。
4. FP16 是否可接受应看什么？质量 drop、最大误差、最差 ROI、稳定性和目标预算，不只看平均 PSNR。
5. 怎样避免异步 GPU timing 假快？在正确 stream 上用 event 或明确同步，记录计时边界。

## 17. FP16 数值背景与验收逻辑

IEEE FP16 使用 1 个符号位、5 个指数位和 10 个显式尾数位；相较 FP32，它的可表示范围与有效精度更小。把权重/激活舍入到 FP16 会引入局部误差，卷积累加是否使用更高精度还取决于 kernel 和硬件路径。因此“启用 FP16”不是每个节点、每次累加都严格半精度的同义词，最终必须从 engine 日志和输出误差验证。

当前 `max abs=1.47e-3`、平均 PSNR 下降约 `0.00187 dB` 说明在这 20 张公开 sRGB 样本和当前任务门槛下变化很小；它不证明所有暗部、极值、其他 shape 或 GPU 都安全。验收顺序应是：图执行无 fallback → float tensor 误差 → 同一 manifest 质量 → 最差 ROI → 稳定性和性能。

## 18. 延迟分解与为什么 kernel 快不等于业务快

```text
T_e2e = T_decode + T_pre + T_H2D + T_compute + T_D2H + T_post + T_encode
T_session ≈ T_binding/runtime + T_H2D + T_compute + T_D2H + T_sync
```

FP16 把 `trtexec` compute 从约 `1.968 ms` 降到 `0.979 ms`，只缩短了 `T_compute`；copy、runtime、同步和 host 部分没有同比缩小，所以 ORT session 仅从约 `7.886 ms` 到 `7.458 ms`。这就是 Amdahl 定律在部署中的表现：某一小段即便无限加速，整体收益仍受其余比例限制。

必须区分 CUDA event 测得的 stream 区间与 host timer。没有同步的 host timer 常只测到 enqueue；把同步放进循环的错误位置又可能把前一轮工作算到下一轮。报告应同时写清 warmup、stream、event、同步点和数据驻留位置。

## 19. Engine 生命周期、代码导航与故障注入

```text
ONNX hash + builder config + TensorRT/CUDA/GPU 环境
  -> parse graph
  -> 设置 precision/workspace/shape profile
  -> builder 搜索 tactic
  -> serialize plan
  -> runtime deserialize
  -> execution context 绑定地址/shape/stream
  -> enqueue -> sync -> validate output
```

| 实验 | 预期现象 | 判断重点 |
|---|---|---|
| 不做 warmup | 首轮显著更慢 | context/tactic/cache 初始化不可混入 steady-state |
| 去掉同步 | host latency 虚低 | enqueue 完成不等于 GPU 完成 |
| 只查看 provider 名 | 可能遗漏节点 fallback | 需看实际 graph partition/日志 |
| 在另一 GPU/版本加载 plan | 失败或不可复现 | plan 是环境相关缓存，不是通用交换格式 |
| 只看平均 PSNR | 局部 artifact 被平均 | 同看 max error、最差样本与 ROI |
| 把 workspace 当峰值显存 | 内存结论错误 | builder 临时预算不等于运行时总占用 |

首次学习应分别保留：源 ONNX hash、build 命令和日志、plan hash、环境矩阵、逐样本对齐 CSV 与延迟 CSV。任一构建参数改变都要重新生成 plan 并重跑 correctness。

## 20. 本周学习验收清单

- [ ] 能解释 FP16 的精度/范围限制及其为何可能加速 Tensor Core 路径。
- [ ] 能画出 build-time 与 runtime 生命周期，并指出 plan 依赖哪些环境信息。
- [ ] 能用延迟分解解释 compute 加速与 session 加速不一致。
- [ ] 能设计同步位置实验，识别一次异步 timing 假快。
- [ ] 能检查 fallback、最差 ROI 和 engine/build 日志，而非只看 provider 和均值。
- [ ] 能说明 workspace、execution context 内存与进程峰值显存不是同一个量。
- [ ] 能准确陈述边界：RTX 4060 Ti fixed-shape 桌面证据，不是 C++ TRT runner、移动端或跨平台结论。
