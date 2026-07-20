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
- 本周算法仍是 RAW-like 单帧基础滤波，不是完整 Bayer RAW denoise。

## 9. Python → C++ 移植练习

先不要看 `denoise_basic.cpp`，按以下顺序独立完成 radius=1 Gaussian：

1. 在 Python 中生成归一化 1D kernel；
2. 使用 separable horizontal + vertical 两遍滤波；
3. 明确使用 reflect-101；
4. 导出一个 `7x5x1` odd-size CPF32 golden；
5. 再写 C++ `ImageView` 版本；
6. 使用 `compare_with_reference` 输出完整误差指标。

移植时逐项核对 kernel dtype/normalization、两遍滤波顺序、border 和中间 buffer
stride。

## 10. 故障注入

- Kernel 忘记归一化：constant 图会整体变亮。
- Python 使用 replicate、C++ 使用 reflect-101：误差集中在边缘环带。
- RGB/BGR 交换：source stage 已经发散，不能误判为 denoise 参数问题。
- 先滤波后加噪：函数都可能正确，但实验问题已经被改变。

## 11. 章末自测

1. Shot noise 和 read noise 与 signal 分别是什么关系？
2. 为什么 AWB gain 会放大色噪？
3. Separable Gaussian 为什么比直接二维卷积便宜？
4. Constant、impulse、step edge 各暴露什么问题？
5. PSNR 提升但 edge gradient 明显下降，应怎样解释？

## 12. 关键词、参数与面试答案

| 关键词/参数 | 定义 | 调大后的趋势 | 验证重点 |
|---|---|---|---|
| shot noise coefficient | variance 中随信号增长的项 | 亮区随机波动更强 | 按亮度分桶看 variance/mean |
| read noise sigma | 近似与信号无关的底噪 | 暗区噪声更明显 | dark/zero patch 的 std |
| kernel radius/size | 滤波邻域半径/尺寸 | 去噪更强、计算更高、边缘更易糊 | impulse、step edge、奇数尺寸 |
| Gaussian sigma | 空间权重衰减尺度，单位 pixel | 权重更平缓、有效邻域更大 | kernel sum=1、对称性和边缘梯度 |
| separable filter | 2D kernel 拆成横向+纵向 1D | 从近似 `O(k²)` 降到 `O(2k)` | 与 direct 2D 对齐并统一 border |
| PSNR/edge gradient | 整体误差 / 局部边缘保持 proxy | 需要联合看，不是单指标最大化 | 固定噪声 realization 和 ROI |

面试回答“PSNR 上升但边缘下降”时，结论应是模型改善了平均误差但存在过平滑风险；需要查看纹理/斜边 crop 和局部指标，再决定是否减小滤波强度，而不是直接宣布质量更好。

## 13. 本周数据流

```text
clean synthetic/RAW-like tensor -> shot/read noise injection
-> noisy baseline -> box/Gaussian C++ -> Python/C++ alignment
-> PSNR + edge/visual result
```

## 14. 从噪声假设到可复现实验

### 14.1 前后依赖与输入输出数据契约

Week 1 提供 planar `ImageView`、stride 和 border 语义；本周把它们用于第一个邻域
算子。输出仍是与输入同 shape/channel 的 linear `float32`，实验脚本会 clip 到
`[0,1]`。C++ API 使用 caller-owned output view：函数不会替调用者管理输出寿命，
也不应假设输入与输出任意重叠时仍正确。

本周所谓 RAW-like 是 linear 单通道或独立通道张量，不是带真实 black level、CFA、
ISO metadata 的 Bayer 文件。它会成为 Week 3 bilateral 的 noisy baseline，但不能外推
成完整 RAW ISP 降噪结果。

### 14.2 噪声公式、符号和数值假设

脚本实际生成方式为：

```text
lambda = max(clean * shot_scale, 0)
shot   = Poisson(lambda) / shot_scale
noisy  = clip(shot + Normal(0, read_sigma), 0, 1)
```

