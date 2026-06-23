# 2026-06-23 阶段 3 正式性能数据

## 环境

- CPU：Intel Core i3-12100F
- 物理核心 / 逻辑处理器：4 / 8
- OS：Windows 10 Pro 64-bit，10.0.19045
- Compiler：MinGW.org GCC 9.2.0
- CMake：3.30.5
- Ninja：1.12.1
- Build type：Release
- Release flags：`-O3 -DNDEBUG`
- Generator：Ninja
- Source base commit：`80de98a`

## 统一测量规则

- Clock：`std::chrono::steady_clock`
- Warmup：1 次
- Denoise / Pipeline `--full`：3 次 measured run，取 median
- Tone Mapping / Tone LUT：5 次 measured run，取 median
- Local Tone Mapping：3 次 measured run，取 median
- File I/O：不计入
- Module benchmark：输入和主要输出 buffer 在计时前分配
- Pipeline benchmark：包含 `run_pipeline_single` 内部 intermediate allocation
- Denoise 参数：radius=2，sigma spatial=1.5，sigma range=0.08，LUT bins=512
- Denoise tile：64×64、128×64、128×128
- Denoise threads：1、2、4、8
- Tone Mapping：RGB float32，percentile exposure，1080P/4K
- Pipeline：RGB float32，exposure=0.22，gamma=2.2

## 文件

- `denoise_full.csv`
- `tone_mapping.csv`
- `tone_lut.csv`
- `local_tone_mapping.csv`
- `pipeline_full.csv`
- `system_info.txt`

## 正确性复验

- Release clean build 成功
- CTest：12/12 通过
- Denoise optimized variants 的 `max_abs_vs_lut` 为 0
- Pipeline golden fixture 逐阶段通过

这些结果仅代表当前 Windows/MinGW/CPU 环境，不能直接泛化到 ARM、NEON、移动
SoC 或硬件 ISP。
