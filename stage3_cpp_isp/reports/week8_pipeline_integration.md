# 第 8 周：Pipeline 集成与阶段 3 总结

## 1. 学习目标

本周把阶段 3 模块集成为可运行 pipeline，并建立最终报告：

- `run_pipeline.cpp`
- `pipeline.hpp` / `pipeline.cpp`
- `bench_pipeline.cpp`
- `dump_intermediate.cpp`
- `stage3_report.md`
- `alignment_report.md`
- `denoise_algorithm_report.md`
- `tone_mapping_algorithm_report.md`
- `hdr_toy_report.md`
- `performance_report.md`
- `stage3_interview_notes.md`

## 2. Pipeline 结构

单输入路径：

```text
input
-> denoise: none / box / gaussian
-> tone: global / local / LUT
-> gamma
-> output
```

HDR 路径：

```text
short + long exposure
-> aligned HDR merge
-> denoise
-> tone
-> gamma
-> output
```

工具保持 command-line based，便于检查参数与执行顺序。reference settings 记录在
`configs/default.yaml`，C++ 工具当前仍通过 CLI 显式传参。

## 3. 生成结果

![Pipeline comparison](figures/week8/week8_pipeline_comparison.png)

旧 pipeline metrics：

| Case | Mean luma | P95 luma | Clip fraction | Pipeline |
|---|---:|---:|---:|---:|
| global | 0.4006 | 0.6240 | 0.0000 | 43.24 ms |
| LUT | 0.4006 | 0.6241 | 0.0000 | 25.36 ms |
| local | 0.4006 | 0.6241 | 0.0000 | 103.72 ms |
| HDR local | 0.3982 | 0.6191 | 0.0000 | 126.64 ms |

这些时间来自早期 Python-side experiment，不等于当前 C++ benchmark。

## 4. 运行命令

```powershell
python .\stage3_cpp_isp\python_ref\run_week8_pipeline_summary.py
ctest --test-dir .\stage3_cpp_isp\build --output-on-failure
.\stage3_cpp_isp\build\bench_pipeline.exe
```

直接运行：

```powershell
.\stage3_cpp_isp\build\run_pipeline.exe single `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\week8_global.cpf32 `
  gaussian global reinhard 0.216 2.2
```

## 5. 阶段结果

阶段 3 已形成完整主线：

- correctness：Python-C++ alignment + CTest；
- algorithms：denoise、TM、LUT/fixed、LTM、HDR toy；
- performance：1080P/4K experiment、LTM bottleneck、pipeline benchmark；
- presentation：总报告、专题报告、面试表达和 resume bullet。

## 6. 输出排错流程

最终图异常时，不要先调 Tone Mapping 参数：

```text
source
-> denoised
-> tone_mapped
-> output (gamma)
```

使用 `dump_intermediate`：

```powershell
.\stage3_cpp_isp\build\dump_intermediate.exe `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\debug `
  gaussian global reinhard 0.216 2.2
```

诊断顺序：

1. `source` 首先错误：CPF32 shape、HWC conversion、range；
2. `denoised` 首先错误：stride、border、radius、sigma；
3. `tone_mapped` 首先错误：exposure、curve、luma/RGB、LUT rounding；
4. 只有 `output` 错误：gamma 或 output range；
5. 只有边缘错误：reflect/replicate；
6. 出现 NaN/Inf：停止，非有限输入超出当前契约。

### 6.1 第一发散原则

| 阶段 | 必查契约 | 常见形态 |
|---|---|---|
| source | shape、HWC↔planar、range | 通道错位、错行、全局 scale |
| denoised | border、radius、sigma | 边缘环带、过平滑、噪声残留 |
| HDR merged | exposure、weight、alignment | 高光低估、暗部偏差、ghost |
| tone mapped | exposure、curve、luma/RGB、LUT | 亮度、色偏、banding |
| output | gamma、clamp、range | 仅显示亮度或 clipping |

