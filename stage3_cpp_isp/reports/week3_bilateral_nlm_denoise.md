# Week 3：Bilateral / NLM 思想与工程实现

## 1. 本周目标

Week 2 的 box / Gaussian filter 只考虑空间距离，因此会跨边缘平均。Week 3 引入 bilateral filter，用空间权重和灰度相似性权重共同决定邻域像素是否参与平均。

主线：

```text
noisy RAW-like input
-> Gaussian baseline
-> bilateral direct
-> bilateral range LUT approximation
-> small NLM reference
-> metric / visual comparison
```

## 2. Bilateral 滤波

Bilateral filter 的核心形式：

```text
I_out(p) = sum_q W_s(||p-q||) * W_r(|I_p-I_q|) * I_q
           / sum_q W_s(||p-q||) * W_r(|I_p-I_q|)
```

其中：

- `W_s` 是 spatial weight，距离越远权重越低。
- `W_r` 是 range weight，像素值差异越大权重越低。
- `sigma_spatial` 控制空间窗口的平滑范围。
- `sigma_range` 控制跨边缘平均的强弱。

如果 `sigma_range` 很小，强边缘两侧几乎不会互相平均；如果很大，bilateral 会退化得更像普通 Gaussian blur。

![Bilateral comparison](figures/week3/week3_bilateral_grid.png)

### 2.1 参数必须和数据范围一起解释

`sigma_range=0.08` 只有在输入约为 `[0,1]` 时才有意义。如果输入改成 12-bit
code `[0,4095]`，同一物理尺度应同步换算，而不是仍然填写 `0.08`。

对 range weight：

```text
W_r(d) = exp(-d^2 / (2*sigma_range^2))
```

当 `sigma_range=0.08`：

| 像素差 `d` | `d/sigma_range` | range weight（约） | 含义 |
|---:|---:|---:|---|
| 0.00 | 0 | 1.000 | 完全信任 |
| 0.04 | 0.5 | 0.882 | 小差异，大概率是同一区域 |
| 0.08 | 1 | 0.607 | 权重明显下降 |
| 0.16 | 2 | 0.135 | 很少跨该差异平均 |
| 0.24 | 3 | 0.011 | 基本视为边缘两侧 |

参数实际上定义了“多大的灰度差算边缘”，不能脱离输入 range 背诵。

### 2.2 三点手算：为什么 bilateral 保边

考虑一维局部值 `[0.20, 0.22, 0.80]`，中心是 `0.22`。为简化，假设三个位置
spatial weight 都为 1，`sigma_range=0.10`：

```text
d_left  = 0.02 -> W_r ≈ 0.980
d_self  = 0    -> W_r = 1
d_right = 0.58 -> W_r ≈ 0
```

输出近似：

```text
(0.980*0.20 + 1*0.22 + 0*0.80) / (0.980 + 1 + 0)
≈ 0.210
```

普通均值约为 `0.407`，会被右侧强边缘严重拉高；bilateral 通过 range weight
抑制了这次跨边缘平均。

## 3. Range LUT 近似

直接 bilateral 每个邻域像素都要算 `exp`，代价很高。阶段三先做一个工程上常见的近似：

```text
abs(center - neighbor) -> range LUT index -> nearest weight
```

当前 C++ 实现将 `[0,1]` 的绝对差量化为 LUT index，并使用 nearest lookup，不做
线性插值。若 LUT 有 `B` 个 bin：

```text
index = round(clamp(abs(center-neighbor), 0, 1) * (B-1))
weight = LUT[index]
delta_d <= 1 / (2*(B-1))
```

最后一行只是输入差的最大量化偏差，不是最终输出误差上界。权重还会参与邻域求和
和归一化，因此仍要运行 direct-vs-LUT 测试。

## 4. NLM 只做理解型实验

NLM 的直觉是：不仅看单个像素是否相似，而是看 patch 是否相似。

```text
weight(p, q) = exp(-mean_square_patch_distance(p, q) / h^2)
```

