#pragma once

#include "cpp_isp/image.hpp"

namespace cpp_isp {

struct HdrMergeParams {
    // 两张输入图已经空间对齐；这里用曝光时间把像素值还原到相对 radiance 再融合。
    float short_exposure = 0.25F;
    float long_exposure = 1.0F;
    // 长曝光接近饱和时降低权重，短曝光过暗时降低权重。
    float saturation_threshold = 0.92F;
    float underexposure_threshold = 0.04F;
    float weight_epsilon = 1.0e-6F;
};

// 高光越接近 1，长曝光越不可信。
float saturation_weight(float value, float threshold);
// 暗部越接近 0，短曝光越不可信。
float underexposure_weight(float value, float threshold);

// 对已经对齐的短/长曝光图做逐像素 HDR 合成。
void hdr_merge_aligned(const ImageView<const float>& short_image,
                       const ImageView<const float>& long_image,
                       ImageView<float> output,
                       const HdrMergeParams& params);

}  // namespace cpp_isp
