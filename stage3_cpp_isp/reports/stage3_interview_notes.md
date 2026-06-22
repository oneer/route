# 阶段 3 面试复述笔记

## 1. 一分钟项目介绍

我围绕 RAW-like denoise、Global/Local Tone Mapping 和简化 HDR merge 构建了
C++ ISP 算法工程项目。每个模块都有 Python reference、C++17 implementation、
CPF32 output alignment、CTest、视觉对比和 benchmark。项目目标不是单纯把图调得
好看，而是证明算法正确性、量化误差并解释性能 tradeoff。

## 2. 去噪核心表达

- RAW noise 可以建模为 shot noise 与 read noise。
- Box/Gaussian 能降低噪声，但会模糊边缘。
- Bilateral 增加 range weight，使强边缘另一侧的像素贡献变小。
- NLM 使用 patch matching，但未经重度优化时不适合作为 realtime baseline。
- 去噪质量要结合 residual map、edge ROI 和指标，不能只看最终主观效果。

## 3. Tone Mapping 核心表达

- Tone Mapping 把 scene-referred linear value 映射到 display-referred range。
- Gamma 是 Tone Mapping 之后的显示/感知编码。
- Reinhard 简单单调，但可能显得灰。
- Filmic 的 highlight shoulder 更柔和。
- S-curve 能增强中间调对比，但对 clipping 和 banding 更敏感。
- Luminance-preserving TM 映射 Y，再统一缩放 RGB，以减少 hue shift。

## 4. LUT / Fixed-Point 核心表达

- LUT 适合 gamma/TM 等 nonlinear curve，因为它用 table lookup 替代昂贵计算。
- LUT speedup 取决于原公式成本：S-curve 移除 `exp` 后收益大，Reinhard 收益小。
- Fixed-point 的主要风险是 scale mismatch、rounding、saturation 和 banding。
- 本项目 12-bit LUT 精度较好，低 bit-depth 在 shadow gradient 上有 banding 风险。

## 5. Local TM 核心表达

- Local TM 把 luminance 分解为 base 与 detail。
- 压缩 base、再恢复 detail，比 Global TM 更容易保留局部对比。
- Box base 会跨越强边缘，可能产生 halo。
- Bilateral base 通过 range weight 减少跨边缘泄漏，但 direct bilateral 很慢。
- Production LTM 通常需要 guided filter、bilateral grid、pyramid、threading、
  SIMD 或 GPU。

## 6. HDR 核心表达

- HDR merge 与 Tone Mapping 是不同阶段。
- Merge 从多曝光恢复更宽的 linear radiance range。
- Tone Mapping 再把 HDR range 映射到显示范围。
- Short exposure 保护高光，long exposure 保留暗部信号。
- Long exposure 在接近饱和时应降权，short exposure 在欠曝区域应降权。
- 本项目假设 frame 已对齐，不处理 ghosting。

## 7. C++ 工程能力表达

- `ImageBuffer`/`ImageView` 分离 ownership 与 view access。
- Stride 与 channel layout 显式保存。
- Border policy 属于正确性契约，不是可忽略的实现细节。
- CPF32 让 Python-C++ alignment 可复现。
- CTest 检查单元行为，视觉图检查感知 artifact，CSV 让结果可量化。

## 8. 下一步改进方向

- 加入 config-driven pipeline。
- 实现更快的 LTM base estimation。
- 为 local filter 增加 tile/halo threading。
- 增加 interpolated LUT 与 dithering。
- 接入阶段 4 CUDA / TensorRT / NCNN deployment。
- 若 HDR 成为主线，再增加 motion-aware merge 或 ghost rejection。
