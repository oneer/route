#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/hdr_merge.hpp"
#include "cpp_isp/image.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>

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

}  // namespace

int main(int argc, char** argv) {
    if (argc != 9) {
        std::cerr << "usage: run_hdr_merge <short.cpf32> <long.cpf32> <output.cpf32> "
                  << "<short_exposure> <long_exposure> <saturation_threshold> "
                  << "<underexposure_threshold> <weight_epsilon>\n";
        return 2;
    }

    try {
        const auto short_tensor = cpp_isp::read_cpf32(argv[1]);
        const auto long_tensor = cpp_isp::read_cpf32(argv[2]);
        auto short_image = tensor_to_image(short_tensor);
        auto long_image = tensor_to_image(long_tensor);
        cpp_isp::ImageBuffer<float> output(short_tensor.width, short_tensor.height, short_tensor.channels);

        cpp_isp::HdrMergeParams params;
        params.short_exposure = static_cast<float>(std::atof(argv[4]));
        params.long_exposure = static_cast<float>(std::atof(argv[5]));
        params.saturation_threshold = static_cast<float>(std::atof(argv[6]));
        params.underexposure_threshold = static_cast<float>(std::atof(argv[7]));
        params.weight_epsilon = static_cast<float>(std::atof(argv[8]));

        const auto short_view = static_cast<const cpp_isp::ImageBuffer<float>&>(short_image).view();
        const auto long_view = static_cast<const cpp_isp::ImageBuffer<float>&>(long_image).view();
        cpp_isp::hdr_merge_aligned(short_view, long_view, output.view(), params);
        cpp_isp::write_cpf32(argv[3], image_to_tensor(output));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_hdr_merge failed: " << error.what() << '\n';
        return 1;
    }
}
