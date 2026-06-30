#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/tone_mapping.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

// 浮点 tone mapping 工具：作为算法参考路径，也可选做 gamma 显示编码。
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
    if (argc < 6 || argc > 7) {
        std::cerr << "usage: run_tone_mapping <input.cpf32> <output.cpf32> "
                  << "<reinhard|filmic|scurve> <rgb|luma> <exposure> [gamma]\n";
        return 2;
    }

    try {
        const auto tensor = cpp_isp::read_cpf32(argv[1]);
        auto input = tensor_to_image(tensor);
        cpp_isp::ImageBuffer<float> tone_output(tensor.width, tensor.height, tensor.channels);
        cpp_isp::ImageBuffer<float> final_output(tensor.width, tensor.height, tensor.channels);

        cpp_isp::ToneMappingParams params;
        params.curve = parse_curve(argv[3]);
        params.preserve_luminance = std::string(argv[4]) == "luma";
        params.exposure = static_cast<float>(std::atof(argv[5]));

        const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
        cpp_isp::tone_map(input_view, tone_output.view(), params);

        const float gamma = argc == 7 ? static_cast<float>(std::atof(argv[6])) : 1.0F;
        if (gamma == 1.0F) {
            // gamma=1 时直接输出 tone mapping 结果，避免一次无意义拷贝。
            cpp_isp::write_cpf32(argv[2], image_to_tensor(tone_output));
        } else {
            const auto tone_view = static_cast<const cpp_isp::ImageBuffer<float>&>(tone_output).view();
            cpp_isp::apply_gamma(tone_view, final_output.view(), gamma);
            cpp_isp::write_cpf32(argv[2], image_to_tensor(final_output));
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_tone_mapping failed: " << error.what() << '\n';
        return 1;
    }
}
