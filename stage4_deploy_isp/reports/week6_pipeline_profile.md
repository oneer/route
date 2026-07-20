# Week 6：CUDA 前处理、Device Tensor 与 Pipeline Profile

## 1. 本周从什么问题开始

前五周已经证明模型能在 PyTorch、ONNX Runtime、TensorRT 和 INT8 路径中运行，但“某个 kernel 很快”不等于“Camera pipeline 很快”。完整链路至少包含：

```text
文件/Camera buffer
  -> CPU decode
  -> preprocess
  -> H2D
  -> GPU inference
  -> postprocess
  -> D2H/显示/保存
```

如果只测中间 `0.009 ms` 的 normalize kernel，而忽略两次 copy、runtime 调度和后处理，就会得到错误优化结论。本周目标是把 host/device 边界画清楚、逐段计时、验证 tensor 是否留在设备端，并用质量、延迟、RAM/VRAM 和拷贝次数共同做决策。

## 2. 两代实验为什么都要保留

本周保留两条互补证据：

1. **独立 CUDA normalize baseline**：证明自定义 uint8 HWC → float32 NCHW kernel 数值正确，并暴露 pageable H2D/D2H 远大于 kernel 的问题；
2. **ORT CUDA I/O Binding pipeline**：输入和输出都绑定为 CUDA OrtValue，消除 inference 中间 D2H，只在开始做一次 H2D、结束做一次最终 D2H。

它们还没有完全连接：当前 I/O Binding 输入仍由 CPU NumPy preprocess 生成，再复制到 GPU；已有自定义 CUDA normalize 的 device pointer 尚未直接绑定给 ORT。因此状态是 `verified_partial`，不是完整 GPU preprocess direct pipeline。

## 3. 输入输出合同

### 3.1 当前 RGB 模型

```text
source       : RGB uint8 HWC, [0,255]
model input  : float32 NCHW, [0,1], [1,3,512,512]
model output : float32 NCHW, nominal [0,1]
quality view : clamp [0,1], HWC RGB
```

### 3.2 不应接入的 RAW kernel

`pack_raw.cu` 面向未来 Bayer RGGB pack，语义是二维 CFA → 4-channel RAW-like tensor。当前 DnCNN 是 3-channel RGB 模型，不能因为 shape 都是 tensor 就把 RAW pack 接入；layout、通道语义、数值范围和训练数据全部不匹配。

## 4. Host、Device 与拷贝边界

### 4.1 旧 baseline

```text
pageable uint8 host
  -> H2D
  -> CUDA normalize
  -> D2H float tensor
  -> host 消费
```

这条链有一次 H2D 和一次 D2H，但没有接 GPU inference。它适合证明 kernel/copy 构成，不适合声称完整推理加速。

### 4.2 当前 I/O Binding

```text
CPU NumPy preprocess
  -> one H2D: CUDA input OrtValue
  -> ORT CUDA inference
  -> CUDA output OrtValue
  -> zero intermediate D2H
  -> one final D2H: quality/output consumption
```

关键改进是 inference 输入/输出都在 device 上；关键未完成项是 preprocess 仍在 CPU。

### 4.3 目标 direct path

```text
pinned host RGB
  -> async H2D on shared stream
  -> custom CUDA preprocess into reusable device buffer
  -> bind the same device pointer/stream to ORT input
  -> inference device output
  -> downstream GPU consumer or one final D2H
```

目标路径要求 pointer、shape、dtype、stream ownership 和 buffer lifetime 全部显式。少一个合同都可能产生隐式 copy、竞态或悬空指针。

## 5. 核心关键词与参数