它能利用非局部重复纹理，但复杂度远高于 bilateral。本阶段只在 `48x48` 小 crop 上做 reference，目的是理解质量/复杂度 tradeoff，不把 NLM 当作 4K 实时主线。

![NLM crop](figures/week3/week3_nlm_small_crop.png)

## 5. 指标结果

本周输出：

- `reports/figures/week3/week3_bilateral_metrics.csv`

指标包括：

- PSNR；
- 残差标准差 `residual std`；
- 边缘梯度均值 `edge gradient mean`；
- LUT 版本相对 direct bilateral 的 max abs error
- NLM 小图运行时间记录

观察重点：

- Gaussian 往往能提高 PSNR，但 edge gradient 会下降。
- bilateral 的目标不是无脑提高 PSNR，而是在降低噪声时更少跨边缘平均。
- `sigma_range` 是非常敏感的参数，过小会残留噪声，过大会糊边。

## 6. C++ 实现

新增：

- `src/bilateral_denoise.cpp`
- `tests/test_bilateral_denoise.cpp`
- `benchmarks/bench_bilateral.cpp`
- `python_ref/denoise_ref.py`
- `python_ref/run_week3_bilateral_nlm.py`

C++ 接口：

```cpp
void bilateral_filter(...);
void bilateral_filter_range_lut(...);
```

公式和代码的对应关系：

| 公式部分 | Python reference | C++ 实现 |
|---|---|---|
| spatial weight | `denoise_ref.py` | `spatial_weight` |
| direct range weight | `np.exp(...)` | `range_weight` |
| LUT 生成 | `bilateral_filter_range_lut` | `make_range_lut` |
| LUT 索引 | Python nearest index | `lookup_range_weight` |
| 邻域与 border | reference 索引逻辑 | `bilateral_lut_rect` + border sampler |
| tile/thread 调度 | golden 保持简单 | Week 4 tiled/rows/tiles wrappers |

Python golden 故意保持直白。C++ 可以改变调度和近似方式，但必须保持同一输入
契约、border 和公式语义。

测试覆盖：

- constant image 不应改变。
- strong edge 两侧不应被明显混合。
- range LUT 版本与 direct 版本误差应在阈值内。

## 7. 论文与资料调研

本周重点了解三类资料：

- Tomasi and Manduchi, *Bilateral Filtering for Gray and Color Images*, 1998：bilateral filter 的经典来源，核心是 spatial closeness 和 photometric similarity 的联合权重。
- Buades, Coll, Morel, *A Non-Local Algorithm for Image Denoising*, 2005：NLM 经典论文，强调 patch similarity 和非局部相似性。
- OpenISP 的 `bnf.py` / `nlm.py`：适合对照传统 ISP 教学实现，理解参数、窗口和计算量。

这部分调研只服务于阶段三实现：本阶段主攻 bilateral 工程化，不扩散到 BM3D、深度学习 denoise 或复杂时域降噪。

## 8. 面试复述要点

可以这样讲：

> Week3 我实现了 bilateral denoise。相比 Gaussian 只按空间距离加权，bilateral 额外引入 range weight，让强边缘两侧的像素权重变低，因此能在一定程度上保边。我还做了 range LUT 近似，把 `exp` 查表化，并用 direct bilateral 对齐验证误差。NLM 我只做了小尺寸 reference，用来理解 patch similarity 和计算复杂度，没有把它包装成实时 4K 实现。

常见追问：

1. **bilateral 为什么能保边？**
   因为边缘两侧像素值差异大，range weight 会变小，跨边缘平均被抑制。
2. **sigma_range 怎么选？**
   它应和噪声强度、数据范围相关。太小残留噪声，太大糊边。
3. **NLM 为什么慢？**
   每个输出像素都要在 search window 中比较 patch，复杂度远高于普通滤波。

## 9. 当前限制

- bilateral 只做单帧空间滤波，没有时域信息。
- 当前实现是 scalar；Week 4 已加入 tile、row/thread 和 tile/thread 调度实验，但
  tile 没有搬入 scratch buffer，也没有 SIMD。
