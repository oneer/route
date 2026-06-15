#include "cpp_isp/denoise.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(float a, float b, float eps = 1e-6F) {
    return std::abs(a - b) <= eps;
}

void test_box_filter_constant_image() {
    cpp_isp::ImageBuffer<float> input(5, 5, 1);
    cpp_isp::ImageBuffer<float> output(5, 5, 1);
    for (auto& value : input.storage()) {
        value = 0.25F;
    }

    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::box_filter(input_view, output.view(), 1, cpp_isp::BorderPolicy::Replicate);

    for (std::uint32_t y = 0; y < output.height(); ++y) {
        for (std::uint32_t x = 0; x < output.width(); ++x) {
            require(near(output(y, x), 0.25F), "box filter should preserve constant image");
        }
    }
}

void test_box_filter_impulse_center() {
    cpp_isp::ImageBuffer<float> input(3, 3, 1);
    cpp_isp::ImageBuffer<float> output(3, 3, 1);
    input(1, 1) = 1.0F;

    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::box_filter(input_view, output.view(), 1, cpp_isp::BorderPolicy::Constant);

    for (std::uint32_t y = 0; y < output.height(); ++y) {
        for (std::uint32_t x = 0; x < output.width(); ++x) {
            require(near(output(y, x), 1.0F / 9.0F), "box impulse response mismatch");
        }
    }
}

void test_gaussian_kernel_normalized() {
    const auto kernel = cpp_isp::make_gaussian_kernel_1d(2, 1.2F);
    float sum = 0.0F;
    for (float value : kernel) {
        sum += value;
    }
    require(near(sum, 1.0F), "gaussian kernel must be normalized");
    require(near(kernel.front(), kernel.back()), "gaussian kernel must be symmetric");
}

}  // namespace

int main() {
    try {
        test_box_filter_constant_image();
        test_box_filter_impulse_center();
        test_gaussian_kernel_normalized();
        std::cout << "test_denoise_basic passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_denoise_basic failed: " << error.what() << '\n';
        return 1;
    }
}