| 关键词/参数 | 定义 | 为什么存在 | 调节/误用后的影响 |
|---|---|---|---|
| H2D / D2H | Host-to-Device / Device-to-Host copy | CPU 与 GPU 是不同内存域 | copy 次数和字节量可能主导短 kernel |
| pageable memory | 普通可分页 host 内存 | 分配方便 | async copy 可能需要驱动 staging，吞吐/重叠受限 |
| pinned memory | 页锁定 host 内存 | 支持更稳定的 DMA 和 async copy | 过量使用会压缩系统可分页内存；必须实测 |
| CUDA stream | 有序提交 GPU 操作的队列 | 支持依赖表达与重叠 | 不同 stream 未同步会读到未完成数据 |
| CUDA Event | 记录同一 device timeline 上的时间点 | 比 host clock 更适合测异步 GPU 区间 | 仍需在正确 stream 上记录并等待完成 |
| I/O Binding | 把 ORT 输入/输出绑定到指定内存位置 | 避免 runtime 自动搬回 host | 只绑定 output 不代表 input/preprocess 无 copy |
| device OrtValue | 位于 CUDA device 的 ORT tensor | 允许 `Session::run_with_iobinding` 直接消费 | shape/dtype/device id 必须与模型一致 |
| warm-up 5 | 不计入统计的预热次数 | 排除首次初始化/cache 影响 | 不能用 warm-up 结果冒充正式样本 |
| timed runs 20 | 正式重复次数 | 得到 p50/p90 分布 | 样本量仍有限，需记录系统负载 |
| p50 / p90 | 中位数 / 90 分位 latency | 描述典型和尾部行为 | 不说明样本、同步、范围时不可比较 |
| peak RAM/VRAM | 进程主存/显存峰值 | 质量与 latency 之外的资源约束 | snapshot 不等于连续 profiler peak；空值不可猜 |

## 6. CUDA normalize 索引为什么这样写

输入是 HWC，输出是 NCHW。对一个线性 thread index：

```text
pixel = index / channels
c     = index % channels
y     = pixel / width
x     = pixel % width

input_index  = (y * width + x) * channels + c
output_index = c * height * width + y * width + x
output       = input / 255.0f
```

HWC 输入能让同一像素的 RGB 连续读取；NCHW 写入跨 channel plane。这个 kernel 主要用于教学和合同验证，是否是最终最优 layout transform 还要看 vectorized load、融合算子、目标 backend 和下游访问模式。

grid 计算使用向上取整：

```text
blocks = (total_elements + threads_per_block - 1) / threads_per_block
```

kernel 内必须检查 `index < total_elements`，否则 512×512×3 之外的尾线程会越界。不能只测试恰好整除 block size 的尺寸。

## 7. 对应实现与证据

- `cuda_kernels/normalize.cu`：normalize kernel；
- `cpp/include/cuda_preprocess.hpp`、`cpp/src/cuda_preprocess_benchmark.cpp`：pinned/pageable、stream、CUDA Event 计时实现；
- `cpp/include/device_pipeline.hpp`、`cpp/src/device_pipeline.cpp`：device pipeline 拷贝/绑定合同；
- `cpp/tests/test_device_pipeline.cpp`：拒绝 intermediate D2H 等合同测试；
- `scripts/10_week6_cuda_preprocess_benchmark.py`：旧 NVRTC pageable baseline；
- `scripts/13_profile_device_pipeline.py`：ORT CUDA I/O Binding 实测；
- `scripts/14_generate_quality_latency_memory_matrix.py`：质量/延迟/内存/拷贝矩阵；
- `outputs/week6_pipeline/week6_cuda_preprocess_summary.csv`：旧 baseline 证据；
- `outputs/device_pipeline/device_pipeline_profile.csv`：新 device pipeline 证据；
- `outputs/device_pipeline/quality_latency_memory_matrix.csv`：跨后端 trade-off。

## 8. 复现顺序

先跑 CPU-safe 合同和矩阵生成：

```powershell
$env:PYTHONPATH="stage4_deploy_isp"
python -m unittest discover -s stage4_deploy_isp/tests -v
python stage4_deploy_isp/scripts/14_generate_quality_latency_memory_matrix.py
```

在已安装 ORT CUDA、CUDA/cuDNN/TensorRT DLL 且 provider 可加载的 Python 环境中运行：

```powershell
<cuda-python> stage4_deploy_isp/scripts/13_profile_device_pipeline.py
```

脚本必须拒绝 CPU provider fallback；不能因为 API 调用成功就写成 GPU 结果。运行后检查 environment JSON、provider、device tensor 标记、copy count 和 CPU correctness 对齐。

## 9. 正确性验收

### 9.1 独立 CUDA normalize

