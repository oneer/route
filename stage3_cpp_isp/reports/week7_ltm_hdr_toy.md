# 第 7 周：Local Tone Mapping 与已对齐 HDR Toy Merge

## 1. 学习目标

本周包含两个相关主题：

- Local Tone Mapping：压缩平滑 base，同时保留 local detail；
- HDR toy merge：融合已对齐 short/long exposure，再连接 Tone Mapping。

本周不实现 motion alignment、ghost removal 或商用 HDR+。目标是建立输入输出明确、
可测试、可对齐、能解释 artifact 和性能的工程 baseline。

## 2. 问题背景

Global TM 对所有像素使用同一 curve：

```text
Y' = f(exposure*Y)
RGB' = RGB * Y' / max(Y,eps)
```

当场景同时有 bright window 和 dark foreground 时，单一 global curve 很难兼顾。

Local TM 先估计低频 base：

```text
Y = base * detail
base' = f(exposure*base)
Y' = base' * detail^detail_strength
RGB' = RGB * Y' / max(Y,eps)
```

它能更灵活地控制 local contrast，但 base 跨越强边缘时，detail reconstruction
可能产生 bright/dark rim，也就是 halo。

HDR merge 解决另一问题：

- long exposure：暗部信号强，但高光易饱和；
- short exposure：保护高光，但暗部更暗、噪声更重。

已对齐 exposure pair：

```text
short_radiance = short / short_exposure
long_radiance  = long / long_exposure
HDR = weighted_average(short_radiance,long_radiance)
```

merge 后仍需 Tone Mapping，因为 radiance 可能超过 display range。

## 3. 输入输出

Local TM 输入：

- float32 linear RGB 或 single-channel；
- Tone Mapping 前允许大于 1；
- 输出 float32 `[0,1]`。

HDR merge 输入：

- short image `[0,1]`；
- long image `[0,1]`；
- shape 与 channel 相同；
- 假设已经对齐；
- exposure time 已知。

HDR merge 输出：

- float32 HDR-like linear radiance；
- 允许大于 1；
- 后续必须接 Global 或 Local TM。

## 4. 算法

### 4.1 Base 层

Box base：

```text
base(p) = mean(Y(q)), q ∈ window(p)
```

简单，但会跨强边缘。

Bilateral base：

```text
base(p) = sum_q Gs(||p-q||) * Gr(Yq-Yp) * Yq
          / sum_q Gs(||p-q||) * Gr(Yq-Yp)
```

利用 range weight 减少 cross-edge leakage，但 direct implementation 很慢。

### 4.2 局部重建

```text
detail = Y / max(base,eps)
mapped_base = curve(exposure*base)
mapped_y = clamp(mapped_base * detail^detail_strength,0,1)
RGB_out = clamp(RGB * mapped_y / max(Y,eps),0,1)
```

`detail_strength<1` 会抑制 texture 与 halo；`=1` 更积极地恢复 detail。

### 4.3 HDR 权重

Long exposure 接近 saturation 时降权：

```text
w_long = 1, max(long_rgb) <= threshold
w_long = (1-max(long_rgb))/(1-threshold), otherwise
```

Short exposure 过暗时降权：

```text
w_short = 1, max(short_rgb) >= threshold
w_short = max(short_rgb)/threshold, otherwise
```

融合：

```text
HDR = (w_short*short/short_exposure
     + w_long*long/long_exposure)
    / (w_short+w_long+eps)
```

### 4.4 HDR 单像素手算

真实 radiance 约为 1：

```text
short_exposure=0.18, short_pixel=0.18
long_exposure=0.72, long_pixel=0.72

short_radiance=1
long_radiance=1
```

两帧都未饱和时，合法权重下 merge 应接近 1。这是重要 test invariant。

如果 long frame 被 clamp 到 1：

```text
long_radiance = 1/0.72 = 1.389
```

它会低估更高的真实 radiance，因此 saturation weight 必须下降，让 short frame
提供高光信息。

### 4.5 Halo 形成链路

