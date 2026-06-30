#include "cpp_isp/tone_mapping.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace cpp_isp {

namespace {

constexpr float kEpsilon = 1.0e-6F;

float clamp01(float value) {
    return std::min(std::max(value, 0.0F), 1.0F);
}

float luminance(float r, float g, float b) {
    return 0.2126F * r + 0.7152F * g + 0.0722F * b;
}

float hable_filmic_raw(float x) {
    // Hable/Uncharted 风格 filmic 曲线：高光压缩更柔和，避免 Reinhard 那种灰雾感。
    constexpr float a = 0.15F;
    constexpr float b = 0.50F;
    constexpr float c = 0.10F;
    constexpr float d = 0.20F;
    constexpr float e = 0.02F;
    constexpr float f = 0.30F;
    return ((x * (a * x + c * b) + d * e) / (x * (a * x + b) + d * f)) - e / f;
}

void validate_same_shape(const ImageView<const float>& input, const ImageView<float>& output) {
    if (input.width() != output.width() || input.height() != output.height() ||
        input.channels() != output.channels()) {
        throw std::invalid_argument("input and output shapes do not match");
    }
}

}  // namespace

float apply_tone_curve(float value, ToneCurve curve, float scurve_midpoint, float scurve_contrast) {
    const float x = std::max(value, 0.0F);
    switch (curve) {
        case ToneCurve::Reinhard:
            // x / (1 + x) 会把无限大的输入渐近压到 1，公式简单且单调。
            return x / (1.0F + x);
        case ToneCurve::Filmic: {
            constexpr float white_point = 11.2F;
            // 用 white_point 归一化，让该白点附近映射到 1。
            const float white_scale = 1.0F / hable_filmic_raw(white_point);
            return clamp01(hable_filmic_raw(x) * white_scale);
        }
        case ToneCurve::SCurve: {
            if (scurve_contrast <= 0.0F) {
                throw std::invalid_argument("scurve_contrast must be positive");
            }
            const float clamped = clamp01(x);
            const float y = 1.0F / (1.0F + std::exp(-scurve_contrast * (clamped - scurve_midpoint)));
            const float y0 = 1.0F / (1.0F + std::exp(scurve_contrast * scurve_midpoint));
            const float y1 = 1.0F / (1.0F + std::exp(-scurve_contrast * (1.0F - scurve_midpoint)));
            // 重新归一化端点，保证输入 0/1 附近仍映射到 0/1。
            return clamp01((y - y0) / std::max(y1 - y0, kEpsilon));
        }
    }
    return 0.0F;
}

float compute_percentile_exposure(const ImageView<const float>& input,
                                  float percentile,
                                  float target_value,
                                  bool use_luminance) {
    if (percentile < 0.0F || percentile > 100.0F || target_value <= 0.0F) {
        throw std::invalid_argument("invalid percentile exposure parameters");
    }

    std::vector<float> samples;
    samples.reserve(static_cast<std::size_t>(input.width()) * input.height());
    if (use_luminance && input.channels() >= 3) {
        // RGB 图像优先用亮度统计曝光，避免某个颜色通道异常主导曝光估计。
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                samples.push_back(luminance(input(y, x, 0), input(y, x, 1), input(y, x, 2)));
            }
        }
    } else {
        samples.reserve(static_cast<std::size_t>(input.width()) * input.height() * input.channels());
        for (std::uint32_t c = 0; c < input.channels(); ++c) {
            for (std::uint32_t y = 0; y < input.height(); ++y) {
                for (std::uint32_t x = 0; x < input.width(); ++x) {
                    samples.push_back(input(y, x, c));
                }
            }
        }
    }

    const auto rank = static_cast<std::size_t>(
        std::round((percentile / 100.0F) * static_cast<float>(samples.size() - 1)));
    // nth_element 只保证第 rank 个元素就位，比完整排序更快。
    std::nth_element(samples.begin(), samples.begin() + rank, samples.end());
    const float white = std::max(samples[rank], kEpsilon);
    return target_value / white;
}

void tone_map(const ImageView<const float>& input,
              ImageView<float> output,
              const ToneMappingParams& params) {
    validate_same_shape(input, output);
    if (params.exposure <= 0.0F) {
        throw std::invalid_argument("exposure must be positive");
    }

    if (params.preserve_luminance && input.channels() >= 3) {
        // 保亮度模式：先压缩 Y，再把 RGB 按同一个比例缩放，尽量保持原始色相。
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                const float r = input(y, x, 0);
                const float g = input(y, x, 1);
                const float b = input(y, x, 2);
                const float y_linear = luminance(r, g, b);
                const float y_mapped = apply_tone_curve(y_linear * params.exposure,
                                                        params.curve,
                                                        params.scurve_midpoint,
                                                        params.scurve_contrast);
                const float scale = y_mapped / std::max(y_linear, kEpsilon);
                output(y, x, 0) = clamp01(r * scale);
                output(y, x, 1) = clamp01(g * scale);
                output(y, x, 2) = clamp01(b * scale);
                for (std::uint32_t c = 3; c < input.channels(); ++c) {
                    output(y, x, c) = apply_tone_curve(input(y, x, c) * params.exposure,
                                                       params.curve,
                                                       params.scurve_midpoint,
                                                       params.scurve_contrast);
                }
            }
        }
        return;
    }

    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        // 非保亮度模式：每个通道独立进曲线，简单但可能改变颜色比例。
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                output(y, x, c) = apply_tone_curve(input(y, x, c) * params.exposure,
                                                   params.curve,
                                                   params.scurve_midpoint,
                                                   params.scurve_contrast);
            }
        }
    }
}

void apply_gamma(const ImageView<const float>& input,
                 ImageView<float> output,
                 float gamma) {
    validate_same_shape(input, output);
    if (gamma <= 0.0F) {
        throw std::invalid_argument("gamma must be positive");
    }

    const float inv_gamma = 1.0F / gamma;
    // 显示编码用 1/gamma 幂；输入先 clamp，避免负数 pow 或超过显示范围。
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                output(y, x, c) = std::pow(clamp01(input(y, x, c)), inv_gamma);
            }
        }
    }
}

}  // namespace cpp_isp