相对 CPU normalize：

| 指标 | 结果 |
|---|---:|
| max absolute error | `5.96e-8` |
| mean absolute error | `8.22e-9` |
| 项目阈值 | `1e-6` |

这证明 HWC→NCHW 和 `/255` 的 kernel 数值对齐，不证明它已经接入 inference。

### 9.2 ORT CUDA I/O Binding

相对 ORT CPU：

| 指标 | 结果 |
|---|---:|
| max absolute error | `2.682e-7` |
| mean absolute error | `2.149e-8` |
| mean quality PSNR | `32.983963 dB` |
| CPU reference PSNR | `32.983963 dB` |

质量一致只说明 backend 数值没有实质改变；它不自动证明所有场景、FP16/INT8 或移动端同样一致。

## 10. 性能结果怎样读

### 10.1 旧 CUDA normalize baseline

| 阶段 | mean latency |
|---|---:|
| CPU normalize | `2.498 ms` |
| pageable H2D | `1.082 ms` |
| CUDA kernel | `0.0091 ms` |
| pageable D2H | `2.707 ms` |
| GPU stage E2E | `3.798 ms` |

结论：kernel 比 CPU 算子快，但 H2D+D2H 使整个 GPU stage 更慢。继续把 kernel 从 `0.0091` 优化到 `0.006` 几乎不会改变 `3.798 ms` 的系统结论。

### 10.2 ORT CUDA I/O Binding pipeline

测试：10 张 evaluation 图片、5 次 warm-up、20 次正式计时、RTX 4060 Ti、FP32、文件 I/O 不计入。

| 阶段/指标 | 结果 |
|---|---:|
| CPU NumPy preprocess mean | `2.396 ms` |
| H2D mean | `2.272 ms` |
| inference mean | `3.381 ms` |
| inference p50/p90 | `3.296 / 3.754 ms` |
| final D2H mean | `2.453 ms` |
| host-to-final-host E2E mean | `10.554 ms` |
| E2E p50/p90 | `10.477 / 11.047 ms` |
| sampled process peak RAM | `614.61 MiB` |
| per-process VRAM | 空值，WDDM/nvidia-smi 未暴露 |

拷贝合同：

```text
1 H2D / 0 intermediate D2H / 1 final D2H
device input = true
device output = true
device preprocess = false
```

## 11. 为什么这次优化有效、又为什么还不完整

有效点：输出不再在 inference 中间回到 host，输入/输出是 device OrtValue，推理 p50/p90 和完整 host-to-final-host 路径有独立口径。

未完成点：CPU preprocess 后仍有一次 H2D；最终为了质量评价仍有一次 D2H；自定义 CUDA preprocess 的 pointer 和 stream 没有直接绑定给 ORT。若下游也是 GPU 显示/编码/算法，最终 D2H 也可能被推迟或消除，但必须在真实消费者链路中验证。

## 12. Pinned memory、stream overlap 为什么还不能写成收益

C++ 路径已经实现 pinned/pageable、stream 与 CUDA Event 的对照代码和静态/合同测试，但当前 CUDA 12.6 与已安装 VS 2026 host compiler 不兼容，未发布可信的可执行实测行。

因此可以写：

> 已实现并测试接口合同，待兼容 CUDA toolchain 上测量。

不能写：

> pinned memory 已带来 X% 加速。

同理，没有 Nsight Systems timeline 就不能声称 copy 与 compute 已成功 overlap；源码中使用异步 API 只是必要条件，不是时间线证据。

## 13. 常见失败与第一排查顺序

| 现象 | 第一检查 | 原因 |
|---|---|---|
| provider 静默回到 CPU | `get_providers()`、provider load 日志并强制拒绝 fallback | CUDA/cuDNN/TensorRT DLL 或版本问题 |
| max error 很大 | RGB/BGR、HWC/NCHW、`/255`、shape | 多数是 tensor contract，不是 GPU 精度 |
| kernel 时间异常小 | 是否在同一 stream 上 event/sync | 异步 launch 只测到提交时间 |
| I/O Binding 仍发生中间 D2H | output binding 和消费路径 | 只绑定 input 或调用 `.numpy()` 会触发 copy |
| H2D 很慢 | host memory 类型、字节量、首次 context、同步边界 | pageable staging 或计时混入初始化 |
| 多 stream 结果不稳定 | event/stream dependency 和 buffer reuse | 下游可能在上游完成前读数据 |
| VRAM 为空 | WDDM/工具是否暴露 per-process 指标 | 空值应保留，不用总显存猜峰值 |

