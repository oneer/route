#pragma once

#include "cpp_isp/image.hpp"

#include <cstdint>

namespace cpp_isp {

enum class ToneCurve {
    Reinhard,
    Filmic,
    SCurve,
};

struct ToneMappingParams {
    ToneCurve curve = ToneCurve::Reinhard;
    float exposure = 1.0F;
    bool preserve_luminance = false;
    float scurve_midpoint = 0.5F;
    float scurve_contrast = 8.0F;
};

float apply_tone_curve(float value, ToneCurve curve, float scurve_midpoint = 0.5F, float scurve_contrast = 8.0F);

float compute_percentile_exposure(const ImageView<const float>& input,
                                  float percentile,
                                  float target_value,
                                  bool use_luminance);

void tone_map(const ImageView<const float>& input,
              ImageView<float> output,
              const ToneMappingParams& params);

void apply_gamma(const ImageView<const float>& input,
                 ImageView<float> output,
                 float gamma);

}  // namespace cpp_isp
