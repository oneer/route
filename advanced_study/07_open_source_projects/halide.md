# Halide

## 深度阅读目标

Halide 要学习的是性能工程方法论：算法怎么写清楚，调度怎么单独优化。stage3 已经用 C++ 写高性能 ISP，但手写 C++ 很容易把算法逻辑、边界处理、并行策略和缓存优化混在一起。Halide 提供了一个更清晰的思维框架。

## algorithm/schedule separation 怎么理解

在普通 C++ 中，你写 blur 时往往同时写“怎么算”和“循环怎么跑”。Halide 把它拆开：

```text
algorithm: output(x, y) = ...
schedule: tile / vectorize / parallel / compute_at / gpu_tile
```

这意味着同一个算法可以先用简单 schedule 验证正确性，再逐步加 tile、vectorize、parallel 优化性能。

## 对 ISP 算法为什么有用

ISP 很多算子都是 stencil 或逐像素变换：demosaic、blur、bilateral、tone curve、local tone mapping。这些算法的性能瓶颈通常不是乘加次数，而是内存访问、cache locality、边界处理和并行粒度。Halide 的教程能帮你更系统地思考这些问题。

## 读代码的具体顺序

1. 先读 tutorial，不要先读 compiler `src/`。
2. 练习 blur、gradient、lookup table 这种小例子。
3. 看 schedule 每改一次，性能为什么变化。
4. 再找 camera pipeline 或 bilateral grid 相关示例。
5. 最后把这种 schedule 思想迁移回 stage3 C++。

## 可迁移练习

1. 选 `stage3_cpp_isp` 的 box blur 或 tone mapping，用 Halide 写一个最小版本。
2. 分别测试 naive、tile、vectorize、parallel 四个 schedule。
3. 把结果写入 stage3 performance report，解释性能差异来自内存还是计算。
4. 回到手写 C++，尝试用同样思想改一个循环。

## 阅读完成标准

读完后你应该能解释：高性能图像处理不是“C++ 自动快”，而是要控制数据复用、向量化、并行和调度。Halide 的价值是把这些优化从算法表达中拆出来。

## 项目信息
- GitHub：https://github.com/halide/Halide
- Star 数或活跃度：长期活跃的高性能图像处理 DSL 项目，具体 Star 数以 GitHub 页面为准。
- 主要语言：C++、LLVM

## 项目解决什么问题

Halide 解决的是图像算法中“算法表达”和“性能调度”纠缠的问题。你可以先写清楚算法，再单独写 schedule 控制 tile、vectorize、parallel、GPU 等优化。

## 项目目录结构解读

建议关注：

- `src/`：Halide 编译器核心。
- `apps/`：图像处理应用示例。
- `tutorial/`：最适合初学者。
- `test/`：语言特性和调度验证。

## 核心模块说明

Halide 的核心思想是 algorithm/schedule separation。算法描述“每个像素怎么算”，schedule 描述“怎么高效算”。这对 ISP 很重要，因为同一个 bilateral filter、tone curve、demosaic，在 Python 中清楚，在 C++ 中未必快，在 GPU 上又需要另一种调度。

## 如何和当前项目关联

stage3 正在做 C++ 高性能 ISP，Halide 能提供性能工程的思维模型：先保证算法正确，再系统优化内存访问、并行和向量化。

## 值得学习的工程设计

- 算法和调度分离。
- 自动生成 CPU/GPU 代码。
- 对图像 stencil、tile、vectorization 友好。
- 教程非常适合学习性能优化语言。

## 初学者阅读顺序

1. 先读 Halide tutorial 前几课。
2. 用一个 blur 或 tone curve 例子理解 Func、Var、schedule。
3. 再看 bilateral grid 或 camera pipeline 相关 app。
4. 对照 stage3 的 benchmark 看手写 C++ 和 DSL 优化的差别。

## 可迁移到当前项目的功能点

1. 把 stage3 的 box blur 或 tone mapping 用 Halide 写一个参考实现。
2. 对比 naive、tiled、vectorized 的性能。
3. 把 schedule 思想写回 C++ 实现注释或性能报告。

## 阅读后应该掌握什么

你应该能解释：高性能 ISP 不只是换 C++，还要系统管理内存访问、并行粒度和计算调度。
