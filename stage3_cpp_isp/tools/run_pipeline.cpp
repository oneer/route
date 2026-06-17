#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/denoise.hpp"
#include "cpp_isp/hdr_merge.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/local_tone_mapping.hpp"
#include "cpp_isp/tone_lut.hpp"
#include "cpp_isp/tone_mapping.hpp"

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

void apply_denoise(const cpp_isp::ImageBuffer<float>& input,
                   cpp_isp::ImageBuffer<float>& output,
                   const std::string& mode) {
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    if (mode == "none") {
        output.storage() = input.storage();
        return;
    }
    if (mode == "box") {
        cpp_isp::box_filter(input_view, output.view(), 1, cpp_isp::BorderPolicy::Reflect);
        return;
    }
    if (mode == "gaussian") {
        cpp_isp::gaussian_filter(input_view, output.view(), 1, 1.0F, cpp_isp::BorderPolicy::Reflect);
        return;
    }
    throw std::invalid_argument("unknown denoise mode: " + mode);
}

void apply_tone(const cpp_isp::ImageBuffer<float>& input,
                cpp_isp::ImageBuffer<float>& output,
                const std::string& mode,
                cpp_isp::ToneCurve curve,
                float exposure) {
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    if (mode == "global") {
        cpp_isp::ToneMappingParams params;
        params.curve = curve;
        params.exposure = exposure;
        params.preserve_luminance = true;
        cpp_isp::tone_map(input_view, output.view(), params);
        return;
    }
    if (mode == "lut") {
        cpp_isp::ToneLutParams params;
        params.curve = curve;
        params.exposure = exposure;
        params.preserve_luminance = true;
        params.input_bits = 12;
        params.output_bits = 12;
        params.input_max = 8.0F;
        cpp_isp::ToneCurveLut lut(params);
        cpp_isp::tone_map_lut(input_view, output.view(), lut);
        return;
    }
    if (mode == "local") {
        cpp_isp::LocalToneMappingParams params;
        params.curve = curve;
        params.exposure = exposure;
        params.base_filter = cpp_isp::LocalBaseFilter::Bilateral;
        params.base_radius = 3;
        params.base_sigma_spatial = 2.4F;
        params.base_sigma_range = 0.35F;
        params.detail_strength = 0.75F;
        cpp_isp::local_tone_map(input_view, output.view(), params);
        return;
    }
    throw std::invalid_argument("unknown tone mode: " + mode);
}

void apply_optional_gamma(const cpp_isp::ImageBuffer<float>& input,
                          cpp_isp::ImageBuffer<float>& output,
                          float gamma) {
    if (gamma == 1.0F) {
        output.storage() = input.storage();
        return;
    }
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::apply_gamma(input_view, output.view(), gamma);
}

cpp_isp::ImageBuffer<float> make_source_single(const std::string& input_path) {
    return tensor_to_image(cpp_isp::read_cpf32(input_path));
}

cpp_isp::ImageBuffer<float> make_source_hdr(const std::string& short_path,
                                            const std::string& long_path,
                                            float short_exposure,
                                            float long_exposure) {
    const auto short_tensor = cpp_isp::read_cpf32(short_path);
    const auto long_tensor = cpp_isp::read_cpf32(long_path);
    auto short_image = tensor_to_image(short_tensor);
    auto long_image = tensor_to_image(long_tensor);
    cpp_isp::ImageBuffer<float> merged(short_tensor.width, short_tensor.height, short_tensor.channels);

    cpp_isp::HdrMergeParams params;
    params.short_exposure = short_exposure;
    params.long_exposure = long_exposure;
    const auto short_view = static_cast<const cpp_isp::ImageBuffer<float>&>(short_image).view();
    const auto long_view = static_cast<const cpp_isp::ImageBuffer<float>&>(long_image).view();
    cpp_isp::hdr_merge_aligned(short_view, long_view, merged.view(), params);
    return merged;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 9 && argc != 12) {
            print_usage();
            return 2;
        }

        const std::string pipeline_mode = argv[1];
        std::string output_path;
        std::string denoise_mode;
        std::string tone_mode;
        cpp_isp::ToneCurve curve = cpp_isp::ToneCurve::Reinhard;
        float exposure = 1.0F;
        float gamma = 1.0F;
        cpp_isp::ImageBuffer<float> source;

        if (pipeline_mode == "single" && argc == 9) {
            source = make_source_single(argv[2]);
            output_path = argv[3];
            denoise_mode = argv[4];
            tone_mode = argv[5];
            curve = parse_curve(argv[6]);
            exposure = static_cast<float>(std::atof(argv[7]));
            gamma = static_cast<float>(std::atof(argv[8]));
        } else if (pipeline_mode == "hdr" && argc == 12) {
            output_path = argv[4];
            denoise_mode = argv[5];
            tone_mode = argv[6];
            curve = parse_curve(argv[7]);
            exposure = static_cast<float>(std::atof(argv[8]));
            gamma = static_cast<float>(std::atof(argv[9]));
            const float short_exposure = static_cast<float>(std::atof(argv[10]));
            const float long_exposure = static_cast<float>(std::atof(argv[11]));
            source = make_source_hdr(argv[2], argv[3], short_exposure, long_exposure);
        } else {
            print_usage();
            return 2;
        }

        cpp_isp::ImageBuffer<float> denoised(source.width(), source.height(), source.channels());
        cpp_isp::ImageBuffer<float> tone_mapped(source.width(), source.height(), source.channels());
        cpp_isp::ImageBuffer<float> final_output(source.width(), source.height(), source.channels());

        apply_denoise(source, denoised, denoise_mode);
        apply_tone(denoised, tone_mapped, tone_mode, curve, exposure);
        apply_optional_gamma(tone_mapped, final_output, gamma);
        cpp_isp::write_cpf32(output_path, image_to_tensor(final_output));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "run_pipeline failed: " << error.what() << '\n';
        return 1;
    }
}
