# 第 4 周：去噪性能工程与 4K 分析

## 1. 学习目标

本周把 Week 3 bilateral 从算法原型推进到可测量的工程模块。重点不是追求最快实现，
而是建立“优化不破坏正确性”的闭环：

```text
scalar bilateral
-> range LUT
-> tile traversal
-> row / tile parallel execution
-> Python-C++ alignment
-> 256 / 1080P / 4K benchmark
-> 可复述的性能结论
```

## 2. 问题定义

输入契约：

- single-channel float `[0,1]`；
- replicate border；
- radius `r=2`；
- `sigma_spatial=1.5`；
- `sigma_range=0.08`；
- range LUT size `512`。

输出：

- shape 不变；
- float `[0,1]`；
- 每个 output pixel 只写一次。

Bilateral 每个输出像素都遍历邻域：

```text
out(p) = sum_q Ws(p,q) * Wr(Ip-Iq) * Iq
         / sum_q Ws(p,q) * Wr(Ip-Iq)
```

radius=2 时，每像素访问 25 个邻居。4K 一帧约为：

```text
3840 * 2160 * 25 ≈ 207M neighbor samples
```

这还没有计算多通道和额外 arithmetic。

## 3. 实现

新增 API：

- `bilateral_filter_range_lut_tiled`
- `bilateral_filter_range_lut_threaded_rows`
- `bilateral_filter_range_lut_threaded_tiles`

所有版本复用同一个矩形 kernel：

```text
bilateral_lut_rect(input, output, y0:y1, x0:x1)
```

变化的只是 traversal schedule：

- Untiled LUT：整图 rectangle；
- Tiled LUT：依次执行多个 tile rectangle；
- Row split：每个 worker 负责连续 row band；
- Tile split：worker 通过 atomic counter 获取 tile。

### 3.1 Halo 处理

- 当前不创建 temporary tile buffer；
- 每个 tile 只写自己的 interior rectangle；
- 邻域读取仍来自原始完整 input；
- 因此逻辑 halo 等于 radius；
- tile boundary correctness 通过跨 tile 读取原图保证。

当前 MinGW.org GCC 9.2 环境下，`std::thread` 不可用，因此 worker launcher 使用
Windows `_beginthreadex` wrapper；算法 API 本身不依赖该 launcher。

## 4. 单元测试

使用不能整除的尺寸：

```text
input: 23x19
tile: 7x5 / 8x6
thread count: 3 / 4
```

比较：

- LUT baseline；
- tiled LUT；
- row-threaded LUT；
- tile-threaded LUT。

验收阈值：

```text
max per-pixel difference <= 1e-6
```

早期 Week 4 结果：

```text
100% tests passed
0 tests failed out of 5
```

阶段 3 后续已扩展到 11 个测试。

## 5. Python-C++ 对齐

Python 生成 `64x64` synthetic edge/texture CPF32，并计算 golden bilateral LUT。
C++ 运行四种模式：

- `lut`
- `tile`
- `rows`
- `tiles`

| Mode | 最大绝对误差 | 平均绝对误差 | PSNR | Failed |
|---|---:|---:|---:|---:|
| lut | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |
| tile | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |
| rows | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |
| tiles | 3.576e-7 | 4.22e-8 | 144.05 dB | 0 / 4096 |

这说明 traversal 和 threading 没有改变算法输出，差异仍处于 float accumulation
量级。

## 6. Benchmark 结果

工具链：

- CMake 3.30.5；
- Ninja 1.12.1；
- MinGW.org GCC 9.2.0；
- Release build。

2026-06-23 已使用当前 warmup + median harness 重跑。完整 CSV：

- `reports/figures/benchmark_20260623/denoise_full.csv`
- `reports/figures/benchmark_20260623/README.md`

| 尺寸 | 方法 | Threads | 耗时 | Speedup |
|---|---|---:|---:|---:|
| 256×256 | direct | 1 | 170.265 ms | 1.00 |
| 256×256 | LUT | 1 | 120.504 ms | 1.41 vs direct |
| 1920×1080 | LUT | 1 | 3646.064 ms | 1.00 |
| 1920×1080 | tile split | 8 | 1351.635 ms | 2.70 |
| 3840×2160 | LUT | 1 | 15163.298 ms | 1.00 |
| 3840×2160 | tile split | 8 | 2513.368 ms | 6.03 |

![Thread speedup](figures/week4/week4_thread_speedup.png)

![Tile sensitivity](figures/week4/week4_tile_sensitivity.png)

## 7. 结果分析

### 7.1 Direct `exp` 与 LUT

- 256×256 下 LUT 约快 `1.41×`；
- 相对 direct bilateral 的最大误差约 `7.15e-7`；
- LUT 对 expensive range function 有收益，但仍需大量邻域读取。

### 7.2 Tile 遍历

