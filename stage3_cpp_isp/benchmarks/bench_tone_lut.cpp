#include "cpp_isp/tone_lut.hpp"

#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <string>

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

template <typename Fn>
double time_ms(Fn&& fn, int repeats) {
    double best_ms = 1.0e30;
    for (int i = 0; i < repeats; ++i) {
        const auto begin = std::chrono::steady_clock::now();
        fn();
        const auto end = std::chrono::steady_clock::now();
        best_ms = std::min(best_ms, std::chrono::duration<double, std::milli>(end - begin).count());
    }
    return best_ms;
}

void run_case(std::uint32_t width,
              std::uint32_t height,
              cpp_isp::ToneCurve curve,
              const std::string& curve_name,
              bool preserve_luminance,
              std::uint32_t input_bits,
              std::uint32_t output_bits) {
    auto input = make_hdr_like_rgb(width, height);
    cpp_isp::ImageBuffer<float> output(width, height, 3);
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();

    cpp_isp::ToneLutParams params;
    params.curve = curve;
    params.exposure = cpp_isp::compute_percentile_exposure(input_view, 99.0F, 1.0F, true);
    params.preserve_luminance = preserve_luminance;
    params.input_bits = input_bits;
    params.output_bits = output_bits;
    params.input_max = 8.0F;
    cpp_isp::ToneCurveLut lut(params);

    const double ms = time_ms([&] { cpp_isp::tone_map_lut(input_view, output.view(), lut); }, 3);
    std::cout << curve_name << ','
              << (preserve_luminance ? "luma" : "rgb") << ','
              << input_bits << ','
              << output_bits << ','
              << width << ','
              << height << ','
              << std::fixed << std::setprecision(6) << params.exposure << ','
              << std::setprecision(3) << ms << '\n';
}

}  // namespace

int main() {
    std::cout << "curve,mode,input_bits,output_bits,width,height,exposure,ms\n";
    for (const auto& size : {std::pair<std::uint32_t, std::uint32_t>{1920, 1080},
                             std::pair<std::uint32_t, std::uint32_t>{3840, 2160}}) {
        run_case(size.first, size.second, cpp_isp::ToneCurve::Reinhard, "reinhard", true, 10, 10);
        run_case(size.first, size.second, cpp_isp::ToneCurve::Reinhard, "reinhard", true, 12, 12);
        run_case(size.first, size.second, cpp_isp::ToneCurve::Filmic, "filmic", true, 12, 12);
        run_case(size.first, size.second, cpp_isp::ToneCurve::SCurve, "scurve", true, 12, 12);
    }
    return 0;
}
