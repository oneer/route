#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/local_tone_mapping.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

cpp_isp::ToneCurve parse_curve(const std::string& value) {
    if (value == "reinhard") {
        return cpp_isp::ToneCurve::Reinhard;
    }
    if (value == "filmic") {
        return cpp_isp::ToneCurve::Filmic;
    }
    if (value == "scurve") {
        return cpp_isp::ToneCurve::SCurve;
    }
    throw std::invalid_argument("unknown tone curve: " + value);
}

cpp_isp::LocalBaseFilter parse_filter(const std::string& value) {
    if (value == "box") {
        return cpp_isp::LocalBaseFilter::Box;
    }
    if (value == "bilateral") {
        return cpp_isp::LocalBaseFilter::Bilateral;
    }
    throw std::invalid_argument("unknown base filter: " + value);
}

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
    if (argc != 10) {
        std::cerr << "usage: run_local_tone_mapping <input.cpf32> <output.cpf32> "
                  << "<reinhard|filmic|scurve> <exposure> <box|bilateral> "
                  << "<radius> <sigma_spatial> <sigma_range> <detail_strength>\n";
        return 2;
    }

    try {
        const auto tensor = cpp_isp::read_cpf32(argv[1]);
        auto input = tensor_to_image(tensor);
        cpp_isp::ImageBuffer<float> output(tensor.width, tensor.height, tensor.channels);

        cpp_isp::LocalToneMappingParams params;
        params.curve = parse_curve(argv[3]);
        params.exposure = static_cast<float>(std::atof(argv[4]));
        params.base_filter = parse_filter(argv[5]);
        params.base_radius = static_cast<std::uint32_t>(std::atoi(argv[6]));
        params.base_sigma_spatial = static_cast<float>(std::atof(argv[7]));
        params.base_sigma_range = static_cast<float>(std::atof(argv[8]));
        params.detail_strength = static_cast<float>(std::atof(argv[9]));

        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
        cpp_isp::local_tone_map(input_view, output.view(), params);
        cpp_isp::write_cpf32(argv[2], image_to_tensor(output));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_local_tone_mapping failed: " << error.what() << '\n';
        return 1;
    }
}
