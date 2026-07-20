#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/image_fusion.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>

namespace {

cpp_isp::ImageBuffer<float> tensor_to_image(const cpp_isp::TensorF32& tensor) {
    cpp_isp::ImageBuffer<float> image(tensor.width, tensor.height, tensor.channels);
    for (std::uint32_t y = 0; y < tensor.height; ++y) {
        for (std::uint32_t x = 0; x < tensor.width; ++x) {
            for (std::uint32_t c = 0; c < tensor.channels; ++c) {
                const std::size_t index = (static_cast<std::size_t>(y) * tensor.width + x) * tensor.channels + c;
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
                const std::size_t index = (static_cast<std::size_t>(y) * tensor.width + x) * tensor.channels + c;
                tensor.data[index] = image(y, x, c);
            }
        }
    }
    return tensor;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 6) {
        std::cerr << "usage: run_image_fusion <left.cpf32> <right.cpf32> <output.cpf32> <x_begin> <x_end>\n";
        return 2;
    }
    try {
        auto left = tensor_to_image(cpp_isp::read_cpf32(argv[1]));
        auto right = tensor_to_image(cpp_isp::read_cpf32(argv[2]));
        cpp_isp::ImageBuffer<float> matched(left.width(), left.height(), left.channels());
        cpp_isp::ImageBuffer<float> output(left.width(), left.height(), left.channels());
        const auto left_view = static_cast<const cpp_isp::ImageBuffer<float>&>(left).view();
        const auto right_view = static_cast<const cpp_isp::ImageBuffer<float>&>(right).view();
        const auto x_begin = static_cast<std::uint32_t>(std::stoul(argv[4]));
        const auto x_end = static_cast<std::uint32_t>(std::stoul(argv[5]));
        const auto before = cpp_isp::evaluate_aligned_overlap(left_view, right_view, x_begin, x_end);
        const auto gains = cpp_isp::estimate_overlap_color_gains(left_view, right_view, x_begin, x_end);
        cpp_isp::apply_channel_gains(right_view, matched.view(), gains);
        const auto matched_view = static_cast<const cpp_isp::ImageBuffer<float>&>(matched).view();
        const auto after = cpp_isp::evaluate_aligned_overlap(left_view, matched_view, x_begin, x_end);
        cpp_isp::feather_blend_aligned(left_view, matched_view, output.view(), x_begin, x_end);
        cpp_isp::write_cpf32(argv[3], image_to_tensor(output));
        std::cout << "mean_color_delta_before=" << before.mean_color_delta
                  << " mean_color_delta_after=" << after.mean_color_delta
                  << " seam_delta_after=" << after.seam_delta << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_image_fusion failed: " << error.what() << '\n';
        return 1;
    }
}
