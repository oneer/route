#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/pipeline.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

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
        << "  run_pipeline single <input.cpf32> <output.cpf32> "
        << "<denoise:none|box|gaussian> <tone:global|local|lut> "
        << "<curve:reinhard|filmic|scurve> <exposure> <gamma>\n"
        << "  run_pipeline hdr <short.cpf32> <long.cpf32> <output.cpf32> "
        << "<denoise:none|box|gaussian> <tone:global|local|lut> "
        << "<curve:reinhard|filmic|scurve> <exposure> <gamma> "
        << "<short_exposure> <long_exposure>\n";
}

cpp_isp::PipelineParams parse_pipeline_params(const char* denoise,
                                              const char* tone,
                                              const char* curve,
                                              const char* exposure,
                                              const char* gamma) {
    cpp_isp::PipelineParams params;
    params.denoise = cpp_isp::parse_pipeline_denoise_mode(denoise);
    params.tone = cpp_isp::parse_pipeline_tone_mode(tone);
    params.curve = cpp_isp::parse_pipeline_tone_curve(curve);
    params.exposure = static_cast<float>(std::atof(exposure));
    params.gamma = static_cast<float>(std::atof(gamma));
    return params;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 9 && argc != 12) {
            print_usage();
            return 2;
        }

        const std::string pipeline_mode = argv[1];
        cpp_isp::PipelineIntermediates result;
        std::string output_path;

        if (pipeline_mode == "single" && argc == 9) {
            auto input = tensor_to_image(cpp_isp::read_cpf32(argv[2]));
            const auto params = parse_pipeline_params(argv[4], argv[5], argv[6], argv[7], argv[8]);
            const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
            result = cpp_isp::run_pipeline_single(input_view, params);
            output_path = argv[3];
        } else if (pipeline_mode == "hdr" && argc == 12) {
            auto short_image = tensor_to_image(cpp_isp::read_cpf32(argv[2]));
            auto long_image = tensor_to_image(cpp_isp::read_cpf32(argv[3]));
            const auto params = parse_pipeline_params(argv[5], argv[6], argv[7], argv[8], argv[9]);
            cpp_isp::HdrMergeParams hdr_params;
            hdr_params.short_exposure = static_cast<float>(std::atof(argv[10]));
            hdr_params.long_exposure = static_cast<float>(std::atof(argv[11]));
            const auto short_view = static_cast<const cpp_isp::ImageBuffer<float>&>(short_image).view();
            const auto long_view = static_cast<const cpp_isp::ImageBuffer<float>&>(long_image).view();
            result = cpp_isp::run_pipeline_hdr(short_view, long_view, hdr_params, params);
            output_path = argv[4];
        } else {
            print_usage();
            return 2;
        }

        cpp_isp::write_cpf32(output_path, image_to_tensor(result.output));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_pipeline failed: " << error.what() << '\n';
        return 1;
    }
}
