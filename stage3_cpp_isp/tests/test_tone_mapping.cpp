#include "cpp_isp/tone_mapping.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

// 浮点 tone mapping 测试覆盖曲线单调性、已知值、百分位曝光、保亮度和 gamma 编码。
namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(float a, float b, float eps = 1e-5F) {
    return std::abs(a - b) <= eps;
}

void test_curves_are_monotonic() {
    for (const auto curve : {cpp_isp::ToneCurve::Reinhard, cpp_isp::ToneCurve::Filmic, cpp_isp::ToneCurve::SCurve}) {
        float prev = cpp_isp::apply_tone_curve(0.0F, curve);
        for (int i = 1; i <= 100; ++i) {
            const float x = static_cast<float>(i) / 10.0F;
            const float y = cpp_isp::apply_tone_curve(x, curve);
            require(y + 1e-6F >= prev, "tone curve should be monotonic");
            require(y >= 0.0F && y <= 1.0F, "tone curve output should stay in [0, 1]");
            prev = y;
        }
    }
}

void test_reinhard_known_values() {
    require(near(cpp_isp::apply_tone_curve(0.0F, cpp_isp::ToneCurve::Reinhard), 0.0F),
            "Reinhard zero failed");
    require(near(cpp_isp::apply_tone_curve(1.0F, cpp_isp::ToneCurve::Reinhard), 0.5F),
            "Reinhard one failed");
    require(near(cpp_isp::apply_tone_curve(3.0F, cpp_isp::ToneCurve::Reinhard), 0.75F),
            "Reinhard three failed");
}

void test_percentile_exposure() {
    cpp_isp::ImageBuffer<float> image(5, 1, 1);
    image(0, 0) = 0.1F;
    image(0, 1) = 0.2F;
    image(0, 2) = 0.4F;
    image(0, 3) = 0.8F;
    image(0, 4) = 1.6F;

    const auto view = static_cast<const cpp_isp::ImageBuffer<float>&>(image).view();
    const float exposure = cpp_isp::compute_percentile_exposure(view, 75.0F, 1.0F, false);
    require(near(exposure, 1.25F), "percentile exposure should map p75 to target");
}

void test_luminance_preserve_keeps_color_ratio() {
    cpp_isp::ImageBuffer<float> input(1, 1, 3);
    cpp_isp::ImageBuffer<float> output(1, 1, 3);
    input(0, 0, 0) = 0.4F;
    input(0, 0, 1) = 0.2F;
    input(0, 0, 2) = 0.1F;

    cpp_isp::ToneMappingParams params;
    params.curve = cpp_isp::ToneCurve::Reinhard;
    params.exposure = 2.0F;
    params.preserve_luminance = true;
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::tone_map(input_view, output.view(), params);

    require(output(0, 0, 0) > output(0, 0, 1), "red should remain strongest");
    require(output(0, 0, 1) > output(0, 0, 2), "green should remain above blue");
    require(near(output(0, 0, 0) / output(0, 0, 1), 2.0F, 1e-4F), "R/G ratio should be preserved");
    require(near(output(0, 0, 1) / output(0, 0, 2), 2.0F, 1e-4F), "G/B ratio should be preserved");
}

void test_gamma() {
    cpp_isp::ImageBuffer<float> input(1, 1, 1);
    cpp_isp::ImageBuffer<float> output(1, 1, 1);
    input(0, 0) = 0.25F;

    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::apply_gamma(input_view, output.view(), 2.0F);
    require(near(output(0, 0), 0.5F), "gamma correction failed");
}

}  // namespace

int main() {
    try {
        test_curves_are_monotonic();
        test_reinhard_known_values();
        test_percentile_exposure();
        test_luminance_preserve_keeps_color_ratio();
        test_gamma();
        std::cout << "test_tone_mapping passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_tone_mapping failed: " << error.what() << '\n';
        return 1;
    }
}
