#include "cpp_isp/local_tone_mapping.hpp"
#include "benchmark_utils.hpp"

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <string>

// 局部 tone mapping benchmark：比较 box base 与 bilateral base 在不同半径/分辨率下的耗时。
namespace {

cpp_isp::ImageBuffer<float> make_hdr_like_rgb(std::uint32_t width, std::uint32_t height) {
    cpp_isp::ImageBuffer<float> image(width, height, 3);
    // 合成一个 HDR-like 场景：渐变背景 + 右上角高亮窗口，用来触发动态范围压缩路径。
    for (std::uint32_t y = 0; y < height; ++y) {
        for (std::uint32_t x = 0; x < width; ++x) {
            const float gx = static_cast<float>(x) / static_cast<float>(std::max(1U, width - 1U));
            const float gy = static_cast<float>(y) / static_cast<float>(std::max(1U, height - 1U));
            const float window = (x > width * 3U / 5U && y < height / 3U) ? 4.5F : 0.0F;
            image(y, x, 0) = 0.1F + 3.0F * gx + window;
            image(y, x, 1) = 0.08F + 2.4F * gy + window * 0.85F;
            image(y, x, 2) = 0.12F + 1.5F * (1.0F - gx) + window * 0.65F;
        }
    }
    return image;
}

void run_case(std::uint32_t width,
              std::uint32_t height,
              cpp_isp::LocalBaseFilter filter,
              const std::string& filter_name,
              std::uint32_t radius) {
    auto input = make_hdr_like_rgb(width, height);
    cpp_isp::ImageBuffer<float> output(width, height, 3);
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();

    cpp_isp::LocalToneMappingParams params;
    params.curve = cpp_isp::ToneCurve::Reinhard;
    params.exposure = 0.25F;
    params.base_filter = filter;
    params.base_radius = radius;
    params.base_sigma_spatial = static_cast<float>(std::max(1U, radius)) * 0.8F;
    params.base_sigma_range = 0.35F;
    params.detail_strength = 0.75F;

    const double ms = cpp_isp_bench::median_ms(
        [&] { cpp_isp::local_tone_map(input_view, output.view(), params); }, 1, 3);
    std::cout << filter_name << ','
              << radius << ','
              << width << ','
              << height << ','
              << std::fixed << std::setprecision(3) << ms << '\n';
}

}  // namespace

int main() {
    std::cout << "base_filter,radius,width,height,ms\n";
    run_case(640, 360, cpp_isp::LocalBaseFilter::Box, "box", 5);
    run_case(640, 360, cpp_isp::LocalBaseFilter::Box, "box", 9);
    run_case(640, 360, cpp_isp::LocalBaseFilter::Bilateral, "bilateral", 3);
    run_case(640, 360, cpp_isp::LocalBaseFilter::Bilateral, "bilateral", 5);
    run_case(1920, 1080, cpp_isp::LocalBaseFilter::Box, "box", 5);
    run_case(1920, 1080, cpp_isp::LocalBaseFilter::Bilateral, "bilateral", 1);
    return 0;
}
