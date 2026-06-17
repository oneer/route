#pragma once

#include "cpp_isp/image.hpp"
#include "cpp_isp/tone_mapping.hpp"

#include <cstdint>
#include <vector>

namespace cpp_isp {

struct ToneLutParams {
    ToneCurve curve = ToneCurve::Reinhard;
    std::uint32_t input_bits = 12;
    std::uint32_t output_bits = 12;
    float input_max = 8.0F;
    float exposure = 1.0F;
    bool preserve_luminance = false;
    float scurve_midpoint = 0.5F;
    float scurve_contrast = 8.0F;
};

class ToneCurveLut {
public:
    explicit ToneCurveLut(const ToneLutParams& params);

    float apply(float value) const;
    std::uint32_t apply_code(float value) const;

    const ToneLutParams& params() const { return params_; }
    const std::vector<std::uint32_t>& values() const { return values_; }

private:
    ToneLutParams params_;
    std::vector<std::uint32_t> values_;
    std::uint32_t input_max_code_ = 0;
    std::uint32_t output_max_code_ = 0;
    float input_scale_ = 1.0F;
    float output_inv_scale_ = 1.0F;
};

void tone_map_lut(const ImageView<const float>& input,
                  ImageView<float> output,
                  const ToneCurveLut& lut);

}  // namespace cpp_isp
