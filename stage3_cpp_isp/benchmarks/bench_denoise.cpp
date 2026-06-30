#include "cpp_isp/denoise.hpp"
#include "benchmark_utils.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

// 更完整的 bilateral 性能基准：比较 direct/LUT/tile/rows/tiles，并输出 CSV 方便报告画图。
namespace {

struct BenchCase {
    std::uint32_t width;
    std::uint32_t height;
    bool include_direct;
};

cpp_isp::ImageBuffer<float> make_bench_input(std::uint32_t width, std::uint32_t height) {
    cpp_isp::ImageBuffer<float> image(width, height, 1);
    for (std::uint32_t y = 0; y < height; ++y) {
        for (std::uint32_t x = 0; x < width; ++x) {
            const float gx = static_cast<float>(x) / static_cast<float>(std::max(1U, width - 1U));
            const float gy = static_cast<float>(y) / static_cast<float>(std::max(1U, height - 1U));
            const float texture = static_cast<float>((x * 13U + y * 17U) % 41U) / 410.0F;
            image(y, x) = std::min(0.65F * gx + 0.25F * gy + texture, 1.0F);
        }
    }
    return image;
}

double max_abs_diff(const cpp_isp::ImageBuffer<float>& a, const cpp_isp::ImageBuffer<float>& b) {
    double max_diff = 0.0;
    for (std::size_t i = 0; i < a.storage().size(); ++i) {
        max_diff = std::max(max_diff, std::abs(static_cast<double>(a.storage()[i] - b.storage()[i])));
    }
    return max_diff;
}

void print_row(const std::string& method,
               std::uint32_t width,
               std::uint32_t height,
               std::uint32_t tile_width,
               std::uint32_t tile_height,
               std::uint32_t threads,
               double ms,
               double speedup,
               double efficiency,
               double max_abs_vs_lut) {
    std::cout << method << ','
              << width << ','
              << height << ','
              << tile_width << ','
              << tile_height << ','
              << threads << ','
              << std::fixed << std::setprecision(3) << ms << ','
              << std::setprecision(4) << speedup << ','
              << std::setprecision(4) << efficiency << ','
              << std::scientific << std::setprecision(6) << max_abs_vs_lut << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    const bool full = argc > 1 && std::string(argv[1]) == "--full";
    // 默认模式跑预览尺寸，--full 才跑 1080p/4K，避免日常验证太慢。
    constexpr int warmup_runs = 1;
    const int measured_runs = full ? 3 : 5;
    const std::vector<BenchCase> cases = full
        ? std::vector<BenchCase>{{256, 256, true}, {1920, 1080, false}, {3840, 2160, false}}
        : std::vector<BenchCase>{{256, 256, true}, {960, 540, false}};
    const std::vector<std::uint32_t> thread_counts = full
        ? std::vector<std::uint32_t>{1, 2, 4, 8}
        : std::vector<std::uint32_t>{1, 2, 4};
    const std::vector<std::pair<std::uint32_t, std::uint32_t>> tile_sizes = {
        {64, 64},
        {128, 64},
        {128, 128},
    };

    std::cout << "method,width,height,tile_width,tile_height,threads,ms,speedup,efficiency,max_abs_vs_lut\n";
    for (const auto& bench_case : cases) {
        auto input = make_bench_input(bench_case.width, bench_case.height);
        cpp_isp::ImageBuffer<float> output(bench_case.width, bench_case.height, 1);
        cpp_isp::ImageBuffer<float> lut_output(bench_case.width, bench_case.height, 1);
        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();

        double direct_ms = 0.0;
        if (bench_case.include_direct) {
            direct_ms = cpp_isp_bench::median_ms([&] {
                cpp_isp::bilateral_filter(input_view,
                                          output.view(),
                                          2,
                                          1.5F,
                                          0.08F,
                                          cpp_isp::BorderPolicy::Replicate);
            }, warmup_runs, measured_runs);
            print_row("direct", bench_case.width, bench_case.height, 0, 0, 1, direct_ms, 1.0, 1.0, 0.0);
        }

        const double lut_ms = cpp_isp_bench::median_ms([&] {
            cpp_isp::bilateral_filter_range_lut(input_view,
                                                lut_output.view(),
                                                2,
                                                1.5F,
                                                0.08F,
                                                512,
                                                cpp_isp::BorderPolicy::Replicate);
        }, warmup_runs, measured_runs);
        print_row("lut", bench_case.width, bench_case.height, 0, 0, 1, lut_ms, 1.0, 1.0, 0.0);

        if (bench_case.include_direct) {
            print_row("direct_vs_lut_speedup",
                      bench_case.width,
                      bench_case.height,
                      0,
                      0,
                      1,
                      lut_ms,
                      direct_ms / lut_ms,
                      direct_ms / lut_ms,
                      max_abs_diff(output, lut_output));
        }

        for (const auto& tile_size : tile_sizes) {
            cpp_isp::ImageBuffer<float> tiled_output(bench_case.width, bench_case.height, 1);
            const double tiled_ms = cpp_isp_bench::median_ms([&] {
                cpp_isp::bilateral_filter_range_lut_tiled(input_view,
                                                         tiled_output.view(),
                                                         2,
                                                         1.5F,
                                                         0.08F,
                                                         512,
                                                         cpp_isp::BorderPolicy::Replicate,
                                                         tile_size.first,
                                                         tile_size.second);
            }, warmup_runs, measured_runs);
            print_row("tile_lut",
                      bench_case.width,
                      bench_case.height,
                      tile_size.first,
                      tile_size.second,
                      1,
                      tiled_ms,
                      lut_ms / tiled_ms,
                      lut_ms / tiled_ms,
                      max_abs_diff(lut_output, tiled_output));
        }

        for (const auto threads : thread_counts) {
            cpp_isp::ImageBuffer<float> row_output(bench_case.width, bench_case.height, 1);
            const double row_ms = cpp_isp_bench::median_ms([&] {
                cpp_isp::bilateral_filter_range_lut_threaded_rows(input_view,
                                                                  row_output.view(),
                                                                  2,
                                                                  1.5F,
                                                                  0.08F,
                                                                  512,
                                                                  cpp_isp::BorderPolicy::Replicate,
                                                                  threads);
            }, warmup_runs, measured_runs);
            print_row("thread_rows",
                      bench_case.width,
                      bench_case.height,
                      0,
                      0,
                      threads,
                      row_ms,
                      lut_ms / row_ms,
                      (lut_ms / row_ms) / static_cast<double>(threads),
                      max_abs_diff(lut_output, row_output));

            cpp_isp::ImageBuffer<float> tile_output(bench_case.width, bench_case.height, 1);
            const double tile_ms = cpp_isp_bench::median_ms([&] {
                cpp_isp::bilateral_filter_range_lut_threaded_tiles(input_view,
                                                                   tile_output.view(),
                                                                   2,
                                                                   1.5F,
                                                                   0.08F,
                                                                   512,
                                                                   cpp_isp::BorderPolicy::Replicate,
                                                                   128,
                                                                   64,
                                                                   threads);
            }, warmup_runs, measured_runs);
            print_row("thread_tiles",
                      bench_case.width,
                      bench_case.height,
                      128,
                      64,
                      threads,
                      tile_ms,
                      lut_ms / tile_ms,
                      (lut_ms / tile_ms) / static_cast<double>(threads),
                      max_abs_diff(lut_output, tile_output));
        }
    }

    return EXIT_SUCCESS;
}
