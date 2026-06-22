# Week 2：RAW 噪声模型与基础去噪

## 1. 本周目标

Week 2 开始进入第一个 ISP 算法模块：RAW denoise。这里不追求复杂算法，而是先把噪声模型、基础滤波、评价方式和 C++ baseline 建起来。

本周主线：

```text
linear clean scene
-> synthetic noise model
-> box / Gaussian denoise baseline
-> residual / PSNR / edge metric
-> C++ module and tests
```

## 2. RAW 噪声模型

RAW 域常见噪声可以粗略拆成两部分：

```text
noisy = Poisson(signal * gain) / gain + Gaussian(0, read_sigma)
```

- **shot noise**：来自光子到达的随机性，信号越强，绝对方差越大；但相对噪声通常在暗部更明显。
- **read noise**：来自读出电路和 ADC，和信号强度关系较弱，在暗部尤其显眼。
- **gain / ISO**：提高模拟或数字增益会让信号变亮，也会让噪声更显眼。

下图展示了 Poisson-Gaussian 模型中噪声标准差随线性信号强度变化的趋势。

![Noise std curve](figures/week2/week2_noise_std_curve.png)

## 3. 为什么 RAW 域去噪重要

RAW denoise 通常放在 demosaic 之前或附近，原因是：

- RAW 域噪声还没有被 demosaic 扩散到三个颜色通道。
- AWB gain 会放大 R/B 通道噪声，低光下色噪更明显。
- 如果噪声进入 sharpening / local tone mapping，后续会被进一步放大。

但 RAW denoise 也有风险：

- 过强滤波会误伤纹理。
- 不同 Bayer 通道噪声水平可能不同。
- 边界策略不一致会导致 Python-C++ 对齐失败。

## 4. 基础滤波 baseline

本周实现两类基础滤波：

| 方法 | 公式直觉 | 优点 | 缺点 |
|---|---|---|---|
| box filter | 窗口内均值 | 简单、快、容易测试 | 容易糊边 |
| Gaussian filter | 按空间距离加权平均 | 比 box 更平滑自然 | 仍然不看像素相似度，会糊纹理 |

它们不是最终高质量 RAW denoise，但非常适合作为 correctness / benchmark baseline。

![Week2 denoise grid](figures/week2/week2_noise_denoise_grid.png)

## 5. 指标结果

本周生成 `reports/figures/week2/week2_basic_denoise_metrics.csv`，包含：

- PSNR；
- 残差标准差 `residual std`；
- 边缘梯度均值 `edge gradient mean`。

解释方式：

- PSNR 越高，整体数值越接近 clean reference。
- residual std 越低，剩余噪声越少。
- edge gradient mean 太低，说明边缘和纹理可能被抹平。

这三个指标不能替代完整 IQ 评价，但足够支撑 Week2 的算法理解。

## 6. C++ 实现

新增：

- `include/cpp_isp/denoise.hpp`
- `src/denoise_basic.cpp`
- `tests/test_denoise_basic.cpp`
- `python_ref/noise_model_ref.py`
- `python_ref/run_week2_noise_denoise.py`

C++ 实现包括：

- `box_filter`
- `make_gaussian_kernel_1d`
- `gaussian_filter`

测试覆盖：

- box filter 保持常量图不变。
- box filter 对中心 impulse 的响应为 `1/9`。
- Gaussian kernel 归一化且对称。

## 7. 算法岗面试表达

可以这样讲：

> 我先从 RAW denoise 的噪声模型入手，把噪声拆成 shot noise 和 read noise，用 Poisson-Gaussian 模型生成 synthetic noisy input。然后实现 box 和 Gaussian 两个基础 C++ denoise baseline，用 PSNR、residual std 和 edge gradient 观察噪声抑制和边缘保留的取舍。这一步不是为了得到最强降噪效果，而是为后续 bilateral / NLM 建立 reference、测试和评价基线。

常见追问：

1. **shot noise 和 read noise 有什么区别？**
   shot noise 来自光子计数随机性，和信号强度相关；read noise 来自传感器读出和 ADC，暗部尤其明显。
2. **为什么 RAW denoise 和 sRGB denoise 不一样？**
   RAW 是线性传感器数据，噪声更接近物理成像模型；sRGB 已经过 demosaic、AWB、CCM、Tone Mapping、Gamma，噪声分布被改变。
3. **为什么 box / Gaussian 会糊边？**
   它们只考虑空间距离，不考虑像素值相似度，边缘两侧会互相平均。

## 8. 当前限制

- 本周只做空间域基础滤波，还没有 bilateral 的 range weight。
- 指标只覆盖简单数值评价，后续要补 ROI crop 和参数消融。
- 当前机器未暴露 C++ 工具链，C++ 测试代码尚未本地编译运行。
