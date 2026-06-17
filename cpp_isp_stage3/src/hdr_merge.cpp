#include "cpp_isp/hdr_merge.hpp"

#include <algorithm>
#include <stdexcept>

namespace cpp_isp {

namespace {

float clamp01(float value) {
    return std::min(std::max(value, 0.0F), 1.0F);
}

void validate_shapes(const ImageView<const float>& short_image,
                     const ImageView<const float>& long_image,
                     const ImageView<float>& output) {
    if (short_image.width() != long_image.width() || short_image.height() != long_image.height() ||
        short_image.channels() != long_image.channels() || short_image.width() != output.width() ||
        short_image.height() != output.height() || short_image.channels() != output.channels()) {
        throw std::invalid_argument("HDR merge image shapes do not match");
    }
}

void validate_params(const HdrMergeParams& params) {
    if (params.short_exposure <= 0.0F || params.long_exposure <= 0.0F ||
        params.saturation_threshold <= 0.0F || params.saturation_threshold > 1.0F ||
        params.underexposure_threshold < 0.0F || params.underexposure_threshold >= 1.0F ||
        params.weight_epsilon <= 0.0F) {
        throw std::invalid_argument("invalid HDR merge parameters");
    }
}

float max_channel(const ImageView<const float>& image, std::uint32_t y, std::uint32_t x) {
    float value = image(y, x, 0);
    for (std::uint32_t c = 1; c < image.channels(); ++c) {
        value = std::max(value, image(y, x, c));
    }
    return value;
}

}  // namespace

float saturation_weight(float value, float threshold) {
    if (threshold <= 0.0F || threshold > 1.0F) {
        throw std::invalid_argument("saturation threshold must be in (0, 1]");
    }
    if (value <= threshold) {
        return 1.0F;
    }
    return clamp01((1.0F - value) / std::max(1.0F - threshold, 1.0e-6F));
}

float underexposure_weight(float value, float threshold) {
    if (threshold < 0.0F || threshold >= 1.0F) {
        throw std::invalid_argument("underexposure threshold must be in [0, 1)");
    }
    if (value >= threshold) {
        return 1.0F;
    }
    return clamp01(value / std::max(threshold, 1.0e-6F));
}

void hdr_merge_aligned(const ImageView<const float>& short_image,
                       const ImageView<const float>& long_image,
                       ImageView<float> output,
                       const HdrMergeParams& params) {
    validate_shapes(short_image, long_image, output);
    validate_params(params);

    for (std::uint32_t y = 0; y < short_image.height(); ++y) {
        for (std::uint32_t x = 0; x < short_image.width(); ++x) {
            const float short_quality = underexposure_weight(max_channel(short_image, y, x),
                                                            params.underexposure_threshold);
            const float long_quality = saturation_weight(max_channel(long_image, y, x),
                                                        params.saturation_threshold);
            const float weight_sum = short_quality + long_quality + params.weight_epsilon;

            for (std::uint32_t c = 0; c < short_image.channels(); ++c) {
                const float short_radiance = short_image(y, x, c) / params.short_exposure;
                const float long_radiance = long_image(y, x, c) / params.long_exposure;
                output(y, x, c) = (short_quality * short_radiance + long_quality * long_radiance) / weight_sum;
            }
        }
    }
}

}  // namespace cpp_isp
