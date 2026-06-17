#include "cpp_isp/local_tone_mapping.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(float a, float b, float eps = 1e-5F) {
    return std::abs(a - b) <= eps;
}

void test_constant_image_has_constant_base() {
    cpp_isp::ImageBuffer<float> input(7, 5, 3);
    cpp_isp::ImageBuffer<float> base(7, 5, 1);
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                input(y, x, c) = 0.4F;
            }
        }
    }

    cpp_isp::LocalToneMappingParams params;
    params.base_radius = 2;
    params.base_filter = cpp_isp::LocalBaseFilter::Box;
    const auto view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::estimate_luminance_base(view, base.view(), params);

    for (std::uint32_t y = 0; y < base.height(); ++y) {
        for (std::uint32_t x = 0; x < base.width(); ++x) {
            require(near(base(y, x), 0.4F), "constant image base should be constant");
        }
    }
}

void test_ltm_compresses_highlight() {
    cpp_isp::ImageBuffer<float> input(9, 9, 3);
    cpp_isp::ImageBuffer<float> output(9, 9, 3);
    for (std::uint32_t y = 0; y < input.height(); ++y) {
        for (std::uint32_t x = 0; x < input.width(); ++x) {
            const float value = (x == 4 && y == 4) ? 4.0F : 0.4F;
            input(y, x, 0) = value;
            input(y, x, 1) = value;
            input(y, x, 2) = value;
        }
    }

    cpp_isp::LocalToneMappingParams params;
    params.curve = cpp_isp::ToneCurve::Reinhard;
    params.exposure = 1.0F;
    params.base_radius = 1;
    params.detail_strength = 0.6F;
    const auto view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::local_tone_map(view, output.view(), params);

    require(output(4, 4, 0) <= 1.0F, "highlight should be display bounded");
    require(output(4, 4, 0) > output(0, 0, 0), "highlight should remain brighter than background");
}

void test_bilateral_base_preserves_step_more_than_box() {
    cpp_isp::ImageBuffer<float> input(9, 1, 1);
    cpp_isp::ImageBuffer<float> box_base(9, 1, 1);
    cpp_isp::ImageBuffer<float> bilateral_base(9, 1, 1);
    for (std::uint32_t x = 0; x < input.width(); ++x) {
        input(0, x) = x < 4 ? 0.1F : 1.0F;
    }

    cpp_isp::LocalToneMappingParams box_params;
    box_params.base_radius = 2;
    box_params.base_filter = cpp_isp::LocalBaseFilter::Box;
    cpp_isp::LocalToneMappingParams bilateral_params = box_params;
    bilateral_params.base_filter = cpp_isp::LocalBaseFilter::Bilateral;
    bilateral_params.base_sigma_range = 0.1F;

    const auto view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::estimate_luminance_base(view, box_base.view(), box_params);
    cpp_isp::estimate_luminance_base(view, bilateral_base.view(), bilateral_params);

    require(std::abs(bilateral_base(0, 3) - input(0, 3)) < std::abs(box_base(0, 3) - input(0, 3)),
            "bilateral base should leak less across edge than box base");
}

}  // namespace

int main() {
    try {
        test_constant_image_has_constant_base();
        test_ltm_compresses_highlight();
        test_bilateral_base_preserves_step_more_than_box();
        std::cout << "test_local_tone_mapping passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_local_tone_mapping failed: " << error.what() << '\n';
        return 1;
    }
}
