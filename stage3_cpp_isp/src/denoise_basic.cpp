#include "cpp_isp/denoise.hpp"

#include <cmath>
#include <stdexcept>

namespace cpp_isp {

namespace {

void validate_same_shape(const ImageView<const float>& input, const ImageView<float>& output) {
    if (input.width() != output.width() || input.height() != output.height() ||
        input.channels() != output.channels()) {
        throw std::invalid_argument("input and output shapes do not match");
    }
}

}  // namespace

void box_filter(const ImageView<const float>& input,
                ImageView<float> output,
                std::uint32_t radius,
                BorderPolicy border_policy) {
    validate_same_shape(input, output);
    const int r = static_cast<int>(radius);
    // 窗口大小是 (2r + 1)^2，box filter 对窗口内每个样本给相同权重。
    const float norm = 1.0F / static_cast<float>((2 * r + 1) * (2 * r + 1));

    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                float sum = 0.0F;
                for (int dy = -r; dy <= r; ++dy) {
                    for (int dx = -r; dx <= r; ++dx) {
                        sum += sample_with_border(input,
                                                  static_cast<int>(y) + dy,
                                                  static_cast<int>(x) + dx,
                                                  c,
                                                  border_policy,
                                                  0.0F);
                    }
                }
                output(y, x, c) = sum * norm;
            }
        }
    }
}

std::vector<float> make_gaussian_kernel_1d(std::uint32_t radius, float sigma) {
    if (sigma <= 0.0F) {
        throw std::invalid_argument("sigma must be positive");
    }

    const int r = static_cast<int>(radius);
    std::vector<float> kernel(static_cast<std::size_t>(2 * r + 1));
    float sum = 0.0F;
    for (int i = -r; i <= r; ++i) {
        // 高斯权重 exp(-x^2 / 2sigma^2)，距离中心越远贡献越小。
        const float value = std::exp(-0.5F * static_cast<float>(i * i) / (sigma * sigma));
        kernel[static_cast<std::size_t>(i + r)] = value;
        sum += value;
    }
    for (float& value : kernel) {
        // 归一化后常量图像仍保持原值，不会整体变亮或变暗。
        value /= sum;
    }
    return kernel;
}

void gaussian_filter(const ImageView<const float>& input,
                     ImageView<float> output,
                     std::uint32_t radius,
                     float sigma,
                     BorderPolicy border_policy) {
    validate_same_shape(input, output);
    const auto kernel = make_gaussian_kernel_1d(radius, sigma);
    const int r = static_cast<int>(radius);

    ImageBuffer<float> temp(input.width(), input.height(), input.channels(), input.row_stride());
    auto temp_view = temp.view();

    // 高斯核可分离：先横向卷积写入 temp，再纵向卷积写入 output。
    // 复杂度从 O(radius^2) 降到 O(radius)，这也是 ISP 里常见的实现方式。
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                float sum = 0.0F;
                for (int dx = -r; dx <= r; ++dx) {
                    sum += kernel[static_cast<std::size_t>(dx + r)] *
                           sample_with_border(input,
                                              static_cast<int>(y),
                                              static_cast<int>(x) + dx,
                                              c,
                                              border_policy,
                                              0.0F);
                }
                temp_view(y, x, c) = sum;
            }
        }
    }

    const auto temp_const = static_cast<const ImageBuffer<float>&>(temp).view();
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                float sum = 0.0F;
                for (int dy = -r; dy <= r; ++dy) {
                    sum += kernel[static_cast<std::size_t>(dy + r)] *
                           sample_with_border(temp_const,
                                              static_cast<int>(y) + dy,
                                              static_cast<int>(x),
                                              c,
                                              border_policy,
                                              0.0F);
                }
                output(y, x, c) = sum;
            }
        }
    }
}

}  // namespace cpp_isp
