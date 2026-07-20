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

## 10. 常见构建故障：移动目录后的 CMake Cache

CMake cache 会记录绝对 source/build 路径。若项目目录从 `cpp_isp_stage3` 重命名为
`stage3_cpp_isp`，旧 `build/CMakeCache.txt` 仍可能指向不存在的路径。典型症状：

```text
current CMakeCache.txt directory is different
source directory ".../cpp_isp_stage3" does not exist
```

这不是源码编译错误。正确处理方式是在新的 build directory 重新 configure。为了
保留旧产物，可以先使用独立目录验证：

```powershell
$env:PATH="D:\Env\QT\Tools\Ninja;D:\Env\MinGW32\mingw\bin;$env:PATH"
& "D:\Env\QT\Tools\CMake_64\bin\cmake.exe" `
  -S .\stage3_cpp_isp `
  -B "$env:TEMP\route-stage3-check" `
  -G Ninja `
  -DCMAKE_CXX_COMPILER="D:/Env/MinGW32/mingw/bin/g++.exe" `
  -DCMAKE_BUILD_TYPE=Release
```

然后 build/CTest。不要因为目录里还留有 `.exe` 就认为它们对应当前源码。

## 11. Week 0 动手检查

1. 手写一个 `2x1x3` CPF32 payload 顺序。
2. 故意在 payload 末尾追加一个 float，确认 reader 拒绝多余数据。
3. 构造 NaN，确认 comparator 不会把它误记为“0 failed”。
4. 对 identity、float 算法和 LUT 分别写出阈值来源。
5. 在新临时 build 目录完成 configure、build、CTest。

## 12. 关键词、参数与面试答案

| 关键词/参数 | 定义 | 选择依据 | 常见故障 |
|---|---|---|---|
| golden/reference | 预先定义的期望输出 | 与实现独立、可手算或由 Python 生成 | 两端复用同一错误逻辑会“共同正确” |
| CPF32 | shape header + little-endian float32 HWC payload | 简化跨语言数值交换 | 把文件 HWC 当内部 planar 会通道错位 |
| `max_abs_error` | 所有 scalar 的最大绝对误差 | 捕获最坏局部偏差 | 单点异常会被 mean 掩盖 |
| RMSE/PSNR | 整体均方误差及其 dB 表达 | 描述全局偏差 | data range、NaN/Inf 处理必须明确 |
| tolerance | 判定对齐通过的绝对/相对容差 | 来自浮点运算或量化误差预算 | 为让测试通过而事后放宽没有意义 |
| odd shape | 如 `17×19` 的非整除尺寸 | 暴露 border、stride、tile/SIMD tail | 只测 256 对齐尺寸会漏掉尾部 bug |

面试回答示例：为什么先建 reference？因为性能优化必须有不变量；本项目先用 CPF32 固定输入输出，再用 max/mean/RMSE/PSNR 和 CTest 保证算法变化没有破坏正确性。它验证本项目数值合同，不代表视觉质量或产品 ISP 标准。

## 13. 本周数据流

```text
Python synthetic tensor -> CPF32 golden -> C++ reader/identity/module
-> CPF32 output -> compare tool -> metrics/CTest
```

## 14. 从零学习与验收闭环

### 14.1 本周在阶段中的位置

Week 0 的输入不是图像算法结果，而是“尚未冻结的工程约定”；输出是 Week 1–8
共同遵守的文件格式、测试入口和误差语言。Week 1 会把连续 HWC 文件转换为带
stride 的 planar 内存，Week 2 以后再在同一合同上加入算法。因此本周验收失败时，
不应继续比较去噪或 Tone Mapping：基础格式错误会让所有后续结论失去意义。

### 14.2 数据、内存和指标合同

| 项目 | 本周约定 | 为什么必须写清楚 |
|---|---|---|
| 文件 | header 为 ASCII，payload 为 little-endian `float32` HWC | 避免把文件编码差异误判成算法误差 |
| 内部内存 | reader 返回拥有数据的 `TensorF32`；后续转换出的 `ImageBuffer` 拥有 planar storage | 文件没有保存 view、padding 或生命周期 |
| 数值范围 | 默认 linear `[0,1]`，模块另有约定时单独声明 | PSNR 的 peak、阈值和参数量纲均依赖范围 |
| 比较单位 | `failed_values` 统计 scalar，不是 pixel | RGB 一像素最多贡献三个失败值 |
| 非有限值 | NaN/Inf 必须视作数据错误，不能参与“高 PSNR”叙述 | 普通大小比较可能漏掉 NaN |

本项目用峰值 `MAX=1` 时：

```text
MAE  = sum(|reference-output|) / N
RMSE = sqrt(sum((reference-output)^2) / N)
PSNR = 20*log10(MAX/RMSE)
```

`N` 是 scalar 数量。若输入允许超过 1，必须重新声明 `MAX` 或不使用该 PSNR；否则
同一 RMSE 会得到误导性的 dB 数字。

### 14.3 最小可复现路径

从仓库根目录执行：

```powershell
cmake --preset verify -S .\stage3_cpp_isp
cmake --build .\stage3_cpp_isp\out\build\verify
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
python .\stage3_cpp_isp\python_ref\make_test_vectors.py
```

预期产物是 `data/test_vectors_manifest.{json,csv}`、CPF32 测试向量和 Week 0 预览图。
然后选择一个 identity pair 运行 comparator；先验证 shape、payload 长度和有限性，
再解释误差指标。若 preset 生成器不可用，应更换可用 Ninja/CMake 工具链并使用新的
build 目录，不能复用记录了旧绝对路径的 cache。

### 14.4 五类面试题与项目证据

1. **概念题：golden 与普通测试输入有何区别？** 输入只规定“喂什么”，golden
   还规定期望输出；本项目用 CPF32 固定两者并记录容差。
2. **原理题：为什么同时报告 max error 和 RMSE？** max 捕获最坏点，RMSE 描述
   全局能量；只看均值会掩盖少数严重错误。
3. **参数题：容差怎样定？** 从浮点舍入、LUT 量化或定点 LSB 推导，再用独立
   reference 验证；不能在看到结果后只为通过而放宽。
4. **调试题：只有 odd shape 失败先查什么？** 查 row/channel stride、border、
   tile tail 和循环上界，定位第一个失败坐标。
5. **系统题：为什么不用 PNG 当中间格式？** PNG 会引入位深、gamma、颜色和编码
   语义；CPF32 更适合数值对齐，但代价是缺少通用元数据与显示便利性。

### 14.5 证据等级与完成标准

本周证据为 `verified_synthetic`：它证明项目内格式、解析、指标和测试闭环可用；不
证明真实 RAW 正确、视觉质量优秀或移动端实时。学习者完成本周时应能独立完成：

- [ ] 手算一个 HWC payload 的 offset，并解释 CPF32 与 planar 的差别；
- [ ] 从空 build 目录完成 configure/build/CTest；
- [ ] 解释 MAE、RMSE、PSNR、failed scalar 各自能发现什么；
- [ ] 注入尾部多一个 float、NaN 和 odd shape，并说出预期失败位置；
- [ ] 说明 Week 0 的输出怎样成为 Week 1–8 的共同输入合同。