- SIDD bridge 是真实手机 sRGB paired data，不是 Bayer RAW，不能据此声称完成了
  真实 RAW denoise 验证。

## 10. 故障注入与排错

### 实验 A：把 `sigma_range` 当成错误量纲

将 `[0,1]` 输入乘以 4095，但保持 `sigma_range=0.08`。几乎所有非零差异的
range weight 都会接近 0，输出更接近 identity。这不是算法失效，而是参数单位与
输入 range 不匹配。

### 实验 B：让 Python 与 C++ 使用不同 border

若内部区域一致、误差只出现在四周，优先检查 border：

```text
误差只在边缘？
-> 检查 reflect/replicate 和 radius
误差遍布全图？
-> 检查 sigma、LUT bins、index rounding
仍不对？
-> 比较单个中心像素的 numerator / denominator
```

### 实验 C：优化后漏写尾部 tile

使用 `23x19` 输入和 `8x6` tile。若只测试能整除的尺寸，最后一块 tile 的边界错误
可能永远不出现。

## 11. 章末自测

1. 输入从 `[0,1]` 改成 `[0,1023]`，`sigma_range=0.08` 应如何换算？
2. 为什么 LUT bin 的输入量化误差不能直接当成最终像素误差？
3. bilateral 的复杂度为何约为 `O(W*H*(2r+1)^2*C)`？
4. 为什么 direct-vs-LUT 和 Python-vs-C++ 是两种不同测试？
5. NLM 比 bilateral 多出的主要计算维度是什么？

答案要点：

1. 若保持同一归一化含义，约换成 `0.08*1023`。
2. 权重还会参与邻域加权和归一化，误差传播依赖局部内容。
3. 每个像素、每个通道都遍历一个二维邻域。
4. 前者测近似误差，后者测同一算法的实现一致性。
5. NLM 还在 search window 内比较 patch。

## 12. 关键词、参数与面试答案

| 关键词/参数 | 量纲/作用 | 调大后的趋势 | 验证方式 |
|---|---|---|---|
| `sigma_spatial` | 空间距离尺度，单位 pixel | 更远像素参与，计算邻域/平滑范围增大 | 固定 range 参数看边缘和噪声 |
| `sigma_range` | 像素差异尺度，单位与输入范围一致 | 跨强度差异的权重增大，更接近普通 Gaussian | `[0,1]` 与 `[0,255]` 不能复用同值 |
| radius | 实际枚举邻域半径，单位 pixel | 运算量约随面积增长 | 质量/latency 双表并覆盖 tail |
| range LUT bins | `exp` 权重的离散表大小 | 误差通常下降、cache/表成本增加 | direct-vs-LUT max error + 速度 |
| NLM search/patch | 搜索范围 / 相似度 patch 尺寸 | 更可能找到重复结构，也显著增加复杂度 | 合成重复纹理和无重复纹理对照 |
| filter strength `h` | NLM 相似度衰减尺度 | 更强平均、纹理损失风险更高 | noise/texture/edge 联合评价 |

面试题“bilateral 为什么保边”的回答必须落到双权重：空间近不够，颜色/亮度差也要小；跨边缘像素因 range weight 很低而被抑制。LUT 优化后还必须重新对齐，因为速度收益可能来自改变了函数近似。

## 13. 本周数据流

```text
noisy tensor -> direct bilateral reference
-> C++ direct / range-LUT bilateral -> alignment + benchmark
-> small NLM Python concept comparison -> quality/cost decision
```

## 14. 可复现的算法学习闭环

### 14.1 前后依赖、输入输出数据契约与 ownership

Week 2 提供同一 noisy realization 和 Gaussian baseline；本周只新增“是否允许邻居参与
平均”的 range 判据。输入/输出均为同 shape 的 planar `float32`，主 synthetic 实验
在 `[0,1]`，border 由调用参数明确指定。C++ 接口接收 non-owning input/output view，
调用者持有 storage；当前文档不承诺任意 in-place alias 正确。

Week 3 的 C++ 主线是 bilateral direct/LUT。NLM 只在 Python `48×48` crop 上用于理解
patch similarity；SIDD bridge 是已处理 sRGB paired data。三者证据不能混写成“C++ 已
实现真实 RAW NLM”。

