#include "cpp_isp/image_fusion.hpp"

#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <vector>

namespace {

double percentile(std::vector<double> values, double q) {
    std::sort(values.begin(), values.end());
    const std::size_t index = static_cast<std::size_t>(q * static_cast<double>(values.size() - 1));
    return values[index];
}

void run_case(std::uint32_t width, std::uint32_t height) {
    cpp_isp::ImageBuffer<float> left(width, height, 3);
    cpp_isp::ImageBuffer<float> right(width, height, 3);
    cpp_isp::ImageBuffer<float> matched(width, height, 3);
    cpp_isp::ImageBuffer<float> output(width, height, 3);
    for (std::uint32_t y = 0; y < height; ++y) {
        for (std::uint32_t x = 0; x < width; ++x) {
            const float value = static_cast<float>(x + y) / static_cast<float>(width + height);
            for (std::uint32_t c = 0; c < 3; ++c) {
                left(y, x, c) = value;
                right(y, x, c) = value * (0.88F + 0.02F * static_cast<float>(c));
            }
        }
    }
    const auto left_view = static_cast<const cpp_isp::ImageBuffer<float>&>(left).view();
    const auto right_view = static_cast<const cpp_isp::ImageBuffer<float>&>(right).view();
    const std::uint32_t x_begin = width / 3U;
    const std::uint32_t x_end = width * 2U / 3U;
    const auto gains = cpp_isp::estimate_overlap_color_gains(left_view, right_view, x_begin, x_end);
    auto run = [&] {
        cpp_isp::apply_channel_gains(right_view, matched.view(), gains);
        const auto matched_view = static_cast<const cpp_isp::ImageBuffer<float>&>(matched).view();
        cpp_isp::feather_blend_aligned(left_view, matched_view, output.view(), x_begin, x_end);
    };
    run();
    std::vector<double> samples;
    samples.reserve(20);
    for (int iteration = 0; iteration < 20; ++iteration) {
        const auto start = std::chrono::steady_clock::now();
        run();
        const auto stop = std::chrono::steady_clock::now();
        samples.push_back(std::chrono::duration<double, std::milli>(stop - start).count());
    }
    std::cout << width << ',' << height << ",3,1,20," << std::fixed << std::setprecision(3)
              << percentile(samples, 0.50) << ',' << percentile(samples, 0.90) << '\n';
}

}  // namespace

int main() {
    std::cout << "width,height,channels,warmup_runs,timed_runs,p50_ms,p90_ms\n";
    run_case(1920, 1080);
    run_case(3840, 2160);
    return 0;
}
