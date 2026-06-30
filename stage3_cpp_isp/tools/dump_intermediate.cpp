#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/pipeline.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

// CPF32 文件里的 data 按 y-x-c interleaved 顺序组织；ImageBuffer 按 c-y-x planar 顺序组织。
// 这里显式转换，避免算法层同时背负两套内存布局。
cpp_isp::ImageBuffer<float> tensor_to_image(const cpp_isp::TensorF32& tensor) {
    cpp_isp::ImageBuffer<float> image(tensor.width, tensor.height, tensor.channels);
    for (std::uint32_t y = 0; y < tensor.height; ++y) {
        for (std::uint32_t x = 0; x < tensor.width; ++x) {
            for (std::uint32_t c = 0; c < tensor.channels; ++c) {
                const std::size_t idx =
                    (static_cast<std::size_t>(y) * tensor.width + x) * tensor.channels + c;
                image(y, x, c) = tensor.data[idx];
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
                const std::size_t idx =
                    (static_cast<std::size_t>(y) * tensor.width + x) * tensor.channels + c;
                tensor.data[idx] = image(y, x, c);
            }
        }
    }
    return tensor;
}

void print_usage() {
    std::cerr
        << "usage:\n"
        << "  dump_intermediate <input.cpf32> <output_prefix> "
        << "<denoise:none|box|gaussian> <tone:global|local|lut> "
        << "<curve:reinhard|filmic|scurve> <exposure> <gamma>\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 8) {
            print_usage();
            return 2;
        }
        auto input = tensor_to_image(cpp_isp::read_cpf32(argv[1]));
        cpp_isp::PipelineParams params;
        params.denoise = cpp_isp::parse_pipeline_denoise_mode(argv[3]);
        params.tone = cpp_isp::parse_pipeline_tone_mode(argv[4]);
        params.curve = cpp_isp::parse_pipeline_tone_curve(argv[5]);
        params.exposure = static_cast<float>(std::atof(argv[6]));
        params.gamma = static_cast<float>(std::atof(argv[7]));

        // run_pipeline_single 会返回每个阶段的缓冲；本工具把它们全部落盘，方便逐步排错。
        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
        const auto result = cpp_isp::run_pipeline_single(input_view, params);
        const std::string prefix = argv[2];
        cpp_isp::write_cpf32(prefix + "_source.cpf32", image_to_tensor(result.source));
        cpp_isp::write_cpf32(prefix + "_denoised.cpf32", image_to_tensor(result.denoised));
        cpp_isp::write_cpf32(prefix + "_tone_mapped.cpf32", image_to_tensor(result.tone_mapped));
        cpp_isp::write_cpf32(prefix + "_output.cpf32", image_to_tensor(result.output));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "dump_intermediate failed: " << error.what() << '\n';
        return 1;
    }
}