```text
base 跨强边缘混合
-> detail=Y/base 在边缘两侧异常
-> mapped_base * detail reconstruction
-> bright/dark rim
```

排查 halo 要同时看 `base`、`detail`、`mapped_base` 和 output。

## 5. 实现

新增：

- `include/cpp_isp/local_tone_mapping.hpp`
- `src/local_tone_mapping.cpp`
- `include/cpp_isp/hdr_merge.hpp`
- `src/hdr_merge.cpp`
- `tests/test_local_tone_mapping.cpp`
- `tests/test_hdr_merge.cpp`
- `tools/run_local_tone_mapping.cpp`
- `tools/run_hdr_merge.cpp`
- `benchmarks/bench_local_tone_mapping.cpp`
- `python_ref/run_week7_ltm_hdr_toy.py`

复用：

- `ImageBuffer<float>` / `ImageView`；
- `BorderPolicy::Reflect`；
- Week 5 `apply_tone_curve`；
- CPF32 alignment。

## 6. 测试

CTest 覆盖：

- constant input 产生 constant base；
- LTM output bounded，highlight ordering 不变；
- bilateral base 在 step edge 上比 box leakage 小；
- HDR weight helper；
- 未 clipping 时恢复 radiance；
- long exposure 饱和时依赖 short radiance。

早期结果：

```text
100% tests passed
0 tests failed out of 10
```

## 7. Python-C++ 对齐

使用 192×128 synthetic HDR-like scene：

| 模块 | Case | 最大绝对误差 | PSNR | Failed |
|---|---|---:|---:|---:|
| Local TM | Reinhard bilateral | 1.79e-7 | 155.92 dB | 0 / 73728 |
| HDR merge | aligned short/long | 4.77e-7 | 137.64 dB | 0 / 73728 |

这些属于 implementation difference，并低于当前 numerical acceptance threshold。
不能直接宣称为通用“人眼不可见阈值”，因为可见性还依赖 display bit depth、gamma、
观察距离和误差分布。

## 8. 视觉结果

![Local TM comparison](figures/week7/week7_ltm_global_comparison.png)

![HDR merge pipeline](figures/week7/week7_hdr_merge_pipeline.png)

HDR 图中包含：

- short exposure：高光安全但暗；
- long exposure：暗部更亮但高光 clipping；
- short/long weight map；
- merged HDR + Global TM；
- merged HDR + Local TM。

## 9. ROI 与 Halo

| 方法 | Mean luma | P95 | Clip fraction | Edge-band std |
|---|---:|---:|---:|---:|
| Global | 0.1530 | 0.3632 | 0.0000 | 0.1429 |
| LTM box | 0.1535 | 0.3653 | 0.0000 | 0.1428 |
| LTM bilateral | 0.1530 | 0.3633 | 0.0000 | 0.1430 |

当前参数较保守，因此 global/local output 接近。目的先是验证 controlled
base/detail implementation，再逐步增强 local contrast。

Halo 风险：

- Box base 跨越 highlight edge，reconstruction 可能产生 rim；
- Bilateral base 减少 leakage，但 direct bilateral 昂贵；
- 增大 `detail_strength` 会同时增强 local contrast 与 halo risk。

## 10. 性能测试

Legacy C++ Release benchmark：

| Base filter | Radius | 尺寸 | 耗时 |
|---|---:|---:|---:|
| box | 5 | 640×360 | 340.577 ms |
| box | 9 | 640×360 | 847.893 ms |
| bilateral | 3 | 640×360 | 1757.533 ms |
| bilateral | 5 | 640×360 | 4465.713 ms |
| box | 5 | 1920×1080 | 3304.228 ms |
| bilateral | 1 | 1920×1080 | 3632.998 ms |

解释：

- 每像素访问 local window；
- bilateral 每邻居还需 spatial/range weight；
- radius 成本近似 `(2r+1)^2`；
- naive Week 7 LTM 正确、可解释，但不具备 production speed。

正式绝对 latency 仍需用 warmup+median harness 重跑。

## 11. 延伸资料

已实现：

