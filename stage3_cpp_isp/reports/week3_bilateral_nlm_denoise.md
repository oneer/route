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

## 2. Bilateral Filter

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

## 3. Range LUT 近似

直接 bilateral 每个邻域像素都要算 `exp`，代价很高。阶段三先做一个工程上常见的近似：

```text
abs(center - neighbor) -> range LUT -> interpolated weight
```

这样可以把大量 `exp` 替换成查表和线性插值。这个方向很适合后续 fixed-point / SIMD / 硬件友好实现，但必须通过误差报告证明近似不会明显破坏输出。

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

- PSNR
- residual std
- edge gradient mean
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

- C++ benchmark 代码已写，但当前机器没有 C++ 工具链，暂未本地运行。
- bilateral 只做单帧空间滤波，没有时域信息。
- 当前没有做 tile / 多线程优化，Week4 专门处理性能问题。