### 14.2 正式参数、对照和运行路径

主实验固定 seed `20260616`，噪声为 `shot_scale=260, read_sigma=0.01`。对照组为：

| Case | 参数 | 回答的问题 |
|---|---|---|
| Gaussian | `r=2, sigma=1.1` | 不看强度差时会损失多少边缘 |
| bilateral weak | `r=2, sigma_s=1.5, sigma_r=0.06` | 较严格 range 判据的去噪/保边平衡 |
| bilateral strong | `r=3, sigma_s=2.2, sigma_r=0.12` | 更大邻域和 range tolerance 的代价 |
| LUT bilateral | weak 参数，`bins=512` | 查表近似相对 direct 的误差 |
| NLM concept | patch `r=1`、search `r=3`、`h=0.08` | patch 相似度和成本的直观关系 |

从仓库根目录运行：

```powershell
python .\stage3_cpp_isp\python_ref\run_week3_bilateral_nlm.py
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
```

有合法 SIDD Tiny 数据时，再单独运行 `run_week3_sidd_real_data.py`，并把结果标为
`verified_public` 的 sRGB bridge；没有数据时不得把未运行结果写成实测。

### 14.3 代码导航、对齐和性能边界

```text
denoise_ref.py                  # 直白 Python direct/LUT/NLM reference
run_week3_bilateral_nlm.py     # 冻结数据、参数、指标和图
include/cpp_isp/denoise.hpp    # C++ API/参数合同
src/bilateral_denoise.cpp      # direct 与 range LUT hot loop
tests/test_bilateral_denoise.cpp
benchmarks/bench_bilateral.cpp # microbenchmark，不是整条 ISP latency
```

Python-C++ 对齐必须冻结数据范围、border、LUT index 的 round/clamp 和累加顺序。direct
对 LUT 测“近似误差”，Python LUT 对 C++ LUT 测“实现误差”，不能用后者证明前者无损。
本周 benchmark 是 scalar 单模块证据，不包含文件 I/O、显示、SIMD、ARM、功耗或整条
Camera pipeline。

### 14.4 Failure、权衡与面试五问

质量权衡是 noise suppression 与 edge/texture preservation；计算权衡是 direct `exp`
与 LUT 量化/访存；NLM 的更大 search/patch 又引入数量级更高的比较成本。若 PSNR 上升
但 edge gradient 和纹理 crop 下降，应表述为“平均误差改善、过平滑风险增加”。

1. **概念：bilateral 的两个域是什么？** 空间域决定距离，range 域决定强度相似性，
   两者相乘后才得到邻居权重。
2. **原理：为何强边缘不会被完全保证保留？** 噪声、sigma、窗口和颜色距离都会改变
   range weight；大 `sigma_range` 仍会跨边缘平均。
3. **参数：LUT bins 越大越好吗？** 通常降低输入量化误差，但增加表大小；最终收益取决
   cache、索引成本与 direct 函数代价，要做质量/速度消融。
4. **调试：中心区域都错，边缘并不特殊，先查什么？** 查 range 量纲、sigma、LUT round/
   clamp 和 numerator/denominator；border mismatch 通常先表现为边缘环带。
5. **系统：为什么本方案还不能称为 Qualcomm 实时 denoise？** 只有 scalar 单帧教学
   kernel，没有 NEON/HVX、TNR、真实 RAW tuning、端侧 latency/功耗和产品集成证据。

证据为 synthetic direct/LUT 与部分公开 sRGB bridge；学习验收要求学习者能：

- [ ] 手算一个三点 bilateral 输出并解释每个权重；
- [ ] 在固定输入上 sweep `sigma_range`，同时记录 PSNR、edge 和 latency；
- [ ] 分开报告 direct-vs-LUT 与 Python-vs-C++；
- [ ] 注入 range 量纲、border 和 tail 三类错误并定位；
- [ ] 明确 NLM、SIDD、RAW 和 C++ 实现各自的证据边界。
