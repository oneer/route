#pragma once

#include "cpp_isp/image.hpp"

#include <cstdint>
#include <vector>

namespace cpp_isp {

struct FusionQualityMetrics {
    double mean_alignment_error = 0.0;
    double mean_color_delta = 0.0;
    double seam_delta = 0.0;
    std::size_t compared_values = 0;
};

// Estimate per-channel gains in an already aligned overlap region [x_begin, x_end).
std::vector<float> estimate_overlap_color_gains(
    const ImageView<const float>& reference,
    const ImageView<const float>& candidate,
    std::uint32_t x_begin,
    std::uint32_t x_end,
    float epsilon = 1.0e-6F,
    float max_gain = 4.0F);

// Apply gains into a caller-owned buffer so repeated runs do not allocate.
void apply_channel_gains(
    const ImageView<const float>& input,
    ImageView<float> output,
    const std::vector<float>& gains,
    float minimum = 0.0F,
    float maximum = 1.0F);

// Feather from left to right across [x_begin, x_end); inputs must already align.
void feather_blend_aligned(
    const ImageView<const float>& left,
    const ImageView<const float>& right,
    ImageView<float> output,
    std::uint32_t x_begin,
    std::uint32_t x_end);

FusionQualityMetrics evaluate_aligned_overlap(
    const ImageView<const float>& left,
    const ImageView<const float>& right,
    std::uint32_t x_begin,
    std::uint32_t x_end);

}  // namespace cpp_isp
