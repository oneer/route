# Week 0：工程骨架与验证基准

## 1. 本周目标

Week 0 的目标不是实现具体 ISP 算法，而是先建立后续所有模块都要复用的验证闭环：

```text
synthetic input
-> Python reference
-> C++ output
-> compare_with_reference
-> error metrics / report
```

这个闭环是阶段三区别于“看图调参”的关键。后续 RAW denoise、Tone Mapping、Local TM、HDR merge 都必须先有 reference 和误差统计，再谈优化。

## 2. 工程结构

本周新建 `stage3_cpp_isp/`，核心目录如下：

```text
stage3_cpp_isp/
├── CMakeLists.txt
├── include/cpp_isp/
├── src/
├── tests/
├── benchmarks/
├── python_ref/
├── tools/
├── data/
└── reports/
```

`CMakeLists.txt` 预留了 GoogleTest 和 Google Benchmark 接入方式：

- 默认模式：构建不依赖第三方库的 smoke test / smoke benchmark fallback。
- `CPP_ISP_USE_FETCHCONTENT=ON`：使用 CMake FetchContent 下载 GoogleTest 和 Google Benchmark。
- `CPP_ISP_ENABLE_ASAN=ON`：在支持的编译器上启用 AddressSanitizer。

后续已使用 Qt CMake + Ninja + MinGW GCC 的 Release 配置完成本机构建和
CTest 验证。默认算法测试是 CTest 注册的轻量可执行文件；FetchContent 模式
目前只把 smoke target 切换到 GoogleTest / Google Benchmark，不能把整套测试
笼统称为 GoogleTest suite。

## 3. CPF32 数据格式

为了让 Python 和 C++ 都能无依赖读写中间结果，本阶段定义一个很小的二进制格式 `CPF32`：

```text
CPF32
<width> <height> <channels>
<little-endian float32 payload>
```

约定：

- 默认数据范围是 linear `[0, 1]`。
- payload 按 `H x W x C` 连续存储。
- payload 是 interleaved HWC，索引为 `(y * width + x) * channels + c`。
- 数值使用 little-endian IEEE-754 float32；C++ 实现拒绝 big-endian host。
- 单通道图也保留 shape 中的 `channels = 1`。
- CPF32 不保存 stride；内部 planar `ImageBuffer` 需要显式做 layout 转换。

这个格式的好处是：

- C++ 端不需要 JSON / NPY / OpenCV 依赖。
- Python 端可以直接用 numpy 写入。
- 对齐工具可以只关注数值误差，不被图像编码或压缩干扰。

## 4. 测试向量

`python_ref/make_test_vectors.py` 会生成下列 synthetic patterns：

| pattern | 目的 |
|---|---|
| zeros | 测试全黑、除零保护、低端边界 |
| ones | 测试全白、saturation、clipping |
| checkerboard | 测试高频输入、边界和滤波响应 |
| gradient_x | 测试横向连续变化和 banding |
| gradient_y | 测试纵向连续变化和 stride 访问 |
| random | 测试一般随机输入和误差统计 |
| dark_patch | 测试暗部 ROI、后续 denoise / TM 暗部提升 |
| highlight_patch | 测试高光 ROI、后续 HDR / TM 高光压缩 |

默认生成尺寸：

- `8x8x1`
- `17x19x1`
- `128x128x1`
- `128x128x3`
- `128x128x4`

可选 `--include-large` 额外生成：

- `1920x1080x1`
- `3840x2160x1`

Week0 预览图：

![Week0 test vectors](figures/week0/week0_test_vectors_contact_sheet.png)

## 5. 对齐指标

`tools/compare_with_reference.cpp` 输出：

- `max_abs_error`
- `mean_abs_error`
- `rmse`
- `psnr`
- `failed_values`

其中 `failed_values` 不是坏点数，而是超过阈值的数值个数。对于 RGB / planar4，统计单位是 scalar value，而不是 pixel。

阈值不能随便写：

- bit-exact 模块：阈值应接近 0，例如 `0` 或 `1e-7`。
- float reference vs C++ float：需要考虑 float32 / float64、运算顺序和函数近似。
- LUT / fixed-point：阈值应来自量化步长和误差预算。

## 6. 为什么 Week0 很重要

ISP 算法模块很容易出现“最终图看着差不多，但中间数值已经错了”的情况。尤其是后续模块会放大前面误差：

- BLC / normalize 的误差会影响暗部。
- Denoise 的边界策略会影响整圈像素。
- Tone Mapping 的曲线误差会在高光和暗部更明显。
- LUT / fixed-point 的 rounding 误差会形成 banding 或 bias。

所以阶段三每个模块都必须先有 reference、测试和误差报告，再做性能优化。

## 7. 本周交付物

- `CMakeLists.txt`
- `cmake/CompilerOptions.cmake`
- `cmake/Sanitizers.cmake`
- `include/cpp_isp/cpf32.hpp`
- `include/cpp_isp/metrics.hpp`
- `src/cpf32.cpp`
- `src/metrics.cpp`
- `tools/compare_with_reference.cpp`
- `tests/test_smoke.cpp`
- `benchmarks/bench_smoke.cpp`
- `python_ref/make_test_vectors.py`
- `data/test_vectors_manifest.json`
- `data/test_vectors_manifest.csv`
- `reports/figures/week0/week0_test_vectors_contact_sheet.png`

## 8. 面试复述要点

可以这样讲：

> 我在阶段三开始前先搭了验证基准，而不是直接写算法。工程里定义了一个简单的 CPF32 float 图像格式，用 Python 生成 synthetic inputs 和 golden reference，再用 C++ compare tool 统一计算 max error、mean error、RMSE、PSNR 和 failed values。这样后续 RAW denoise、Tone Mapping、HDR merge 做优化时，都能先证明输出没有被破坏。

常见追问：

1. **为什么不用肉眼看图判断正确？**
   因为图像显示会经过 gamma、quantization、resize 和色彩映射，很多中间误差肉眼不明显，但会被后续模块放大。
2. **为什么要保留 17x19 这种奇数尺寸？**
   奇数尺寸容易暴露边界、stride、tile tail 和 SIMD tail 的 bug。
3. **为什么要有全 0 / 全 1？**
   全 0 测低端边界和除零，全 1 测饱和、clipping 和 LUT 最高索引。

## 9. 当前限制

- Week0 只建立 identity reference，后续每个算法模块会各自生成真实 reference。
- `CPF32` 是项目内部格式，不是通用图像格式；它服务于对齐验证。
