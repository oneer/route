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
