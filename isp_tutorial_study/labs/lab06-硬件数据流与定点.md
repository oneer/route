# Lab 06：硬件数据流、存储、定点与性能

对应章节：11–13、33。

## 目标

把图像算法转换成像素率、带宽、缓存、位宽、吞吐和最坏延迟约束，并用 C++ benchmark/对齐测试验证实现。

## 纸面预算

对 3840×2160@60、RAW12 输入，至少计算：

```text
active_pixel_rate = width × height × fps
required_clock = active_pixel_rate / pixels_per_clock / utilization
minimum_stream_bandwidth = active_pixel_rate × bits_per_pixel
line_buffer_bits = image_width × cached_lines × internal_bits_per_pixel
```

必须另外说明 blanking、对齐、metadata、中间读写和多路输出为什么会增加真实预算。

## 构建与测试

前置检查：`cmake --version` 和 `ctest --version`。

```powershell
Set-Location D:\document\route\stage3_cpp_isp
cmake --preset verify
cmake --build --preset verify
ctest --preset verify
```

如 preset 不适配本机，使用项目 README 中的显式 Ninja/编译器命令，不要随意改项目 CMake 配置。

## Benchmark

```powershell
.\build\bench_denoise.exe --full
.\build\bench_tone_mapping.exe
.\build\bench_tone_lut.exe
.\build\bench_pipeline.exe
```

## 定点实验

选择 tone LUT 或一个 3×3 矩阵，比较 float 与 10/12/14-bit 定点实现：

- 最大绝对误差、平均误差。
- 饱和像素数量。
- 暗部 banding 或颜色跳变。
- 运行时间和内存。

## 验收

- 区分 active pixel rate、接口像素率和内部总访存带宽。
- 缓存预算包含通道数、内部位深和边界行。
- 性能报告至少包含 p50/p90 或多次重复，不只记录一次时间。
- 定点报告说明 Q 格式、舍入、饱和和溢出策略。
- 能指出算法改动如何影响 SRAM、布线、时序和功耗。
