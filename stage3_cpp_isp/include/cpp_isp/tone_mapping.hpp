#pragma once

#include "cpp_isp/image.hpp"

#include <cstdint>

namespace cpp_isp {

// 三种全局 tone curve：Reinhard 稳定简单，Filmic 更像电影响应，S 曲线强调中间调对比。
enum class ToneCurve {
    Reinhard,
    Filmic,
    SCurve,
};

struct ToneMappingParams {
    ToneCurve curve = ToneCurve::Reinhard;
    // exposure 先在线性域放大/缩小，再进入 tone curve，相当于调整曝光补偿。
    float exposure = 1.0F;
    // true 时按亮度压缩后再缩放 RGB，能减少直接逐通道映射导致的色偏。
    bool preserve_luminance = false;
    float scurve_midpoint = 0.5F;
    float scurve_contrast = 8.0F;
};

// 对单个线性值应用 tone curve；输入可大于 1，输出约束在显示友好的 [0, 1] 范围。
float apply_tone_curve(float value, ToneCurve curve, float scurve_midpoint = 0.5F, float scurve_contrast = 8.0F);

// 根据输入亮度/像素分布估算曝光：把指定百分位的值映射到 target_value。
float compute_percentile_exposure(const ImageView<const float>& input,
                                  float percentile,
                                  float target_value,
                                  bool use_luminance);

void tone_map(const ImageView<const float>& input,
              ImageView<float> output,
              const ToneMappingParams& params);

// Gamma 是显示编码步骤，通常 tone mapping 后再做；gamma=2.2 对应常见 sRGB 近似。
void apply_gamma(const ImageView<const float>& input,
                 ImageView<float> output,
                 float gamma);

}  // namespace cpp_isp
