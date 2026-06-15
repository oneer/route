#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/denoise.hpp"
#include "cpp_isp/image.hpp"

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

}  // namespace

int main(int argc, char** argv) {
    if (argc < 4 || argc > 5) {
        std::cerr << "usage: run_bilateral_lut <input.cpf32> <output.cpf32> <mode> [threads]\n"
                  << "mode: lut | tile | rows | tiles\n";
        return 2;
    }

    const std::string input_path = argv[1];
    const std::string output_path = argv[2];
    const std::string mode = argv[3];
    const std::uint32_t threads = argc == 5 ? static_cast<std::uint32_t>(std::atoi(argv[4])) : 4U;

    try {
        const auto tensor = cpp_isp::read_cpf32(input_path);
        auto input = tensor_to_image(tensor);
        cpp_isp::ImageBuffer<float> output(tensor.width, tensor.height, tensor.channels);
        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();

        if (mode == "lut") {
            cpp_isp::bilateral_filter_range_lut(input_view,
                                                output.view(),
                                                2,
                                                1.5F,
                                                0.08F,
                                                512,
                                                cpp_isp::BorderPolicy::Replicate);
        } else if (mode == "tile") {
            cpp_isp::bilateral_filter_range_lut_tiled(input_view,
                                                     output.view(),
                                                     2,
                                                     1.5F,
                                                     0.08F,
                                                     512,
                                                     cpp_isp::BorderPolicy::Replicate,
                                                     128,
                                                     64);
        } else if (mode == "rows") {
            cpp_isp::bilateral_filter_range_lut_threaded_rows(input_view,
                                                              output.view(),
                                                              2,
                                                              1.5F,
                                                              0.08F,
                                                              512,
                                                              cpp_isp::BorderPolicy::Replicate,
                                                              threads);
        } else if (mode == "tiles") {
            cpp_isp::bilateral_filter_range_lut_threaded_tiles(input_view,
                                                               output.view(),
                                                               2,
                                                               1.5F,
                                                               0.08F,
                                                               512,
                                                               cpp_isp::BorderPolicy::Replicate,
                                                               128,
                                                               64,
                                                               threads);
        } else {
            throw std::invalid_argument("unknown mode: " + mode);
        }

        cpp_isp::write_cpf32(output_path, image_to_tensor(output));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_bilateral_lut failed: " << error.what() << '\n';
        return 1;
    }
}