- 256×256 小图可能更慢，因为 loop 与 scheduling overhead 占比高；
- 4K 下 tested tile size 的 single-thread gain 约 `1.06×`；
- 收益有限，因为没有把 tile+halo 搬入 cache-local scratch。

### 7.3 多线程

- 1080P 8-thread tile split：约 `2.70×`；
- 4K 8-thread tile split：约 `6.03×`；
- efficiency 低于理想值，候选原因包括 thread launch、memory traffic、scalar math；
- 256×256 工作量太小，8 threads 不一定有收益。

### 7.4 Row Split 与 Tile Split

- Row split：简单，write 连续；
- Tile split：适合未来存在 per-tile decision 或不均匀 workload；
- 当前 scalar bilateral 两者都可用，最终由 benchmark 决定。

### 7.5 先预测再实验

| 改动 | 预期 | 可能不成立的原因 |
|---|---|---|
| direct → LUT | 更快 | 建表、索引和访存抵消收益 |
| full image → tile | 大图略快 | 无 scratch 时 locality 改善有限 |
| 1 → 8 threads | 大图加速 | 启动开销、带宽、核心数 |
| radius 2 → 4 | 邻域样本约 3.24× | 常数项和 cache 使时间不严格同比 |

radius 2 的邻域是 25，radius 4 是 81：

```text
81 / 25 = 3.24
```

这是分析 benchmark 合理性的基线，不是性能保证。

### 7.6 证据等级

```text
可观察：
输入放大约 4 倍，时间如何变化

可从复杂度推断：
每像素访问 (2r+1)^2 个邻居

当前不能声称：
已经实测 cache miss 是主瓶颈

不能泛化：
单台 32-bit MinGW 结果 -> ARM/NEON/mobile SoC
```

## 8. 延伸资料

本周已经实现：

- direct bilateral range LUT；
- implicit halo tile traversal；
- row/tile parallel execution；
- Python-C++ alignment；
- 4K benchmark。

可继续阅读：

- Tomasi and Manduchi：bilateral filtering；
- Durand and Dorsey：fast bilateral approximation；
- OpenCV `parallel_for_`；
- Google Benchmark。

## 9. 限制

- 当前正式数据来自 MinGW GCC 9.2，仍不是现代 x64 production compiler baseline；
- scalar implementation，无 AVX/NEON/SIMD；
- tile 不复制 halo 到 scratch；
- 每次调用都创建 thread，没有 persistent thread pool；
- 只 benchmark single-channel；
- legacy CSV 需要按新 harness 重跑。

## 10. 面试复述

> Week 4 保持 bilateral LUT 算法不变，只改变 traversal 和 scheduling：整图、
> serial tile、row-split 和 tile-split。优化后先跑 unit test，再与 Python golden
> 对齐。2026-06-23 正式实验中，4K single-thread LUT 约 15.16 s，8-thread tile
> split 约 2.51 s，约 6.03×。我不会把它包装成产品实时实现，因为仍有 scalar math、
> thread creation、memory traffic、无 scratch tile 和无 SIMD 等限制。

## 11. 性能练习

1. 用当前 median harness 重跑 256×256、1080P、4K；
2. 记录 CPU、compiler、Release flags、radius、LUT bins、threads；
3. 计算：

```text
speedup(N) = T1 / TN
efficiency(N) = speedup(N) / N
time_per_megapixel = time_ms / megapixels
```

4. 优化前后先跑 test，再跑 alignment；
5. 若 8 threads 更慢，检查 workload、thread creation、logical cores 和 memory
   traffic，不要直接写成 cache miss。

完成标准：把性能结论写成“实验条件 + 数字 + correctness 证据 + 适用边界”。

## 12. 性能参数与面试答案

| 关键词/参数 | 含义 | 为什么影响性能 | 需要同时验证 |
|---|---|---|---|
| tile width/height | 每个任务处理的空间块尺寸 | 影响任务数、局部性、调度和 tail | halo、奇数尺寸和完整输出覆盖 |
| halo | tile 为计算邻域而额外读取的边界 | 太小会产生接缝，太大会重复计算 | tile 与 untiled max error |
| thread count | 并行 worker 数 | 受物理核、任务粒度、带宽和创建开销限制 | 1/2/4/8 的实际曲线，不假设线性 |
| warm-up/iterations | 预热与正式重复次数 | 控制冷启动和统计稳定性 | 报 median/p50/p90 与系统信息 |
| speedup | baseline latency / optimized latency | 只有相同工作与正确性时有意义 | 同输入、同输出、同计时范围 |
| allocation scope | buffer 分配是否在计时区间 | 分配可能主导短算子 | algorithm-only 与 e2e 分开 |