在未 clipping 的理想条件下，`Var(shot)≈clean/shot_scale`，总方差近似
`clean/shot_scale + read_sigma²`。所以 `shot_scale` 越大，本脚本模拟的 shot noise 越
小；它不是 ISO 本身。正式主实验固定 seed `20260615`，Poisson-Gaussian 使用
`shot_scale=300`、`read_sigma=0.008`，box 为 `radius=1`，Gaussian 为
`radius=2, sigma=1.1`。固定 seed 是为了公平比较滤波器，不代表真实噪声只有一种 realization。

### 14.3 参数选择和对照设计

| 参数 | 单位/范围 | 增大趋势 | 本周怎样验证 |
|---|---|---|---|
| `shot_scale` | 模拟 photon scale，正数 | shot variance 下降 | 固定 read noise，按亮度 patch 测 std |
| `read_sigma` | `[0,1]` 线性幅值 | 暗部底噪上升 | zero/dark patch 的 std |
| `radius` | pixel，非负整数 | 邻域与成本增大、过平滑风险上升 | impulse、step edge、奇数尺寸 |
| Gaussian `sigma` | pixel，正数 | 空间权重更平坦 | kernel 曲线、PSNR 与 edge gradient |
| seed | PRNG 状态 | 不代表强弱，只固定样本 | 同参数复跑应得到同一 synthetic 输入 |

公平实验一次只改变滤波器或其强度，保持 clean scene、noise realization、border、ROI
和指标不变。若每个算法重新采样噪声，PSNR 差异可能来自输入而非算法。

### 14.4 从零执行、代码导航和排错

```powershell
python .\stage3_cpp_isp\python_ref\run_week2_noise_denoise.py
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
```

阅读顺序：`noise_model_ref.py` 先确认噪声与 pad 方式，
`run_week2_noise_denoise.py` 再确认 seed/参数/指标，随后读 `denoise.hpp` 和
`denoise_basic.cpp`，最后用 `test_denoise_basic.cpp` 检查 constant、impulse 和 kernel
不变量。正常产物是 Week 2 曲线、对比图和 metrics CSV。

排错时按现象定位：全图有固定亮度偏差先查 kernel sum；只在四周错先查 border；
横竖响应不一致先查 separable 两遍顺序与临时 buffer stride；结果更干净但纹理消失，
这是参数 trade-off，不是数值对齐 bug。

### 14.5 五类面试题、证据和验收

1. **概念：shot/read noise 如何区分？** 前者方差随信号增长，后者在简化模型中近似
   常量；可用不同亮度平场拟合 `variance=a*signal+b`。
2. **原理：separable Gaussian 为什么从 `k²` 变成约 `2k`？** 二维核可写成横纵两个
   一维核，每像素做两次长度 `k` 的遍历。
3. **参数：sigma 增大为何不等于窗口成本必然增加？** 枚举成本由 radius 决定；sigma
   改权重。若为了覆盖更大 sigma 同时增大 radius，成本才随之上升。
4. **调试：constant 图变暗先查什么？** 核归一化、border 与 clip；再逐项比较横向
   中间量，而不是先调噪声参数。
5. **系统：为什么空间滤波不能解决视频噪声稳定性？** 它没有跨帧信息，不能利用时域
   冗余，也没有运动补偿；本阶段没有实现 TNR。

证据等级为 `verified_synthetic`。它证明简化噪声模型、基础滤波与部分 C++ 单元测试
可复现，不证明真实传感器噪声标定、Bayer 通道耦合或手机实时性。

- [ ] 能从 Poisson 方差推导 `clean/shot_scale`；
- [ ] 能复现固定 seed baseline 并找到 CSV/图；
- [ ] 能预测 radius、sigma、read noise 改变后的指标趋势；
- [ ] 能用 constant/impulse/edge 分别定位三类错误；
- [ ] 能说明为什么 Week 3 要在此 baseline 上引入 range weight。
