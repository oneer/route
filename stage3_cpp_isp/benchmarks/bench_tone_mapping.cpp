#include "cpp_isp/tone_mapping.hpp"
#include "benchmark_utils.hpp"

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {

cpp_isp::ImageBuffer<float> make_hdr_like_rgb(std::uint32_t width, std::uint32_t height) {
    cpp_isp::ImageBuffer<float> image(width, height, 3);
    for (std::uint32_t y = 0; y < height; ++y) {
        for (std::uint32_t x = 0; x < width; ++x) {
            const float gx = static_cast<float>(x) / static_cast<float>(std::max(1U, width - 1U));
            const float gy = static_cast<float>(y) / static_cast<float>(std::max(1U, height - 1U));
            const float highlight = (x > width * 3U / 5U && y < height / 3U) ? 4.0F : 0.0F;
            image(y, x, 0) = 0.2F + 3.0F * gx + highlight;
            image(y, x, 1) = 0.15F + 2.0F * gy + highlight * 0.85F;
            image(y, x, 2) = 0.12F + 1.2F * (1.0F - gx) + highlight * 0.65F;
        }
    }
    return image;
}

void run_case(std::uint32_t width,
              std::uint32_t height,
              cpp_isp::ToneCurve curve,
              const std::string& curve_name,
              bool preserve_luminance) {
    auto input = make_hdr_like_rgb(width, height);
    cpp_isp::ImageBuffer<float> output(width, height, 3);
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();

    cpp_isp::ToneMappingParams params;
    params.curve = curve;
    params.exposure = cpp_isp::compute_percentile_exposure(input_view, 99.0F, 1.0F, true);
    params.preserve_luminance = preserve_luminance;

    const double ms = cpp_isp_bench::median_ms(
        [&] { cpp_isp::tone_map(input_view, output.view(), params); }, 1, 5);
    std::cout << curve_name << ','
              << (preserve_luminance ? "luma" : "rgb") << ','
              << width << ','
              << height << ','
              << std::fixed << std::setprecision(6) << params.exposure << ','
              << std::setprecision(3) << ms << '\n';
}

}  // namespace

int main() {
    std::cout << "curve,mode,width,height,exposure,ms\n";
    for (const auto& size : {std::pair<std::uint32_t, std::uint32_t>{1920, 1080},
                             std::pair<std::uint32_t, std::uint32_t>{3840, 2160}}) {
        run_case(size.first, size.second, cpp_isp::ToneCurve::Reinhard, "reinhard", false);
        run_case(size.first, size.second, cpp_isp::ToneCurve::Reinhard, "reinhard", true);
        run_case(size.first, size.second, cpp_isp::ToneCurve::Filmic, "filmic", true);
        run_case(size.first, size.second, cpp_isp::ToneCurve::SCurve, "scurve", true);
    }
    return 0;
}
