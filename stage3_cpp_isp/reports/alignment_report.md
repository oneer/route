# 阶段 3 数值对齐报告

## 1. 对齐方法

项目使用 CPF32 作为简单的跨语言张量格式：

```text
CPF32
<width> <height> <channels>
<little-endian float32 HWC payload>
```

完整对齐流程是：

```text
Python reference 输出
-> 写入 CPF32
-> C++ 工具执行同一算法
-> 写入 CPF32
-> compare_with_reference 比较
```

统一统计以下指标：

- 最大绝对误差 `max_abs_error`
- 平均绝对误差 `mean_abs_error`
- 均方根误差 `RMSE`
- 峰值信噪比 `PSNR`
- 超过阈值的数值个数 `failed_values`

`failed_values` 的单位是 scalar value，不是 RGB pixel。NaN/Inf 不属于当前模块
数据契约；比较器遇到非有限值会直接报错，不能让 NaN 因比较规则而被误记为
“0 failed”。

阈值不能随手写一个固定常数，而应根据路径决定：

- identity / integer code path：应接近 bit-exact；
- Python float 与 C++ float：考虑 dtype、运算顺序和数学函数实现差异；
- LUT / fixed-point：考虑输入索引量化、输出 code step 和 rounding rule；
- 优化前后同算法：若只改变调度，阈值应比跨语言对齐更严格。

`1e-5` 是当前跨语言 fixture 的验收阈值，不是所有模块都应无条件复用的常数。

## 2. 代表性结果

以下数字直接来自已提交的 Week 4–7 alignment CSV。统一使用
`tolerance=1e-5`，failed count 的分母是 scalar values。

| 模块 | Reference → candidate | 数据契约 | Border | 最大绝对误差 | 平均绝对误差 | RMSE | PSNR | Failed |
|---|---|---|---|---:|---:|---:|---:|---:|
| Bilateral LUT | Python LUT → C++ LUT | f32 `[0,1]`，64×64×1 | replicate | 3.576e-7 | 4.22e-8 | 6.28e-8 | 144.05 dB | 0 / 4096 |
| Bilateral tiled | Python LUT → C++ tiled LUT | f32 `[0,1]`，64×64×1 | replicate | 3.576e-7 | 4.22e-8 | 6.28e-8 | 144.05 dB | 0 / 4096 |
| Global TM | Python Reinhard → C++ Reinhard RGB | f32 HDR-like → `[0,1]` | 不适用 | 5.96e-8 | 4.1e-9 | 8.6e-9 | 161.30 dB | 0 / 184320 |
| Global TM | Python Reinhard → C++ Reinhard luma | f32 HDR-like → `[0,1]` | 不适用 | 1.788e-7 | 6.8e-9 | 1.25e-8 | 158.04 dB | 0 / 184320 |
| Global TM | Python Filmic → C++ Filmic luma | f32 HDR-like → `[0,1]` | 不适用 | 1.788e-7 | 1.31e-8 | 1.93e-8 | 154.29 dB | 0 / 184320 |
| Global TM | Python S-curve → C++ S-curve luma | f32 normalized → `[0,1]` | 不适用 | 2.980e-7 | 6.9e-9 | 1.62e-8 | 155.78 dB | 0 / 184320 |
| Tone LUT | Python LUT → C++ Reinhard 10→10 | f32 domain `[0,8]` → `[0,1]` | 不适用 | 1.192e-7 | 6.1e-9 | 1.18e-8 | 158.59 dB | 0 / 184320 |
| Tone LUT | Python LUT → C++ Filmic 12→12 | f32 domain `[0,8]` → `[0,1]` | 不适用 | 8.94e-8 | 3.2e-9 | 6.3e-9 | 164.08 dB | 0 / 184320 |
| Local TM | Python LTM → C++ Reinhard bilateral | f32 HDR-like → `[0,1]` | reflect-101 | 1.788e-7 | 8.9e-9 | 1.60e-8 | 155.92 dB | 0 / 73728 |
| HDR merge | Python aligned merge → C++ merge | f32 exposure `[0,1]` → linear HDR-like | 不适用 | 4.768e-7 | 7.05e-8 | 1.312e-7 | 137.64 dB | 0 / 73728 |

证据文件：

- `figures/week4/week4_python_cpp_alignment.csv`
- `figures/week5/week5_python_cpp_alignment.csv`
- `figures/week6/week6_python_cpp_alignment.csv`
- `figures/week7/week7_python_cpp_alignment.csv`

注意：Tone LUT 行比较的是“Python LUT 实现与 C++ LUT 实现”，不是
“float curve 与 LUT approximation”。后者属于算法近似误差，应读取
`figures/week6/week6_lut_size_ablation.csv`。

## 3. 常见误差来源

- float32 运算顺序不同；
- Python 中间计算临时使用 float64；
- C++ `std::exp` 与 NumPy `exp` 的实现差异；
- LUT code 量化后再转换回 normalized float；
- border policy、曝光参数、curve 参数不一致；
- nearest lookup、interpolation、rounding、saturation 规则不一致。

误差空间分布本身也能帮助定位问题：

| 误差分布 | 优先怀疑 |
|---|---|
| 只在图像边缘 | border / radius |
| 全图近似固定比例 | exposure / range / scale |
| 平滑梯度出现周期性台阶 | LUT index / rounding / output bit depth |
| 仅高光区域异常 | clamp / saturation / white point |
| 通道颜色互换 | HWC / planar / RGB 顺序 |
| 出现少量 NaN/Inf | 非法输入、除零或 overflow，应直接失败 |

## 4. 排错清单

Python 与 C++ 不对齐时，按以下顺序检查：

1. tensor shape 与 channel layout 是否一致；
2. border policy 是否一致；
3. dtype 与 range 是否一致；
4. exposure、curve、sigma 等参数是否一致；
5. rounding 与 saturation rule 是否一致；
6. reference 使用 nearest LUT lookup 还是 interpolation；
7. 比较中间输出，不只比较最终 RGB；
8. 先拒绝 NaN/Inf，再解释 max error 与 failed count。

## 5. 可复现实验必须保存什么

一次可复查的 alignment 记录应同时保存：

```text
reference 文件和生成命令
candidate executable 和参数
shape / dtype / range / layout
border / rounding / clamp
tolerance 的来源
max / mean / RMSE / PSNR / failed count
error map 或差异集中区域
Git commit 与构建类型
```

仅保存一张“0 failed”截图不足以复现实验。

## 6. 故障注入练习

依次制造三个错误并预测 error map：

1. 将 bilateral C++ 改成另一个 border；
2. 将 LUT nearest rounding 改成 truncate；
3. 将 HDR short exposure 填错两倍。

它们应分别对应“边缘环带”“梯度系统偏差”“全局 radiance scale 偏差”。能根据
误差形态判断根因，比背诵一个阈值更重要。