“第一个错误阶段”比“误差最大阶段”更有诊断价值，因为后续非线性模块可能放大或
压缩上游误差。

### 6.2 端到端 Golden Fixture

当前已实现自动 fixture：

```text
固定 synthetic input 与参数
Python 生成 source/denoised/tone/output golden CPF32
C++ dump 同名 intermediate tensor
逐阶段使用各自 tolerance
报告 first failed stage
```

对应文件：

- `python_ref/make_pipeline_golden.py`
- `data/pipeline_golden/`
- `tests/test_pipeline_golden.cpp`

CTest 阈值：source bit-exact、denoised `1e-6`、tone/output `1e-5`。不能只比较最终
output，否则上游正负误差可能被 curve 偶然抵消。

## 7. 阶段 4 接口

下一阶段应：

- 复用 CPF32 fixture；
- 把 hot per-pixel module 移植到 CUDA 或其他 backend；
- deployed output 与阶段 3 CPU reference 对齐；
- 固定 correctness 与 performance baseline。

## 8. Pipeline 故障实验

1. Gamma 从 `2.2` 改为 `1.0`，确认 output 首先发散；
2. Denoise border 从 reflect 改为 replicate，确认 denoised edge 首先发散；
3. LUT rounding 改成 truncate，观察 tone gradient bias；
4. CPF32 RGB channel order 交换，确认 source 已错误；
5. 每次只引入一个 bug，并记录：

```text
症状
最初怀疑
第一个发散 tensor
根因
后续 stage 如何放大或掩盖
永久测试
```

## 9. 章末自测

1. 最终输出偏暗，为什么不能立即调 exposure？
2. 只有四周不一致，应先查什么？
3. Pipeline benchmark 是否包含 allocation 为什么必须说明？
4. YAML 与 CLI 参数不一致会造成什么问题？
5. Module unit test 全过，端到端为什么仍可能失败？

## 10. Pipeline 参数与面试答案

| 关键词/参数 | 定义 | 集成风险 | 验证方式 |
|---|---|---|---|
| stage contract | 每阶段 layout/dtype/range/语义 | 单模块各自正确但接口不一致 | 每阶段 dump metadata 与 tensor |
| first divergence | C++ 与 golden 首次超过阈值的阶段 | 后续差异通常只是被放大的结果 | 按 source→denoise→tone→output 比较 |
| caller-owned buffer | 调用者管理输入/输出内存 | 生命周期、stride、aliasing 错误 | identity/overlap/奇数 stride 测试 |
| per-stage tolerance | 每阶段允许误差 | float、LUT、fixed 误差来源不同 | 根据数值预算定义，不能全链路共用大阈值 |
| config provenance | 参数来自 YAML/CLI/default 的记录 | 入口不一致会导致无法复现 | 输出最终 resolved config |
| pipeline benchmark scope | 是否包含 allocation、转换和 I/O | 不同范围数字不能直接比较 | 同时报 algorithm-only 与 e2e |

### Week 8 面试五问

1. 为什么所有 module unit test 通过，端到端仍可能失败？接口的 range/layout/参数语义可能不一致。
2. 如何用第一发散点定位？固定输入并逐阶段与 golden 比较，从首个超阈值阶段查起。
3. 为什么每阶段 tolerance 不应都设成同一个大值？各阶段误差机制不同，大阈值会掩盖前端错误。
4. caller-owned buffer 的优势和风险是什么？减少隐藏分配/复制，但必须明确 ownership、stride、生命周期和 aliasing。
5. 如何把 Stage 3 交给 Stage 4？冻结 tensor contract、CPF32/manifest、参考输出、容差、benchmark scope 和版本信息；不只交一个 `.exe`。

## 11. 集成边界

Week 8 证明学习型 denoise/HDR/Tone 模块可以按冻结合同串联，并能用逐阶段 golden 定位第一发散点。它不是完整 Bayer RAW ISP，不包含 AE/AF、真实多帧配准、去鬼影、移动端实时调度或产品级内存/功耗证明。

