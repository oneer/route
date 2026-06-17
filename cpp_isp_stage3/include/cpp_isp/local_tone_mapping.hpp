#pragma once

#include "cpp_isp/border.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/tone_mapping.hpp"

#include <cstdint>

namespace cpp_isp {

enum class LocalBaseFilter {
    Box,
    Bilateral,
};

struct LocalToneMappingParams {
    ToneCurve curve = ToneCurve::Reinhard;
    float exposure = 1.0F;
    std::uint32_t base_radius = 5;
    float base_sigma_spatial = 3.0F;
    float base_sigma_range = 0.25F;
    float detail_strength = 1.0F;
    LocalBaseFilter base_filter = LocalBaseFilter::Box;
    BorderPolicy border_policy = BorderPolicy::Reflect;
};

void estimate_luminance_base(const ImageView<const float>& input,
                             ImageView<float> base,
                             const LocalToneMappingParams& params);

void local_tone_map(const ImageView<const float>& input,
                    ImageView<float> output,
                    const LocalToneMappingParams& params);

}  // namespace cpp_isp
