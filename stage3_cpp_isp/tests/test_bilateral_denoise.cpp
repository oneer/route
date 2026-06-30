#include "cpp_isp/denoise.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

// 双边滤波测试覆盖三件事：
// 1. 常量图不应被改变；2. 强边缘不应被跨边缘平均；3. LUT/分块/多线程优化应接近直接公式。
namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(float a, float b, float eps = 1e-5F) {
    return std::abs(a - b) <= eps;
}

void test_bilateral_preserves_constant_image() {
    cpp_isp::ImageBuffer<float> input(7, 7, 1);
    cpp_isp::ImageBuffer<float> output(7, 7, 1);
    for (auto& value : input.storage()) {
        value = 0.4F;
    }

    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::bilateral_filter(input_view, output.view(), 2, 1.5F, 0.1F, cpp_isp::BorderPolicy::Replicate);

    for (std::uint32_t y = 0; y < output.height(); ++y) {
        for (std::uint32_t x = 0; x < output.width(); ++x) {
            require(near(output(y, x), 0.4F), "bilateral should preserve constant image");
        }
    }
}

void test_bilateral_respects_strong_edge() {
    cpp_isp::ImageBuffer<float> input(5, 3, 1);
    cpp_isp::ImageBuffer<float> output(5, 3, 1);
    for (std::uint32_t y = 0; y < input.height(); ++y) {
        input(y, 0) = 0.0F;
        input(y, 1) = 0.0F;
        input(y, 2) = 1.0F;
        input(y, 3) = 1.0F;
        input(y, 4) = 1.0F;
    }

    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::bilateral_filter(input_view, output.view(), 1, 1.0F, 0.05F, cpp_isp::BorderPolicy::Replicate);

    require(output(1, 1) < 0.05F, "left side should not average across strong edge");
    require(output(1, 2) > 0.95F, "right side should not average across strong edge");
}

void test_lut_version_close_to_direct_version() {
    cpp_isp::ImageBuffer<float> input(5, 5, 1);
    cpp_isp::ImageBuffer<float> direct(5, 5, 1);
    cpp_isp::ImageBuffer<float> lut(5, 5, 1);
    for (std::uint32_t y = 0; y < input.height(); ++y) {
        for (std::uint32_t x = 0; x < input.width(); ++x) {
            input(y, x) = static_cast<float>(x + y) / 8.0F;
        }
    }

    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::bilateral_filter(input_view, direct.view(), 1, 1.2F, 0.2F, cpp_isp::BorderPolicy::Replicate);
    cpp_isp::bilateral_filter_range_lut(input_view, lut.view(), 1, 1.2F, 0.2F, 512, cpp_isp::BorderPolicy::Replicate);

    for (std::uint32_t y = 0; y < input.height(); ++y) {
        for (std::uint32_t x = 0; x < input.width(); ++x) {
            require(near(direct(y, x), lut(y, x), 5e-4F), "range LUT approximation too far");
        }
    }
}

void fill_pattern(cpp_isp::ImageBuffer<float>& image) {
    for (std::uint32_t y = 0; y < image.height(); ++y) {
        for (std::uint32_t x = 0; x < image.width(); ++x) {
            const float gradient = static_cast<float>(x + y * 2) / 63.0F;
            const float texture = static_cast<float>((x * 11 + y * 7) % 17) / 170.0F;
            image(y, x) = std::min(gradient + texture, 1.0F);
        }
    }
}

void require_images_close(const cpp_isp::ImageBuffer<float>& a,
                          const cpp_isp::ImageBuffer<float>& b,
                          float eps,
                          const char* message) {
    require(a.width() == b.width() && a.height() == b.height() && a.channels() == b.channels(),
            "shape mismatch in image comparison");
    for (std::uint32_t y = 0; y < a.height(); ++y) {
        for (std::uint32_t x = 0; x < a.width(); ++x) {
            require(near(a(y, x), b(y, x), eps), message);
        }
    }
}

void test_tiled_and_threaded_versions_match_lut_baseline() {
    cpp_isp::ImageBuffer<float> input(23, 19, 1);
    cpp_isp::ImageBuffer<float> baseline(23, 19, 1);
    cpp_isp::ImageBuffer<float> tiled(23, 19, 1);
    cpp_isp::ImageBuffer<float> rows(23, 19, 1);
    cpp_isp::ImageBuffer<float> tiles(23, 19, 1);
    fill_pattern(input);

    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::bilateral_filter_range_lut(input_view,
                                        baseline.view(),
                                        2,
                                        1.5F,
                                        0.12F,
                                        512,
                                        cpp_isp::BorderPolicy::Replicate);
    cpp_isp::bilateral_filter_range_lut_tiled(input_view,
                                             tiled.view(),
                                             2,
                                             1.5F,
                                             0.12F,
                                             512,
                                             cpp_isp::BorderPolicy::Replicate,
                                             7,
                                             5);
    cpp_isp::bilateral_filter_range_lut_threaded_rows(input_view,
                                                      rows.view(),
                                                      2,
                                                      1.5F,
                                                      0.12F,
                                                      512,
                                                      cpp_isp::BorderPolicy::Replicate,
                                                      3);
    cpp_isp::bilateral_filter_range_lut_threaded_tiles(input_view,
                                                       tiles.view(),
                                                       2,
                                                       1.5F,
                                                       0.12F,
                                                       512,
                                                       cpp_isp::BorderPolicy::Replicate,
                                                       8,
                                                       6,
                                                       4);

    require_images_close(baseline, tiled, 1e-6F, "tiled LUT output mismatch");
    require_images_close(baseline, rows, 1e-6F, "row-threaded LUT output mismatch");
    require_images_close(baseline, tiles, 1e-6F, "tile-threaded LUT output mismatch");
}

}  // namespace

int main() {
    try {
        test_bilateral_preserves_constant_image();
        test_bilateral_respects_strong_edge();
        test_lut_version_close_to_direct_version();
        test_tiled_and_threaded_versions_match_lut_baseline();
        std::cout << "test_bilateral_denoise passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_bilateral_denoise failed: " << error.what() << '\n';
        return 1;
    }
}