## 12. 端到端学习教程：从哪里开始、怎样判断完成

### 12.1 先画清楚输入输出数据契约，而不是先运行最终命令

| Stage | input | output | 关键参数 | ownership / allocation |
|---|---|---|---|---|
| source | CPF32 HWC `float32` | planar linear buffer | shape/range/layout | reader/`ImageBuffer` 持有；view 不持有 |
| denoise | planar linear | 同 shape linear | mode/radius/sigma/border | pipeline 生成独立 intermediate |
| HDR（可选） | aligned short/long `[0,1]` | linear radiance，可 `>1` | exposure/threshold | merge buffer 由 pipeline 持有 |
| tone | linear，可 `>1` | bounded `[0,1]` | mode/curve/exposure/LUT/LTM | 独立 tone intermediate |
| gamma | bounded linear display value | encoded `[0,1]` | gamma | final output buffer |

`PipelineIntermediates` 返回 owning `ImageBuffer`，便于离线诊断；这也意味着当前实现会
保留多份整图内存。它是可观察性优先的教学设计，不是零分配、ring buffer 或实时视频
内存方案。上层若只保存 view 而让该返回对象销毁，会产生悬空生命周期问题。

### 12.2 从零复现的推荐顺序

```powershell
# 1. 在干净 Release build 中验证全部 module
cmake --preset verify -S .\stage3_cpp_isp
cmake --build .\stage3_cpp_isp\out\build\verify
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure

# 2. 重建逐阶段 golden 和教学图表
python .\stage3_cpp_isp\python_ref\make_pipeline_golden.py
python .\stage3_cpp_isp\python_ref\run_week8_pipeline_summary.py

# 3. 运行单输入 pipeline，再按需 dump intermediate
.\stage3_cpp_isp\out\build\verify\run_pipeline.exe single `
  .\stage3_cpp_isp\data\week8_pipeline\week8_scene_noisy.cpf32 `
  .\stage3_cpp_isp\data\week8_pipeline\week8_global.cpf32 `
  gaussian global reinhard 0.216 2.2