- box/bilateral base-detail LTM；
- halo comparison；
- aligned dual-exposure merge；
- saturation/underexposure-aware weight；
- HDR output 连接 Global/Local TM。

延伸阅读：

- Durand and Dorsey：Fast Bilateral Filtering for HDR Display；
- Debevec and Malik：HDR radiance map；
- Mertens exposure fusion；
- Hasinoff HDR+。

这些资料用于理解产品方向，不表示本周已实现 burst alignment 或 ghost removal。

## 12. 限制

- HDR 假设 perfect alignment；
- 无 camera response calibration；
- HDR weight 没有显式 noise model；
- Local TM 是 direct window；
- 无 guided filter、bilateral grid、mip pyramid、optimized tile/halo。

## 13. 面试复述

> 我把 Local TM 实现为 base/detail decomposition：压缩 base，再按可调强度恢复
> detail。Box base 简单但会跨边缘产生 halo；bilateral base 更保边，但 direct
> 实现很慢。HDR toy merge 假设 short/long frame 已对齐，long 在 saturation 区域
> 降权，short 在 underexposed 区域降权。Merge 恢复更宽 radiance，Tone Mapping
> 再把它映射到 display。

## 14. 下一周

Week 8 集成：

```text
linear / RAW-like input
-> optional denoise
-> optional HDR merge
-> global / local / LUT TM
-> gamma / output
```

## 15. 故障注入

### A. 错误 Exposure

把 `short_exposure` 从 `0.18` 改成 `0.36`，观察 short radiance 缩小一半。

### B. 去掉 Long Saturation Weight

令 `w_long=1`，检查高光 radiance 是否被系统性低估。

### C. 制造 Ghost

将 long exposure 平移 1–2 pixel。shape 仍合法，但 edge 出现 double image。

### D. 定位 Halo

导出 `Y/base/detail/mapped_base/output`，逐步增大 `detail_strength`，记录第一个异常
tensor。

## 16. 章末自测

1. HDR merge 与 Tone Mapping 分别改变什么？
2. 为什么 short 更可信于高光，long 更可信于暗部？
3. shape 相同为什么不等于 frame 已对齐？
4. box base 与 bilateral base 的质量/性能取舍？
5. 为什么 `detail_strength=1` 不保证无损恢复？

## 17. LTM/HDR 参数与面试答案

| 关键词/参数 | 定义 | 调节方向/风险 | 验证方式 |
|---|---|---|---|
| base radius/sigma | 分离低频 illumination 的空间尺度 | 越大 base 越平，halo/局部对比变化更明显 | step edge、halo ROI、box-vs-bilateral |
| compression strength | 对 base 动态范围的压缩强度 | 越强暗部更亮/高光更压，但易显得平 | 暗/中/亮 ROI 和局部梯度 |
| detail strength | 重建时 detail 层增益 | 过高放大噪声/halo，过低过平滑 | 纹理与噪声 ROI 联合看 |
| exposure ratio | long/short 的相对曝光尺度 | 错误会造成亮度不一致或融合偏置 | 单像素手算与未饱和区域一致性 |
| saturation weight | 高光饱和时降低 long 权重 | 保护 short 的高光信息 | 高光 patch 与去掉权重的故障实验 |
| alignment | 两帧同一坐标对应同一场景点 | shape 相同不代表已配准 | 人为位移/运动制造 ghost |

面试回答“为什么 short 保高光、long 保暗部”：short 不易饱和但暗部 SNR 差，long 暗部信号足但高光易 clip；融合权重应按可靠性变化。本周只验证已对齐 toy，不包含运动配准和去鬼影。

## 18. 从局部算子到 HDR 链路的学习闭环

### 18.1 前后依赖、张量合同与 ownership

Local TM 复用 Week 5 float curve；HDR merge 产出的 radiance 先保持 linear 且可大于
1，再交给 Global/Local TM。把 merge 输出提前 clamp 到 `[0,1]` 会永久丢掉刚恢复的
高光范围。short/long、base 和 output 都由调用者提供或由上层 `ImageBuffer` 持有，
算法 view 不接管生命周期。

