#pragma once

#include "cpp_isp/image.hpp"

namespace cpp_isp {

struct HdrMergeParams {
    float short_exposure = 0.25F;
    float long_exposure = 1.0F;
    float saturation_threshold = 0.92F;
    float underexposure_threshold = 0.04F;
    float weight_epsilon = 1.0e-6F;
};

float saturation_weight(float value, float threshold);
float underexposure_weight(float value, float threshold);

void hdr_merge_aligned(const ImageView<const float>& short_image,
                       const ImageView<const float>& long_image,
                       ImageView<float> output,
                       const HdrMergeParams& params);

}  // namespace cpp_isp
