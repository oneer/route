# HDR Toy Merge 算法专题报告

## 1. 问题背景与边界

阶段 3 实现的是“已对齐双曝光 HDR toy merge”。目标是理解曝光融合、radiance
恢复和 Tone Mapping 的关系，而不是构建完整商用 HDR+ burst pipeline。

明确不包含：

- motion alignment；
- optical flow；
- ghost removal；
- multi-frame burst selection；
- camera response calibration。

## 2. 输入、输出与数值范围

输入：

- short exposure CPF32；
- long exposure CPF32；
- width、height、channels 完全相同；
- 假设几何位置已经对齐；
- float32 线性值；
- reference exposure 为 short `0.18`、long `0.72`。

输出：

- merged linear HDR-like CPF32；
- 数值可以超过 `[0,1]`；
- 后续通常连接 Global 或 Local Tone Mapping。

## 3. 算法

每个像素先计算质量权重：

```text
short_quality = underexposure_weight(max(short_rgb))
long_quality  = saturation_weight(max(long_rgb))

short_radiance = short / short_exposure
long_radiance  = long / long_exposure

merged = (short_quality * short_radiance
        + long_quality  * long_radiance)
       / (short_quality + long_quality + eps)
```

Python 与 C++ 使用相同分段权重：

```text
long_quality(v) =
  1                                  , v <= saturation_threshold
  clamp((1-v)/(1-threshold), 0, 1)   , otherwise

short_quality(v) =
  1                                  , v >= underexposure_threshold
  clamp(v/threshold, 0, 1)           , otherwise
```

`v` 是该像素 RGB 最大通道值。RGB 共用一个 quality weight，避免每通道独立权重
引入额外色偏。

short exposure 不易饱和，更适合保护高光；long exposure 在暗部具有更强信号，
更适合提供阴影信息。质量权重的作用是避免信任“已经饱和的长曝光高光”和
“严重欠曝的短曝光暗部”。

## 4. 公式到代码的对应关系

主要文件：

- `python_ref/hdr_merge_ref.py`
- `python_ref/run_week7_ltm_hdr_toy.py`
- `src/hdr_merge.cpp`
- `include/cpp_isp/hdr_merge.hpp`
- `tests/test_hdr_merge.cpp`
- `tools/run_hdr_merge.cpp`
- `tools/run_pipeline.cpp`

| 步骤 | Python | C++ | 易错点 |
|---|---|---|---|
| 最大通道质量输入 | `np.max(...,axis=-1)` | `max_channel` | channel / layout |
| long saturation weight | `saturation_weight` | 同名函数 | threshold / clamp |
| short dark weight | `underexposure_weight` | 同名函数 | zero threshold / epsilon |
| radiance 恢复 | 除以 exposure | `hdr_merge_aligned` | exposure 单位 |
| 加权融合 | normalized sum | `hdr_merge_aligned` | denominator / epsilon |

HDR merge 也通过 `pipeline.hpp` 暴露，因此集成 pipeline 可以先 merge，再执行
denoise 和 Tone Mapping。

## 5. 测试方法

测试覆盖：

- weight function 行为；
- shape 一致性；
- 非法参数拒绝；
- 简单 short/long merge；
- synthetic HDR-like fixture 的 Python-C++ 对齐。

最强的测试 invariant 是：

```text
如果两张图都是同一 radiance 的未饱和观测，
short / short_exposure
与
long / long_exposure
应相等，
因此合法权重下 merged 也应恢复该 radiance。
```

Python reference 可以重新生成 aligned CPF32 与 preview。

## 6. 对齐与误差

| 模块 | Case | 最大绝对误差 | PSNR | Failed |
|---|---|---:|---:|---:|
| HDR merge | aligned short/long | 4.77e-7 | 137.64 dB | 0 / 73728 |

主要误差来源：

- float32 与 Python temporary precision；
- max-channel quality weight；
- exposure 参数不一致；
- saturation / underexposure threshold 不一致。

## 7. 视觉结果

关键图片：

- `reports/figures/week7/week7_short_exposure.png`
- `reports/figures/week7/week7_long_exposure.png`
- `reports/figures/week7/week7_hdr_merge_pipeline.png`
- `reports/figures/week8/week8_pipeline_hdr_local.png`

short exposure 保留高光结构，long exposure 提供更强暗部信号。merge 后仍需 Tone
Mapping，因为线性动态范围大于普通显示范围。

## 8. 性能解释

HDR merge 本身是简单 per-pixel weighted blend。早期 Week 8 小场景中，
`HDR merge + local TM` 约为 `126.64 ms`，但主要成本来自 Local TM 的 base
estimation。

这个数字不是独立 HDR kernel latency，不能直接用来描述 HDR merge 性能。
产品链路中更困难的通常是 alignment、motion handling 与 ghost rejection。

## 9. 已知限制

- 假设双曝光完美对齐；
- 不处理 moving object 与 ghost；
- 使用 max-channel saturation/underexposure heuristic；
- 不估计 camera response function；
- 使用 synthetic exposure pair，不是 calibrated RAW bracket。

## 10. 面试复述

> 我实现了简化的已对齐双曝光 HDR merge。高光区域更信任 short exposure，暗部
> 更信任 long exposure；两张图先按 exposure 恢复 radiance，再用饱和/欠曝权重
> 融合。输出仍是宽动态范围线性结果，需要继续连接 Tone Mapping。我明确把项目
> 边界限制在 aligned toy merge，没有把它描述成含运动配准和去鬼影的完整 HDR。

## 11. 失败模式

| 症状 | 优先怀疑 |
|---|---|
| 全局 radiance scale 错误 | exposure time / unit |
| 高光过暗 | 已饱和 long frame 权重仍过高 |
| 暗部噪声重 | 欠曝 short frame 权重过高 |
| 双边缘 | geometric / motion misalignment |
| 色偏 | per-channel weight 或 channel order |
| NaN/Inf | exposure 非法或 denominator 处理错误 |

## 12. 学习练习

1. 手算 radiance=1.0、exposure=0.18/0.72 的像素；
2. clamp long exposure，解释其 radiance 为什么被低估；
3. 将一张曝光图平移 2 pixel，解释 shape validation 为什么仍会通过；
4. 填错 short exposure，区分 global scale error 与 ghost；
5. 解释 merged HDR-like result 为什么不能直接显示。
