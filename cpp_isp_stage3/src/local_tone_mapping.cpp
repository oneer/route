#include "cpp_isp/local_tone_mapping.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cpp_isp {

namespace {

constexpr float kEpsilon = 1.0e-6F;

float clamp01(float value) {
    return std::min(std::max(value, 0.0F), 1.0F);
}

float luminance(const ImageView<const float>& input, std::uint32_t y, std::uint32_t x) {
    if (input.channels() >= 3) {
        return 0.2126F * input(y, x, 0) + 0.7152F * input(y, x, 1) + 0.0722F * input(y, x, 2);
    }
    return input(y, x, 0);
}

void validate_same_shape(const ImageView<const float>& input, const ImageView<float>& output) {
    if (input.width() != output.width() || input.height() != output.height() ||
        input.channels() != output.channels()) {
        throw std::invalid_argument("input and output shapes do not match");
    }
}

void validate_base_shape(const ImageView<const float>& input, const ImageView<float>& base) {
    if (input.width() != base.width() || input.height() != base.height() || base.channels() != 1) {
        throw std::invalid_argument("base must be single-channel with same width/height");
    }
}

void validate_params(const LocalToneMappingParams& params) {
    if (params.exposure <= 0.0F || params.base_sigma_spatial <= 0.0F ||
        params.base_sigma_range <= 0.0F || params.detail_strength < 0.0F) {
        throw std::invalid_argument("invalid local tone mapping parameters");
    }
}

float sample_luminance_with_border(const ImageView<const float>& input,
                                   int y,
                                   int x,
                                   BorderPolicy policy) {
    const int mapped_y = map_border_index(y, static_cast<int>(input.height()), policy);
    const int mapped_x = map_border_index(x, static_cast<int>(input.width()), policy);
    if (mapped_y < 0 || mapped_x < 0) {
        return 0.0F;
    }
    return luminance(input, static_cast<std::uint32_t>(mapped_y), static_cast<std::uint32_t>(mapped_x));
}

float spatial_weight(int dx, int dy, float sigma) {
    const float d2 = static_cast<float>(dx * dx + dy * dy);
    return std::exp(-0.5F * d2 / (sigma * sigma));
}

float range_weight(float diff, float sigma) {
    return std::exp(-0.5F * diff * diff / (sigma * sigma));
}

}  // namespace

void estimate_luminance_base(const ImageView<const float>& input,
                             ImageView<float> base,
                             const LocalToneMappingParams& params) {
    validate_base_shape(input, base);
    validate_params(params);
    const int r = static_cast<int>(params.base_radius);

    for (std::uint32_t y = 0; y < input.height(); ++y) {
        for (std::uint32_t x = 0; x < input.width(); ++x) {
            const float center = luminance(input, y, x);
            float weighted_sum = 0.0F;
            float weight_sum = 0.0F;
            for (int dy = -r; dy <= r; ++dy) {
                for (int dx = -r; dx <= r; ++dx) {
                    const float value = sample_luminance_with_border(input,
                                                                     static_cast<int>(y) + dy,
                                                                     static_cast<int>(x) + dx,
                                                                     params.border_policy);
                    float weight = 1.0F;
                    if (params.base_filter == LocalBaseFilter::Bilateral) {
                        weight = spatial_weight(dx, dy, params.base_sigma_spatial) *
                                 range_weight(value - center, params.base_sigma_range);
                    }
                    weighted_sum += weight * value;
                    weight_sum += weight;
                }
            }
            base(y, x) = weight_sum > 0.0F ? weighted_sum / weight_sum : center;
        }
    }
}

void local_tone_map(const ImageView<const float>& input,
                    ImageView<float> output,
                    const LocalToneMappingParams& params) {
    validate_same_shape(input, output);
    validate_params(params);

    ImageBuffer<float> base(input.width(), input.height(), 1);
    estimate_luminance_base(input, base.view(), params);
    const auto base_view = static_cast<const ImageBuffer<float>&>(base).view();

    for (std::uint32_t y = 0; y < input.height(); ++y) {
        for (std::uint32_t x = 0; x < input.width(); ++x) {
            const float y_linear = luminance(input, y, x);
            const float base_value = std::max(base_view(y, x), kEpsilon);
            const float detail = y_linear / std::max(base_value, kEpsilon);
            const float compressed_base = apply_tone_curve(base_value * params.exposure, params.curve);
            const float detail_scale = std::pow(std::max(detail, kEpsilon), params.detail_strength);
            const float y_mapped = clamp01(compressed_base * detail_scale);
            const float scale = y_mapped / std::max(y_linear, kEpsilon);

            for (std::uint32_t c = 0; c < input.channels(); ++c) {
                output(y, x, c) = clamp01(input(y, x, c) * scale);
            }
        }
    }
}

}  // namespace cpp_isp
