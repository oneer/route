#include "cpp_isp/denoise.hpp"
#include "benchmark_utils.hpp"

#include <iostream>

namespace {

cpp_isp::ImageBuffer<float> make_gradient_noise(std::uint32_t width, std::uint32_t height) {
    cpp_isp::ImageBuffer<float> image(width, height, 1);
    for (std::uint32_t y = 0; y < height; ++y) {
        for (std::uint32_t x = 0; x < width; ++x) {
            const float gradient = static_cast<float>(x) / static_cast<float>(width - 1);
            const float pattern = static_cast<float>((x * 13 + y * 17) % 37) / 370.0F;
            image(y, x) = gradient + pattern;
        }
    }
    return image;
}

}  // namespace

int main() {
    for (const auto size : {128U, 256U}) {
        auto input = make_gradient_noise(size, size);
        cpp_isp::ImageBuffer<float> output(size, size, 1);
        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();

        const double direct_ms = cpp_isp_bench::median_ms([&] {
            cpp_isp::bilateral_filter(input_view, output.view(), 2, 1.5F, 0.08F,
                                      cpp_isp::BorderPolicy::Replicate);
        }, 1, 5);
        const double lut_ms = cpp_isp_bench::median_ms([&] {
            cpp_isp::bilateral_filter_range_lut(input_view, output.view(), 2, 1.5F, 0.08F, 512,
                                                cpp_isp::BorderPolicy::Replicate);
        }, 1, 5);

        std::cout << "size=" << size << "x" << size
                  << " direct_ms=" << direct_ms
                  << " lut_ms=" << lut_ms << '\n';
    }
    return 0;
}
