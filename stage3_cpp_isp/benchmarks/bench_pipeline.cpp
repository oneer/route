#include "cpp_isp/pipeline.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {

cpp_isp::ImageBuffer<float> make_scene(std::uint32_t width, std::uint32_t height) {
    cpp_isp::ImageBuffer<float> image(width, height, 3);
    for (std::uint32_t y = 0; y < height; ++y) {
        for (std::uint32_t x = 0; x < width; ++x) {
            const float gx = static_cast<float>(x) / static_cast<float>(std::max(1U, width - 1U));
            const float gy = static_cast<float>(y) / static_cast<float>(std::max(1U, height - 1U));
            const float texture = static_cast<float>((x * 17U + y * 29U) % 53U) / 530.0F;
            const float base = std::min(0.08F + 0.65F * gx + 0.35F * gy + texture, 2.5F);
            image(y, x, 0) = base;
            image(y, x, 1) = std::min(base * 0.92F + 0.03F, 2.5F);
            image(y, x, 2) = std::min(base * 0.82F + 0.08F, 2.5F);
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

struct BenchCase {
    const char* name;
    std::uint32_t width;
    std::uint32_t height;
};

struct PipelineCase {
    cpp_isp::PipelineDenoiseMode denoise;
    cpp_isp::PipelineToneMode tone;
    cpp_isp::ToneCurve curve;
    float exposure;
    float gamma;
};

}  // namespace

int main(int argc, char** argv) {
    const bool full = argc > 1 && std::string(argv[1]) == "--full";
    const int repeats = full ? 1 : 2;
    const std::vector<BenchCase> sizes = full
        ? std::vector<BenchCase>{{"1080p", 1920, 1080}, {"4k", 3840, 2160}}
        : std::vector<BenchCase>{{"small", 320, 180}, {"preview", 640, 360}};
    const std::vector<PipelineCase> pipelines = {
        {cpp_isp::PipelineDenoiseMode::Gaussian, cpp_isp::PipelineToneMode::Global, cpp_isp::ToneCurve::Reinhard, 0.22F, 2.2F},
        {cpp_isp::PipelineDenoiseMode::Gaussian, cpp_isp::PipelineToneMode::Lut, cpp_isp::ToneCurve::Reinhard, 0.22F, 2.2F},
        {cpp_isp::PipelineDenoiseMode::None, cpp_isp::PipelineToneMode::Local, cpp_isp::ToneCurve::Reinhard, 0.22F, 2.2F},
    };

    std::cout << "case,width,height,denoise,tone,curve,exposure,gamma,ms\n";
    for (const auto& size : sizes) {
        auto image = make_scene(size.width, size.height);
        const auto input = static_cast<const cpp_isp::ImageBuffer<float>&>(image).view();
        for (const auto& pipeline : pipelines) {
            cpp_isp::PipelineParams params;
            params.denoise = pipeline.denoise;
            params.tone = pipeline.tone;
            params.curve = pipeline.curve;
            params.exposure = pipeline.exposure;
            params.gamma = pipeline.gamma;
            const double ms = time_ms([&] {
                volatile auto result = cpp_isp::run_pipeline_single(input, params);
                (void)result;
            }, repeats);
            std::cout << size.name << ','
                      << size.width << ','
                      << size.height << ','
                      << cpp_isp::to_string(params.denoise) << ','
                      << cpp_isp::to_string(params.tone) << ','
                      << cpp_isp::to_string(params.curve) << ','
                      << params.exposure << ','
                      << params.gamma << ','
                      << std::fixed << std::setprecision(3) << ms << '\n';
        }
    }
    return EXIT_SUCCESS;
}
