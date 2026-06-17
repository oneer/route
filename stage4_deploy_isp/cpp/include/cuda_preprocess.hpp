#pragma once

#include <cstddef>

namespace stage4 {

float cuda_normalize_u8_to_float_nchw(
    const unsigned char* input_hwc,
    float* output_nchw,
    int width,
    int height,
    int channels,
    int runs);

}  // namespace stage4