| Tensor | shape/layout | range/语义 | 首要不变量 |
|---|---|---|---|
| short/long | 相同 planar float | 已对齐 exposure image `[0,1]` | 同坐标必须对应同一场景点 |
| merged | 同 shape planar float | relative linear radiance，可 `>1` | 未饱和静态区域应恢复一致 radiance |
| base | 单通道 planar float | 低频 luminance estimate | 正值、无 NaN，常量输入仍常量 |
| LTM output | 同输入 channel | bounded `[0,1]` | 单调趋势和有限性 |

shape 一致只证明数组可逐像素运算，不证明曝光、response、白平衡或几何已对齐。

### 18.2 参数选择、耦合和从零复现

主实验使用 99th percentile exposure；LTM box 为 `r=5, sigma_s=3.0,
sigma_r=0.25, detail=0.75`，bilateral base 为 `r=3, sigma_s=2.4,
sigma_r=0.35, detail=0.75`；HDR exposure 为 `0.18/0.72`，阈值为
`saturation=0.92, underexposure=0.04`。

```powershell
python .\stage3_cpp_isp\python_ref\run_week7_ltm_hdr_toy.py
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
.\stage3_cpp_isp\out\build\verify\bench_local_tone_mapping.exe
```

阅读路径：先在 `hdr_merge_ref.py` 和主脚本手算 radiance/weight，再对照
`hdr_merge.hpp/.cpp`；随后从 `local_tone_mapping.hpp/.cpp` 跟踪
`Y -> base -> detail -> mapped_base -> RGB`，最后用测试、alignment、ROI 和 halo 图分别
验证不变量、实现一致性与视觉风险。

### 18.3 Failure tree 与质量—性能—内存权衡

```text
双边/重影 -> 先看 short/long registration，不先调 tone
高光 radiance 偏低 -> 查 long saturation 与 short exposure scale
暗部噪声显著 -> 查 short underexposure weight、long reliability 与 detail strength
亮暗边缘有 rim -> 导出 base/detail，比较 box 与 bilateral
输出 NaN/闪白 -> 查 exposure>0、weight sum、epsilon、base≈0
```

更大的 base radius 能分离更低频 illumination，却按 naive window 平方增加成本，并可能
扩大 halo 影响带；bilateral base 保边但需要昂贵双权重；降低 detail strength 可抑制
halo/噪声，也牺牲局部纹理。当前实现每次创建中间 buffer，报告没有峰值内存和 buffer
pool 证据；legacy latency 也不代表 steady-state Camera pipeline。

### 18.4 面试五问、证据和验收

1. **概念：HDR merge 和 LTM 的分工？** merge 从多曝光估计更宽 linear radiance；LTM
   把它压到显示范围，两者不能互相替代。
2. **原理：halo 怎样从 base 泄漏形成？** base 跨边缘平均使 `Y/base` 两侧异常，detail
   重建把异常变成亮/暗 rim。
3. **参数：detail strength 增大为何既增强纹理也放大噪声？** noise 也存在于高频 detail，
   指数重建不会区分真实纹理和噪声。
4. **调试：shape 相同却出现 ghost，先查什么？** 几何/运动 alignment 与时间同步；tone
   参数无法修复双像。
5. **系统：怎样走向产品 HDR？** 增加 response/曝光标定、噪声感知权重、运动估计与
   去鬼影、时序稳定、快速 edge-aware base、内存/端侧 profiling；本周均未完成。

本周 LTM/HDR 为 `verified_synthetic`，实现对齐不等于真实动态场景验证。

- [ ] 能手算未饱和与 long 饱和两个 merge 像素；
- [ ] 能解释每个阈值、epsilon 和 detail 参数的量纲；
- [ ] 能导出 base/detail/weight 并用第一异常 tensor 定位；
- [ ] 能在报告中同时给 halo、clip、latency 和适用边界；
- [ ] 能明确说出 perfect alignment、无 ghost removal、非实时三项限制。