## 14. 质量、延迟、内存与拷贝的决策规则

任何“更快 backend”至少回答四个问题：

1. quality 是否在同一 frozen evaluation 上通过；
2. latency 是 compute、session 还是 e2e，p50/p90 如何；
3. peak RAM/VRAM 是否真实测量，空值是否明确；
4. H2D/D2H 次数和中间 tensor 所在设备是什么。

只满足第一和第二项时应标为 `verified_partial`。桌面 RTX 结果也不能改写成 Snapdragon/NPU、移动功耗或实时 Camera pipeline 结论。

## 15. Week 6 面试五问与参考回答

1. **为什么 `0.0091 ms` kernel 没带来端到端加速？** 因为 pageable H2D+D2H 共约 `3.789 ms`，远大于 kernel；系统瓶颈在数据移动和边界，不在算术。
2. **I/O Binding 解决了什么？** 它让 ORT 输入/输出驻留在指定 device memory，当前消除了 intermediate D2H；但 CPU preprocess→H2D 仍存在。
3. **Pinned memory 一定更快吗？** 不一定。它改善 DMA/async copy 条件，但分配、系统内存压力、传输大小和 pipeline 是否能 overlap 都会影响收益，必须实测。
4. **CUDA Event 与 host timer 有何区别？** Event 在 device stream timeline 上测 GPU 区间；host timer 易只测到异步提交。完整 e2e 仍需 host 视角并明确同步。
5. **下一步最值得优化哪里？** 先把 custom preprocess device buffer/stream 直接绑定给 ORT，验证无隐式 copy；再用 Nsight 检查 timeline，最后才考虑微调 kernel。

## 16. 本周动手练习

1. 故意删除 kernel 的尾部边界判断，用非整除尺寸验证失败；
2. 把 HWC/NCHW index 交换，比较 max error 和可视化症状；
3. 在 output OrtValue 上提前调用 host conversion，确认 copy count/时间变化；
4. 在兼容工具链上运行 pageable vs pinned，记录字节量、p50/p90 和 correctness；
5. 画出当前、目标 direct path 两张 host/device 图，并标出每个 buffer owner 和 stream。

## 17. 证据边界与下一阶段

已验证：独立 CUDA normalize correctness、ORT CUDA device input/output、零 intermediate D2H、质量对齐、分阶段 p50/p90、RAM snapshot 和拷贝合同。

仍为 `not_run`：custom CUDA preprocess pointer 直绑 ORT、Nsight timeline、可信 per-process VRAM peak、pinned/pageable 实测收益、Snapdragon/NPU、移动端功耗和完整 Camera buffer pipeline。

完成标准：学习者能从业务输入画出 host/device 数据流，解释每个 latency 数字属于哪个边界，指出当前最贵的数据移动，并且不会把局部 kernel、桌面 GPU 或接口实现包装成端侧量产成果。

## 18. 学习地图与前置知识

Week 6 把前五周串成一个系统问题：模型正确并不等于数据路径正确，kernel 快也不等于 pipeline 快。开始前应能独立解释 Week 0 tensor contract、Week 1 ONNX 对齐、Week 2 buffer ownership、Week 3 GPU timing、Week 4 精度预算。若这些概念不稳，应回到对应报告完成 checklist，而不是直接看 profiler 数字。

本周的核心问题只有三个：数据现在位于 host 还是 device、谁拥有它、跨边界发生了几次同步和复制。每一个 latency 数字都必须绑定一段明确的数据流。

## 19. 字节量、带宽与整体收益公式

`512×512×3` 的 float32 tensor 大小为：

```text
bytes = H * W * C * sizeof(float)
      = 512 * 512 * 3 * 4
      = 3,145,728 bytes ≈ 3 MiB
effective_bandwidth = transferred_bytes / transfer_time
```

