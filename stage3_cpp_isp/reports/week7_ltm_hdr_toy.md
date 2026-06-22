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