# 4. 最后才测性能
.\stage3_cpp_isp\out\build\verify\bench_pipeline.exe
```

每步预期证据分别是：CTest pass/fail、golden CPF32、结果图/CSV、逐阶段 tensor 和
benchmark 输出。脚本生成的历史图表不等于本机刚执行成功；提交结论前要记录 commit、
resolved CLI 参数、工具链和产物时间。

### 12.3 配置来源、代码导航与 Python-C++ 对齐

```text
configs/default.yaml              # 报告采用的参考参数记录，不被 C++ 自动读取
include/cpp_isp/pipeline.hpp      # mode、params、owning intermediates
src/pipeline.cpp                  # 实际执行顺序与默认子模块参数
tools/run_pipeline.cpp            # CLI 解析和文件 I/O
tools/dump_intermediate.cpp       # 第一发散诊断入口
python_ref/make_pipeline_golden.py
tests/test_pipeline_golden.cpp    # 每阶段独立 tolerance
benchmarks/bench_pipeline.cpp     # 性能 scope 的真实定义
```

YAML 是 provenance 文档，CLI 才是当前 executable 的实际输入；两者不一致时，以命令
行运行值为事实并报告差异。Python/C++ 必须冻结 source、stage order、border、curve、
round/clamp 和 gamma；对齐后仍要做视觉与性能评价，因为“实现相同”不代表设计优秀。

### 12.4 Pipeline 公式/参数传播与系统权衡

| 上游变化 | 下游传播 | 不能怎样误判 |
|---|---|---|
| denoise 过强 | tone 后纹理更平、局部对比降低 | 不能把它只归因于 tone curve |
| denoise 不足 | LTM/gamma 放大暗部噪声 | 不能只继续增强 denoise 而不看 detail strength |
| exposure 过高 | curve/LUT 末端占比上升 | Python/C++ 仍可完美对齐 |
| LUT bits/domain 不足 | tone 出现 bias/banding | 不能用更大 tolerance 宣布通过 |
| HDR 未对齐 | merge 后 ghost，tone 再增强 | 不能用局部 tone 消除几何错误 |

保留四份 intermediate 提高可调试性但增加峰值内存；基础 Gaussian 计算较轻但质量有限；
Local TM 质量灵活但当前 naive latency 高；LUT 加速曲线但引入量化。最终选择必须同时
报告质量、latency、memory 和证据环境，而不是只选一个最优数字。

### 12.5 五类面试题与 Stage 3 毕业验收

1. **概念：module correctness 与 pipeline correctness 有何区别？** 前者验证单函数，
   后者还验证模块顺序、接口合同、参数来源和误差传播。
2. **原理：为什么第一发散点优先于最终最大误差？** 非线性下游会放大、压缩甚至抵消
   上游误差，首个错误 tensor 更接近根因。
3. **参数：gamma 改变后哪些 tensor 应保持不变？** source、denoised、tone_mapped 应
   不变，只有 final output 改变；否则执行顺序或参数传播错误。
4. **调试：unit tests 全过但 golden pipeline 失败怎么办？** 核对 resolved mode、range/
   layout、默认子参数和 stage tolerance，从第一失败 stage 重现最小用例。
5. **系统：怎样交付给 Stage 4/Qualcomm 端？** 冻结 tensor contract、golden、容差、
   版本和 benchmark scope，再在目标 backend 做数值/性能验证；Stage 3 没有 QAIRT/QNN、
   HVX/NEON、移动端功耗或 CAMX 集成证据。

Stage 3 主证据是 `verified_synthetic/golden`；Week 3.5 只有有限公开 sRGB bridge，
多线程仅 bilateral LUT 的部分路径。整个库是 C++17 学习型 baseline，不是生产实时 ISP。

- [ ] 能不看文档画出 single/HDR 两条 pipeline 与每阶段 range；
- [ ] 能从干净 build 复现 CTest、golden、结果和 benchmark；
- [ ] 能解释 CLI/YAML 的真实生效关系和每个核心参数；
- [ ] 能注入三个跨模块错误并用 first divergence 定位；
- [ ] 能向面试官明确区分 synthetic、public sRGB、legacy benchmark 和 not-run 项；
- [ ] 能提出下一阶段的 SIMD/ARM、TNR、buffer pool、端侧部署验证计划，但不声称已实现。

## 13. 高通岗位补强：多摄、实时 C++ 与生产边界

Stage 3 已有 C++17 pipeline、golden、benchmark 和[多摄标定/融合学习实现](multicamera_calibration_and_fusion.md)。它能支撑算法与工程面试，但当前 homography/融合主要是 synthetic planar evidence；要回答 Camera Systems 深挖，必须知道它与真实多摄的距离。

### 13.1 Homography 能解决什么、不能解决什么

针孔模型中，三维点到像素的简化关系为：

```text
s * p = K [R | t] P
```

`K` 是内参，`R/t` 是外参，真实镜头还需要畸变模型。单个 homography `p2 ~ H p1` 对同一平面或近似纯旋转成立；存在相机平移和不同深度时，近景/远景视差不同，一个 `H` 无法同时对齐。此时需要内外参、畸变校正、rectification、depth/disparity 或分层/光流 warp，而不是继续增加 feather 宽度掩盖错位。

完整实拍链路应为：

```text
intrinsic + distortion calibration
  -> stereo extrinsic calibration
  -> timestamp/exposure/WB metadata matching
  -> undistort/rectify or target-view warp
  -> overlap validity + occlusion/motion confidence
  -> photometric/color matching
  -> seam/fusion
  -> reprojection/color/seam/temporal metrics
