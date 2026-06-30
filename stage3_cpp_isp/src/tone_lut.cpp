#include "cpp_isp/tone_lut.hpp"

#include "cpp_isp/fixed_point.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cpp_isp {

namespace {

constexpr float kEpsilon = 1.0e-6F;

float clamp01(float value) {
    return std::min(std::max(value, 0.0F), 1.0F);
}

float luminance(float r, float g, float b) {
    return 0.2126F * r + 0.7152F * g + 0.0722F * b;
}

void validate_lut_params(const ToneLutParams& params) {
    if (params.input_bits < 2 || params.input_bits > 16) {
        throw std::invalid_argument("input_bits must be in [2, 16]");
    }
    if (params.output_bits < 2 || params.output_bits > 16) {
        throw std::invalid_argument("output_bits must be in [2, 16]");
    }
    if (params.input_max <= 0.0F || params.exposure <= 0.0F) {
        throw std::invalid_argument("input_max and exposure must be positive");
    }
}

void validate_same_shape(const ImageView<const float>& input, const ImageView<float>& output) {
    if (input.width() != output.width() || input.height() != output.height() ||
        input.channels() != output.channels()) {
        throw std::invalid_argument("input and output shapes do not match");
    }
}

}  // namespace

ToneCurveLut::ToneCurveLut(const ToneLutParams& params) : params_(params) {
    validate_lut_params(params_);
    input_max_code_ = max_value_for_bits(params_.input_bits);
    output_max_code_ = max_value_for_bits(params_.output_bits);
    // input_scale: 线性浮点值 -> 输入码值；output_inv_scale: 输出码值 -> [0,1] 浮点值。
    input_scale_ = static_cast<float>(input_max_code_) / params_.input_max;
    output_inv_scale_ = 1.0F / static_cast<float>(output_max_code_);
    values_.resize(static_cast<std::size_t>(input_max_code_) + 1U);

    for (std::uint32_t code = 0; code <= input_max_code_; ++code) {
        // 遍历每个输入码值，反量化到线性域，套用浮点 tone curve，再量化成输出码值。
        const float x = (static_cast<float>(code) / static_cast<float>(input_max_code_)) * params_.input_max;
        const float y = apply_tone_curve(x,
                                         params_.curve,
                                         params_.scurve_midpoint,
                                         params_.scurve_contrast);
        const auto quantized = static_cast<std::int64_t>(
            std::llround(static_cast<double>(clamp01(y)) * output_max_code_));
        values_[code] = saturate_to_bits(quantized, params_.output_bits);
    }
}

std::uint32_t ToneCurveLut::apply_code(float value) const {
    const float clamped = std::min(std::max(value, 0.0F), params_.input_max);
    // +0.5F 做最近整数取整，减少直接截断带来的系统性偏暗。
    const auto code = static_cast<std::uint32_t>(clamped * input_scale_ + 0.5F);
    return values_[std::min(code, input_max_code_)];
}

float ToneCurveLut::apply(float value) const {
    return static_cast<float>(apply_code(value)) * output_inv_scale_;
}

void tone_map_lut(const ImageView<const float>& input,
                  ImageView<float> output,
                  const ToneCurveLut& lut) {
    validate_same_shape(input, output);
    const auto& params = lut.params();

    if (params.preserve_luminance && input.channels() >= 3) {
        // LUT 路径和浮点 tone_map 保持同样的“压缩亮度、缩放 RGB”语义。
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                const float r = input(y, x, 0);
                const float g = input(y, x, 1);
                const float b = input(y, x, 2);
                const float y_linear = luminance(r, g, b);
                const float y_mapped = lut.apply(y_linear * params.exposure);
                const float scale = y_mapped / std::max(y_linear, kEpsilon);
                output(y, x, 0) = clamp01(r * scale);
                output(y, x, 1) = clamp01(g * scale);
                output(y, x, 2) = clamp01(b * scale);
                for (std::uint32_t c = 3; c < input.channels(); ++c) {
                    output(y, x, c) = lut.apply(input(y, x, c) * params.exposure);
                }
            }
        }
        return;
    }

    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                output(y, x, c) = lut.apply(input(y, x, c) * params.exposure);
            }
        }
    }
}

}  // namespace cpp_isp