面试被问“8 线程为何更慢”时，先列可验证假设：任务过小、线程创建、调度、内存带宽或 false sharing；再用线程复用、硬件计数器和不同尺寸实验区分，不能无证据归因于 cache miss。

## 13. 性能实验流程

```text
锁定 scalar/LUT correctness baseline
  -> 预测瓶颈
  -> 一次只改 tile 或 thread strategy
  -> 重跑 alignment/CTest
  -> 相同 Release 输入测 p50/p90
  -> 用质量 + speedup + scope 决定是否保留
```

## 14. 从算法正确到性能结论的完整教程

### 14.1 前后依赖、输入输出数据契约与内存合同

Week 3 冻结 bilateral LUT 的数值语义，本周只改变遍历与调度，输出必须继续与单线程
LUT baseline 对齐。输入/输出是 caller-owned planar `float32` view；每个 worker 写互不
重叠的 output rectangle，并从同一个只读完整 input 取 halo。当前 tile 没有独立
scratch，也没有 tile-local allocation，所以“tiled”只表示遍历/任务划分，不代表数据
已经搬进连续 cache buffer。

### 14.2 复现顺序与代码导航

```powershell
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
.\stage3_cpp_isp\out\build\verify\bench_denoise.exe --full
python .\stage3_cpp_isp\python_ref\run_week4_denoise_performance.py
```

运行前记录 CPU、逻辑/物理核、操作系统、编译器、Release flags 和电源状态。先读
`bilateral_denoise.cpp` 的共享 rectangle kernel，再读 `bench_denoise.cpp`，确认计时
区域、尺寸和线程数，最后读分析脚本。若本机 executable 位于不同 build 目录，应以
实际 CMake 输出为准并在报告中记录，不应复制已有机器的绝对时间。

正式 harness 使用 `warmup_runs=1` 和重复样本的 median；它降低偶发抖动，但没有给出
完整分布。招聘级性能报告还应保存各次样本并给 p50/p90/p99，同时区分：

```text
algorithm-only = 已准备输入/输出，只计 kernel 调用
end-to-end      = allocation + conversion + kernel + synchronization/I/O（按定义）
```

本周 CSV 只能在相同 scope、输入、参数、编译配置下横向比较。

### 14.3 结果怎样读，怎样避免错误归因

`speedup=T1/TN`，`efficiency=speedup/N`。效率低于 1 只说明没有线性加速，不能仅凭
latency 判定 cache miss、带宽或调度谁是根因。需要分别做 thread reuse、固定频率、
tile sweep、硬件计数器或 memory roofline 才能缩小原因。

本周 4K 8-thread 约 6.03× 是指定 MinGW/CPU/参数上的 `verified_synthetic` 结果；4K
仍约 2.51 s，远离实时预算。它不支持“已完成 4K30”、ARM/NEON 或移动 SoC 结论。
多线程只覆盖 bilateral LUT 的 row/tile wrapper，不代表 Stage 3 所有模块均已并行。

### 14.4 Failure matrix、五类面试题与验收

| 现象 | 首查 | 用什么实验区分 |
|---|---|---|
| tile 接缝 | halo/read source/tile tail | tiled 与 untiled error map，odd shape |
| 8 线程小图变慢 | 创建/任务粒度 | 复用线程、扩大图像、扫 thread count |
| 同参数复跑波动大 | 系统负载/频率/样本过少 | 保存原始样本、固定电源、报告分位数 |
| 加速但 max error 变大 | 调度越界/race/算法被改 | 先跑 CTest/alignment，再接受性能数字 |
| 4K 未接近 1080P 的约 4 倍 | cache/频率/固定开销候选 | 用每 MP 时间和多个尺寸建模，避免直接定因 |

1. **概念：latency、throughput、speedup 有何区别？** 单次时间、单位时间处理量、相对
   baseline 比值；多帧并发时三者不能混用。
2. **原理：为何 radius 从 2 到 4 邻域约 3.24×？** 采样数由 25 变 81；实际时间还受
   固定成本和访存影响。
3. **参数：tile 越小会怎样？** 任务/边界管理增多，潜在 locality 改善；最优值必须实测。
4. **调试：加线程后偶发数值错误先查什么？** 输出区域重叠、共享可写状态、任务尾部和
   生命周期，而不是放宽 tolerance。
5. **系统：离 4K30 还有多少预算？** 4K30 约 33.3 ms/frame；本周 2513 ms 不能称实时，
   下一步需要算法近似、SIMD、线程复用和端侧 profiling，而非只增加线程。

- [ ] 在同一机器从 correctness baseline 重跑 full benchmark；
- [ ] 计算 speedup、efficiency、ms/MP 并保留实验条件；
- [ ] 用 odd shape 证明 tile tail/halo 正确；
- [ ] 解释 algorithm-only 与 end-to-end 的差别；
- [ ] 用证据语言区分“测得”“推断”“尚未验证”。
