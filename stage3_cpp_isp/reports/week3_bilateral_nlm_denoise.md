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
