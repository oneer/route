#include "cpp_isp/hdr_merge.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

// HDR 合成测试验证权重函数，以及在未饱和/长曝光饱和两种典型场景下的 radiance 恢复。
namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(float a, float b, float eps = 1e-5F) {
    return std::abs(a - b) <= eps;
}

void test_weight_helpers() {
    require(near(cpp_isp::saturation_weight(0.5F, 0.9F), 1.0F), "unsaturated value should keep weight");
    require(near(cpp_isp::saturation_weight(1.0F, 0.9F), 0.0F), "saturated value should lose weight");
    require(near(cpp_isp::underexposure_weight(0.0F, 0.1F), 0.0F), "black short frame should lose weight");
    require(near(cpp_isp::underexposure_weight(0.2F, 0.1F), 1.0F), "valid short frame should keep weight");
}

void test_merge_recovers_radiance_when_not_clipped() {
    cpp_isp::ImageBuffer<float> short_image(1, 1, 3);
    cpp_isp::ImageBuffer<float> long_image(1, 1, 3);
    cpp_isp::ImageBuffer<float> output(1, 1, 3);
    cpp_isp::HdrMergeParams params;
    params.short_exposure = 0.25F;
    params.long_exposure = 1.0F;

    for (std::uint32_t c = 0; c < 3; ++c) {
        short_image(0, 0, c) = 0.2F;
        long_image(0, 0, c) = 0.8F;
    }

    const auto short_view = static_cast<const cpp_isp::ImageBuffer<float>&>(short_image).view();
    const auto long_view = static_cast<const cpp_isp::ImageBuffer<float>&>(long_image).view();
    cpp_isp::hdr_merge_aligned(short_view, long_view, output.view(), params);
    require(near(output(0, 0, 0), 0.8F, 1e-4F), "aligned merge should recover radiance");
}

void test_merge_uses_short_when_long_saturates() {
    cpp_isp::ImageBuffer<float> short_image(1, 1, 1);
    cpp_isp::ImageBuffer<float> long_image(1, 1, 1);
    cpp_isp::ImageBuffer<float> output(1, 1, 1);
    cpp_isp::HdrMergeParams params;
    params.short_exposure = 0.25F;
    params.long_exposure = 1.0F;
    params.saturation_threshold = 0.9F;

    short_image(0, 0) = 0.25F;
    long_image(0, 0) = 1.0F;

    const auto short_view = static_cast<const cpp_isp::ImageBuffer<float>&>(short_image).view();
    const auto long_view = static_cast<const cpp_isp::ImageBuffer<float>&>(long_image).view();
    cpp_isp::hdr_merge_aligned(short_view, long_view, output.view(), params);
    require(near(output(0, 0), 1.0F, 1e-4F), "saturated long frame should defer to short radiance");
}

}  // namespace

int main() {
    try {
        test_weight_helpers();
        test_merge_recovers_radiance_when_not_clipped();
        test_merge_uses_short_when_long_saturates();
        std::cout << "test_hdr_merge passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_hdr_merge failed: " << error.what() << '\n';
        return 1;
    }
}