一次 H2D 加一次 D2H 至少移动约 6 MiB 的显式 tensor 数据，还未计算输入 u8、对齐、allocator staging 和其他中间量。整体优化的 speedup 应从同一边界计算：

```text
speedup = T_old_same_boundary / T_new_same_boundary
T_e2e = T_pre + T_H2D + T_runtime + T_compute + T_D2H + T_post
```

不能用旧的 e2e 除以新的 kernel，也不能把理论 PCIe 带宽直接当有效带宽。小传输常受固定调用、pageable staging 和同步开销支配。

## 20. 当前路径、目标路径与代码导航

```text
当前已验证路径
NumPy CPU preprocess
  -> ORT I/O Binding 分配/绑定 CUDA input
  -> 一次 H2D
  -> ORT CUDA graph，在 device 保持中间 tensor
  -> 绑定 CUDA output
  -> 一次最终 D2H

目标但尚未验证的 direct path
camera/device buffer
  -> custom CUDA preprocess 写 device tensor
  -> 同一 pointer/stream 交给 ORT
  -> device-side downstream consumer
```

独立 `normalize.cu` benchmark 只证明 kernel correctness 和局部计时；`13_profile_gpu_pipeline.py` 证明当前 Python/ORT I/O Binding 的 buffer/拷贝合同。两者尚未连接成“custom CUDA 输出 pointer 直接喂 ORT”的单一 C++ pipeline，因此必须保持 `not_run`。实现该连接时应核对 pointer、shape、dtype、device id、stream dependency 和 buffer lifetime 六项。

## 21. 参数耦合与调试实验

| 参数/动作 | 耦合对象 | 失败表现 | 证明方法 |
|---|---|---|---|
| pageable→pinned | allocator、DMA、系统内存 | 不一定提速，可能增加内存压力 | 同字节量/同边界 p50/p90 实测 |
| 改 stream | producer/ORT/consumer event | 数据竞争或隐式同步 | timeline + correctness 重复跑 |
| 提前 `.numpy()` | output residency | 插入 D2H | copy count 与 trace |
| 复用 device buffer | lifetime、in-flight request | 前后帧覆盖 | event dependency 与多帧校验 |
| 改 input shape | allocation、binding、engine profile | 拒绝或重分配 | metadata/profile 与日志 |
| 只优化 normalize kernel | copy/runtime 占比 | kernel 更快但 e2e 不变 | 同边界前后分解表 |

建议按一次只改一项的顺序完成：提前 host conversion、pageable/pinned、单/双 buffer、单/多 stream、direct binding。每次同时记录 correctness、copy count、p50/p90 和内存，不接受只有一张 profiler 截图的结论。

## 22. 四阶段闭环与本周验收清单

```text
Stage 1 算法与数据合同
  -> Stage 2 学习模型与评测合同
  -> Stage 3 C++/内存/性能工程
  -> Stage 4 图转换、后端、精度与端到端证据
```

- [ ] 能手算 tensor 字节量与有效带宽，并核对 profiler 数量级。
- [ ] 能画出当前和目标路径，标出 owner、memory domain、copy、stream 和同步点。
- [ ] 能区分 kernel、compute、session 与 e2e speedup，保证分子分母边界相同。
- [ ] 能解释 I/O Binding 已解决和未解决的问题。
- [ ] 能完成至少两项调试实验，并用 copy count 与 correctness 支撑结论。
- [ ] 能指出 `normalize.cu` 与 Python I/O Binding 尚未连成 direct pipeline 的证据缺口。
- [ ] 能从 Stage 1 讲到 Stage 4，说明每个阶段给下一阶段冻结了什么合同和证据。

## 23. 高通岗位补强：实时 deadline、队列与 PPA

Camera 系统优化不只问单次 inference latency，还问持续 throughput、尾延迟、队列、功耗、温度和内存带宽。当前桌面数据能训练分析方法，不能替代 Snapdragon PPA。

### 23.1 Latency、throughput 与 frame deadline

30 fps 的 frame period 为：

```text
T_frame = 1000 / 30 ≈ 33.3 ms
```