```

几何误差先表现为 double edge/ghost，颜色或曝光不一致再表现为接缝。调试顺序应先画 feature reprojection 和 validity mask，再看颜色匹配，最后调 blend；否则融合会把几何根因模糊化。

### 13.2 同步、Rolling Shutter 与运动

两相机时间差 `Δt` 在图像平面速度约为 `v` 时，会产生近似位移 `Δx ≈ vΔt`。即使 timestamp 相近，rolling shutter 的不同行曝光时间仍可能造成局部几何不一致。面试中要区分：

- 静态双摄：可验证 calibration、颜色和基本融合；
- 软件近同步：能测 timestamp gap，但不等于硬件同步；
- 硬件同步：还要核对曝光/增益/帧 id 和 Sensor row timing；
- 动态多摄：需要 motion/occlusion confidence、失败回退和时域稳定性。

当前仓库的 near-parallax、motion seam、degenerate geometry 是受控 failure injection，不是实拍同步证据。

### 13.3 30 fps 不等于每个模块拥有 33.3 ms

30 fps 的 frame period 约 `33.3 ms`，但 capture、ISP、算法、显示/编码会共享 deadline；多 stage 还可能并行、排队或跨帧。系统需要同时看 latency、throughput 和 jitter：

```text
throughput >= target_fps
end_to_end_latency <= product_budget
queue_depth bounded
p90/p99 jitter 不触发 deadline miss
```

某节点 p50 很快但 p99 阻塞，会造成 queue accumulation 和旧帧输出。benchmark 必须声明输入是否已在 cache、I/O/分配是否排除、线程亲和性、warmup、并发 request 和输出正确性。单次 1080P fusion p50/p90 不能直接证明完整 Camera pipeline 30 fps。

### 13.4 Buffer、allocator 与 ARM 优化顺序

生产 C++ 优先冻结 buffer 合同：owner、lifetime、width/height/channels、dtype、row/channel stride、alignment、memory domain 和可写性。先用 scalar/golden 建 correctness，再依次做 allocation hoist/buffer pool、tile/cache、线程、SIMD；每一步都重跑 odd shape、边界、数值容差和尾延迟。

NEON/HVX 不是“把循环改成向量类型”这么简单：需要处理 vector width 尾部、load/store alignment、定点 scale/round/saturate、不同指令路径的 bit-exact/tolerance 和目标编译器。当前没有 ARM64/NEON/HVX 实测，不能把 x64 C++ benchmark 外推到 Snapdragon。

### 13.5 高风险故障与首查

| 现象 | 第一检查 | 不应先做的事 |
|---|---|---|
| 接缝双边 | reprojection、depth/parallax、timestamp | 直接增大 feather |
| 亮度接缝 | exposure/WB/gamma 域与 overlap 统计 | 在 encoded RGB 上盲目线性增益 |
| 动态 ghost | frame id、motion/occlusion mask | 用平均 PSNR 证明可用 |
| 尾延迟尖峰 | allocation、lock、queue、cache、频率 | 只报告最快 run |
| SIMD 边界错 | tail、stride、alignment、saturate | 放宽全图容差掩盖越界 |
| 多线程偶发错 | buffer reuse、ownership、dependency | 把问题归因给“浮点不确定” |

### 13.6 面试练习与升级证据

1. 说明 planar homography、stereo rectification、depth-aware warp 各自的适用条件。
2. 从 feature reprojection error 推导它如何变成接缝 double edge。
3. 设计静态双摄采集协议，明确 timestamp、exposure、WB、focus 和计算摄影状态。
4. 给 30 fps pipeline 分配 latency budget，并说明 queue/backpressure 如何验收。
5. 把一个 scalar kernel 优化到 NEON 的实验拆成 correctness、speed、tail、memory 四张表。
6. 解释为什么 CTest 全过、单节点 benchmark 达标仍不能声称生产实时。

升级到 `verified_real` 至少需要真实标定图、独立实拍双摄对、内外参/畸变资产、重投影与接缝指标、失败场景、可复现 C++ 命令和设备环境。升级到移动端性能证据还需要 arm64 build、实际频率/线程/温度和 profiler；硬件同步、NEON/HVX、TNR/EIS 仍需分别验证。
