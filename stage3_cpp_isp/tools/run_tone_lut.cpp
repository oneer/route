#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/tone_lut.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

// LUT 工具用于比较浮点 tone mapping 与定点/查表近似之间的误差和速度。
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
        std::cerr << "usage: run_tone_lut <input.cpf32> <output.cpf32> "
                  << "<reinhard|filmic|scurve> <rgb|luma> <exposure> "
                  << "<input_bits> <output_bits> <input_max>\n";
        return 2;
    }

    try {
        const auto tensor = cpp_isp::read_cpf32(argv[1]);
        auto input = tensor_to_image(tensor);
        cpp_isp::ImageBuffer<float> output(tensor.width, tensor.height, tensor.channels);

        cpp_isp::ToneLutParams params;
        params.curve = parse_curve(argv[3]);
        params.preserve_luminance = std::string(argv[4]) == "luma";
        params.exposure = static_cast<float>(std::atof(argv[5]));
        params.input_bits = static_cast<std::uint32_t>(std::atoi(argv[6]));
        params.output_bits = static_cast<std::uint32_t>(std::atoi(argv[7]));
        params.input_max = static_cast<float>(std::atof(argv[8]));

        // 构造 LUT 时一次性生成整张表；之后每个像素只做量化查表。
        cpp_isp::ToneCurveLut lut(params);
        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
        cpp_isp::tone_map_lut(input_view, output.view(), lut);
        cpp_isp::write_cpf32(argv[2], image_to_tensor(output));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_tone_lut failed: " << error.what() << '\n';
        return 1;
    }
}
