#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/metrics.hpp"
#include "cpp_isp/pipeline.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

namespace {

cpp_isp::ImageBuffer<float> tensor_to_image(const cpp_isp::TensorF32& tensor) {
    cpp_isp::ImageBuffer<float> image(tensor.width, tensor.height, tensor.channels);
    for (std::uint32_t y = 0; y < tensor.height; ++y) {
        for (std::uint32_t x = 0; x < tensor.width; ++x) {
            for (std::uint32_t c = 0; c < tensor.channels; ++c) {
                const std::size_t index =
                    (static_cast<std::size_t>(y) * tensor.width + x) * tensor.channels + c;
                image(y, x, c) = tensor.data[index];
            }
        }
    }
    return image;
}

cpp_isp::TensorF32 image_to_tensor(const cpp_isp::ImageBuffer<float>& image) {
    cpp_isp::TensorF32 tensor;
    tensor.width = image.width();
    tensor.height = image.height();
    tensor.channels = image.channels();
    tensor.data.resize(static_cast<std::size_t>(tensor.width) * tensor.height * tensor.channels);
    for (std::uint32_t y = 0; y < tensor.height; ++y) {
        for (std::uint32_t x = 0; x < tensor.width; ++x) {
            for (std::uint32_t c = 0; c < tensor.channels; ++c) {
                const std::size_t index =
                    (static_cast<std::size_t>(y) * tensor.width + x) * tensor.channels + c;
                tensor.data[index] = image(y, x, c);
            }
        }
    }
    return tensor;
}

void compare_stage(const std::string& stage,
                   const cpp_isp::ImageBuffer<float>& output,
                   const std::string& golden_path,
                   double tolerance) {
    const auto golden = cpp_isp::read_cpf32(golden_path);
    const auto metrics = cpp_isp::compare_tensors(golden, image_to_tensor(output), tolerance);
    if (metrics.failed_pixels != 0) {
        throw std::runtime_error(
            "pipeline first divergence at " + stage +
            ": max_abs_error=" + std::to_string(metrics.max_abs_error) +
            ", failed_values=" + std::to_string(metrics.failed_pixels));
    }
}

}  // namespace

int main() {
    try {
        const std::string root = CPP_ISP_SOURCE_DIR;
        const std::string fixture_dir = root + "/data/pipeline_golden/";
        auto input = tensor_to_image(cpp_isp::read_cpf32(fixture_dir + "pipeline_source.cpf32"));

        cpp_isp::PipelineParams params;
        params.denoise = cpp_isp::PipelineDenoiseMode::Gaussian;
        params.tone = cpp_isp::PipelineToneMode::Global;
        params.curve = cpp_isp::ToneCurve::Reinhard;
        params.exposure = 0.42F;
        params.gamma = 2.2F;

        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
        const auto result = cpp_isp::run_pipeline_single(input_view, params);

        compare_stage("source", result.source, fixture_dir + "pipeline_source.cpf32", 0.0);
        compare_stage("denoised", result.denoised, fixture_dir + "pipeline_denoised.cpf32", 1.0e-6);
        compare_stage("tone_mapped",
                      result.tone_mapped,
                      fixture_dir + "pipeline_tone_mapped.cpf32",
                      1.0e-5);
        compare_stage("output", result.output, fixture_dir + "pipeline_output.cpf32", 1.0e-5);

        std::cout << "test_pipeline_golden passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_pipeline_golden failed: " << error.what() << '\n';
        return 1;
    }
}
