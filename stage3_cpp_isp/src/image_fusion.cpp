#include "cpp_isp/image_fusion.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cpp_isp {
namespace {

void validate_pair(const ImageView<const float>& first,
                   const ImageView<const float>& second) {
    if (first.width() != second.width() || first.height() != second.height() ||
        first.channels() != second.channels()) {
        throw std::invalid_argument("fusion image shapes do not match");
    }
}

void validate_output(const ImageView<const float>& input,
                     const ImageView<float>& output) {
    if (input.width() != output.width() || input.height() != output.height() ||
        input.channels() != output.channels()) {
        throw std::invalid_argument("fusion output shape does not match input");
    }
}

void validate_overlap(std::uint32_t width,
                      std::uint32_t x_begin,
                      std::uint32_t x_end) {
    if (x_begin >= x_end || x_end > width) {
        throw std::invalid_argument("invalid overlap range");
    }
}

}  // namespace

std::vector<float> estimate_overlap_color_gains(
    const ImageView<const float>& reference,
    const ImageView<const float>& candidate,
    std::uint32_t x_begin,
    std::uint32_t x_end,
    float epsilon,
    float max_gain) {
    validate_pair(reference, candidate);
    validate_overlap(reference.width(), x_begin, x_end);
    if (epsilon <= 0.0F || max_gain < 1.0F) {
        throw std::invalid_argument("invalid color gain parameters");
    }
    std::vector<double> reference_sum(reference.channels(), 0.0);
    std::vector<double> candidate_sum(reference.channels(), 0.0);
    for (std::uint32_t y = 0; y < reference.height(); ++y) {
        for (std::uint32_t x = x_begin; x < x_end; ++x) {
            for (std::uint32_t c = 0; c < reference.channels(); ++c) {
                reference_sum[c] += reference(y, x, c);
                candidate_sum[c] += candidate(y, x, c);
            }
        }
    }
    std::vector<float> gains(reference.channels(), 1.0F);
    for (std::uint32_t c = 0; c < reference.channels(); ++c) {
        const double gain = reference_sum[c] / std::max(candidate_sum[c], static_cast<double>(epsilon));
        gains[c] = static_cast<float>(std::clamp(gain, 1.0 / max_gain, static_cast<double>(max_gain)));
    }
    return gains;
}

void apply_channel_gains(
    const ImageView<const float>& input,
    ImageView<float> output,
    const std::vector<float>& gains,
    float minimum,
    float maximum) {
    validate_output(input, output);
    if (gains.size() != input.channels() || minimum > maximum) {
        throw std::invalid_argument("invalid channel gain parameters");
    }
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                output(y, x, c) = std::clamp(input(y, x, c) * gains[c], minimum, maximum);
            }
        }
    }
}

void feather_blend_aligned(
    const ImageView<const float>& left,
    const ImageView<const float>& right,
    ImageView<float> output,
    std::uint32_t x_begin,
    std::uint32_t x_end) {
    validate_pair(left, right);
    validate_output(left, output);
    validate_overlap(left.width(), x_begin, x_end);
    const float denominator = static_cast<float>(std::max<std::uint32_t>(x_end - x_begin - 1U, 1U));
    for (std::uint32_t y = 0; y < left.height(); ++y) {
        for (std::uint32_t x = 0; x < left.width(); ++x) {
            float right_weight = 0.0F;
            if (x >= x_end) {
                right_weight = 1.0F;
            } else if (x >= x_begin) {
                right_weight = static_cast<float>(x - x_begin) / denominator;
            }
            const float left_weight = 1.0F - right_weight;
            for (std::uint32_t c = 0; c < left.channels(); ++c) {
                output(y, x, c) = left_weight * left(y, x, c) + right_weight * right(y, x, c);
            }
        }
    }
}

FusionQualityMetrics evaluate_aligned_overlap(
    const ImageView<const float>& left,
    const ImageView<const float>& right,
    std::uint32_t x_begin,
    std::uint32_t x_end) {
    validate_pair(left, right);
    validate_overlap(left.width(), x_begin, x_end);
    FusionQualityMetrics metrics;
    std::vector<double> left_sum(left.channels(), 0.0);
    std::vector<double> right_sum(left.channels(), 0.0);
    double absolute_sum = 0.0;
    double seam_sum = 0.0;
    for (std::uint32_t y = 0; y < left.height(); ++y) {
        for (std::uint32_t x = x_begin; x < x_end; ++x) {
            for (std::uint32_t c = 0; c < left.channels(); ++c) {
                absolute_sum += std::abs(static_cast<double>(left(y, x, c) - right(y, x, c)));
                left_sum[c] += left(y, x, c);
                right_sum[c] += right(y, x, c);
                ++metrics.compared_values;
            }
        }
        for (std::uint32_t c = 0; c < left.channels(); ++c) {
            seam_sum += std::abs(static_cast<double>(left(y, x_begin, c) - right(y, x_begin, c)));
            seam_sum += std::abs(static_cast<double>(left(y, x_end - 1U, c) - right(y, x_end - 1U, c)));
        }
    }
    metrics.mean_alignment_error = absolute_sum / static_cast<double>(metrics.compared_values);
    const double pixels = static_cast<double>((x_end - x_begin) * left.height());
    for (std::uint32_t c = 0; c < left.channels(); ++c) {
        metrics.mean_color_delta += std::abs(left_sum[c] / pixels - right_sum[c] / pixels);
    }
    metrics.mean_color_delta /= left.channels();
    metrics.seam_delta = seam_sum / static_cast<double>(2U * left.height() * left.channels());
    return metrics;
}

}  // namespace cpp_isp