它不是每个节点各自拥有的预算。capture、ISP、ML feature、后处理和下游会共享或并行使用时间，且可能同时存在多个 in-flight request。系统至少验证：

```text
throughput >= target_fps
e2e latency <= product budget
deadline_miss_rate <= allowed rate
queue_depth stays bounded
```

若平均 service time 接近或大于到达间隔，queue 会积累，输出越来越旧；即使 p50 达标，p90/p99 或偶发同步也可能造成掉帧。实时策略需要明确 backpressure：丢旧帧、跳过 feature、降低质量、切换 backend，还是阻塞上游。选择取决于预览、拍照、视频等 use case，不能只有一个通用答案。

### 23.2 内存带宽和 copy 预算

除显式 tensor 外，还应估算每帧所有 plane、alignment padding、中间 buffer 和重复读写：

```text
bandwidth_demand ≈ sum(bytes_read + bytes_written) * fps
```

`512×512×3×4` 只是一个约 3 MiB tensor；真实高分辨率 YUV/RAW、多曝光、多摄和多 stage 会显著放大带宽。减少 FLOPs 不一定降低功耗，如果算法增加了大中间 tensor 或跨 DDR 往返。profiling 应把 compute-unit utilization 与 memory/copy timeline 联合解释。

### 23.3 功耗、能量和温度怎样测

一个最低限度的比较协议是同一设备、亮度/网络/后台负载/温度区间，先测 idle/baseline，再对稳定运行区间重复采样：

```text
dynamic_power ≈ P_active - P_idle
energy_per_frame ≈ dynamic_power / achieved_fps
```

报告必须写采样来源、频率、窗口、warmup、环境温度、SoC/battery 状态和方差。短 benchmark 可能处在 boost，不能代表 thermal steady-state；功耗下降但 fps 同时下降时，应比较 energy/frame 和业务 deadline，而非只报瓦数。

桌面板卡功率、整机插座功率和移动 SoC rail/battery 功率的边界不同。当前仓库没有稳定移动功耗实测，因此 `power` 保持空值。芯片 **area** 也无法由软件项目测量；只能讨论选择 ISP/GPU/HTP、SRAM/DDR、precision 和算子复杂度对硬件资源的设计影响，不能输出面积数字。

### 23.4 PPA 决策表

| 方案 | 可能收益 | 可能代价 | 必须验证 |
|---|---|---|---|
| FP16/INT8 | 更高吞吐、较小带宽/资产 | 量化误差、conversion、算子限制 | per-scene/worst quality、实际 kernel/partition |
| CPU→GPU/HTP | 并行 compute | launch/partition/copy、共享资源、功耗 | e2e、copy、utilization、thermal |
| buffer reuse/pool | 降低 allocation 和抖动 | lifetime/并发覆盖风险 | 多 request correctness、RSS/peak |
| multi-stream/async | overlap copy/compute | dependency 复杂、峰值内存增加 | timeline、race、p90/p99 |
| 降分辨率/tile | 降 compute/带宽 | 细节、halo、tile seam | ROI IQ 与边界测试 |
| feature fallback | 保住 deadline/稳定性 | 质量/风格切换 | gate、hysteresis、用户可见跳变 |

### 23.5 面试故障题

1. p50 为 `10 ms` 但仍掉帧，应检查哪些 p90/p99、queue、sync 和资源竞争？
2. HTP compute 很快但 Camera e2e 变慢，怎样画 buffer/copy/format-conversion 图？
3. 为什么功耗测试必须同时报告 achieved fps、温度和 idle baseline？
4. buffer pool 降低延迟后出现偶发花屏，如何从 ownership、fence 和 in-flight request 定位？
5. 质量、latency、memory、power 四项无法同时最优时，怎样基于 use case 设 hard constraint 与优化目标？
6. area 无法实测时，面试中怎样讨论 PPA 而不虚构数据？

当前已经能用 ORT CUDA I/O Binding 的 copy count、p50/p90、RAM 和质量解释桌面系统 trade-off；deadline miss、queue depth、p99、移动功耗/温度、Snapdragon memory bandwidth 和硬件 area 均未验证。完成本节练习只能升级知识就绪度，不能升级实测证据等级。
