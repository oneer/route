#pragma once

#include <cstddef>

namespace stage4 {

struct CudaPreprocessTimings {
    float h2d_mean_ms = 0.0F;
    float kernel_mean_ms = 0.0F;
    float d2h_mean_ms = 0.0F;
    float e2e_mean_ms = 0.0F;
    int h2d_count_per_run = 1;
    int d2h_count_per_run = 1;
    bool uses_pinned_memory = false;
};

// Profile H2D, kernel, D2H and their device-side end-to-end sequence with CUDA Events.
CudaPreprocessTimings profile_cuda_normalize_u8_to_float_nchw(
    const unsigned char* input_hwc,
    float* output_nchw,
    int width,
    int height,
    int channels,
    int runs,
    bool use_pinned_memory);

}  // namespace stage4
