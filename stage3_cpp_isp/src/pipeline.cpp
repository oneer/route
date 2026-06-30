#include "cpp_isp/pipeline.hpp"

#include "cpp_isp/denoise.hpp"
#include "cpp_isp/local_tone_mapping.hpp"
#include "cpp_isp/tone_lut.hpp"

#include <stdexcept>

namespace cpp_isp {

namespace {

ImageBuffer<float> copy_image(const ImageView<const float>& input) {
    ImageBuffer<float> output(input.width(), input.height(), input.channels(), input.row_stride());
    // 显式拷贝成拥有内存的 ImageBuffer，避免后续中间结果依赖外部输入生命周期。
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                output(y, x, c) = input(y, x, c);
            }
        }
    }
    return output;
}

void apply_pipeline_denoise(const ImageView<const float>& input,
                            ImageView<float> output,
                            PipelineDenoiseMode mode) {
    if (mode == PipelineDenoiseMode::None) {
        // None 模式仍写入 denoised 缓冲，保证下游管线总能读取同名中间结果。
        for (std::uint32_t c = 0; c < input.channels(); ++c) {
            for (std::uint32_t y = 0; y < input.height(); ++y) {
                for (std::uint32_t x = 0; x < input.width(); ++x) {
                    output(y, x, c) = input(y, x, c);
                }
            }
        }
        return;
    }
    if (mode == PipelineDenoiseMode::Box) {
        // 教学默认半径 1：窗口 3x3，便于和 Python reference 对齐。
        box_filter(input, output, 1, BorderPolicy::Reflect);
        return;
    }
    if (mode == PipelineDenoiseMode::Gaussian) {
        gaussian_filter(input, output, 1, 1.0F, BorderPolicy::Reflect);
        return;
    }
    throw std::invalid_argument("unknown pipeline denoise mode");
}

void apply_pipeline_tone(const ImageView<const float>& input,
                         ImageView<float> output,
                         const PipelineParams& params) {
    if (params.tone == PipelineToneMode::Global) {
        // 全局 tone mapping 使用 preserve_luminance，避免 RGB 三通道独立压缩带来的色相变化。
        ToneMappingParams tone_params;
        tone_params.curve = params.curve;
        tone_params.exposure = params.exposure;
        tone_params.preserve_luminance = true;
        tone_map(input, output, tone_params);
        return;
    }
    if (params.tone == PipelineToneMode::Lut) {
        // LUT 路径固定 12-bit 输入/输出，模拟常见 ISP 硬件查表模块。
        ToneLutParams lut_params;
        lut_params.curve = params.curve;
        lut_params.exposure = params.exposure;
        lut_params.preserve_luminance = true;
        lut_params.input_bits = 12;
        lut_params.output_bits = 12;
        lut_params.input_max = 8.0F;
        ToneCurveLut lut(lut_params);
        tone_map_lut(input, output, lut);
        return;
    }
    if (params.tone == PipelineToneMode::Local) {
        // 局部路径默认用 bilateral base，牺牲一点速度换更少 halo。
        LocalToneMappingParams local_params;
        local_params.curve = params.curve;
        local_params.exposure = params.exposure;
        local_params.base_filter = LocalBaseFilter::Bilateral;
        local_params.base_radius = 3;
        local_params.base_sigma_spatial = 2.4F;
        local_params.base_sigma_range = 0.35F;
        local_params.detail_strength = 0.75F;
        local_tone_map(input, output, local_params);
        return;
    }
    throw std::invalid_argument("unknown pipeline tone mode");
}

void apply_pipeline_gamma(const ImageView<const float>& input, ImageView<float> output, float gamma) {
    if (gamma == 1.0F) {
        // gamma=1 是恒等变换，但仍写入 output，保持中间结果完整。
        for (std::uint32_t c = 0; c < input.channels(); ++c) {
            for (std::uint32_t y = 0; y < input.height(); ++y) {
                for (std::uint32_t x = 0; x < input.width(); ++x) {
                    output(y, x, c) = input(y, x, c);
                }
            }
        }
        return;
    }
    apply_gamma(input, output, gamma);
}

}  // namespace

PipelineDenoiseMode parse_pipeline_denoise_mode(const std::string& value) {
    if (value == "none") {
        return PipelineDenoiseMode::None;
    }
    if (value == "box") {
        return PipelineDenoiseMode::Box;
    }
    if (value == "gaussian") {
        return PipelineDenoiseMode::Gaussian;
    }
    throw std::invalid_argument("unknown denoise mode: " + value);
}

PipelineToneMode parse_pipeline_tone_mode(const std::string& value) {
    if (value == "global") {
        return PipelineToneMode::Global;
    }
    if (value == "local") {
        return PipelineToneMode::Local;
    }
    if (value == "lut") {
        return PipelineToneMode::Lut;
    }
    throw std::invalid_argument("unknown tone mode: " + value);
}

ToneCurve parse_pipeline_tone_curve(const std::string& value) {
    if (value == "reinhard") {
        return ToneCurve::Reinhard;
    }
    if (value == "filmic") {
        return ToneCurve::Filmic;
    }
    if (value == "scurve") {
        return ToneCurve::SCurve;
    }
    throw std::invalid_argument("unknown tone curve: " + value);
}

const char* to_string(PipelineDenoiseMode mode) {
    switch (mode) {
        case PipelineDenoiseMode::None:
            return "none";
        case PipelineDenoiseMode::Box:
            return "box";
        case PipelineDenoiseMode::Gaussian:
            return "gaussian";
    }
    return "unknown";
}

const char* to_string(PipelineToneMode mode) {
    switch (mode) {
        case PipelineToneMode::Global:
            return "global";
        case PipelineToneMode::Local:
            return "local";
        case PipelineToneMode::Lut:
            return "lut";
    }
    return "unknown";
}

const char* to_string(ToneCurve curve) {
    switch (curve) {
        case ToneCurve::Reinhard:
            return "reinhard";
        case ToneCurve::Filmic:
            return "filmic";
        case ToneCurve::SCurve:
            return "scurve";
    }
    return "unknown";
}

PipelineIntermediates run_pipeline_single(const ImageView<const float>& input,
                                          const PipelineParams& params) {
    PipelineIntermediates result;
    // 按阶段分配独立缓冲，便于 dump_intermediate 和 golden test 检查每一步。
    result.source = copy_image(input);
    result.denoised = ImageBuffer<float>(input.width(), input.height(), input.channels());
    result.tone_mapped = ImageBuffer<float>(input.width(), input.height(), input.channels());
    result.output = ImageBuffer<float>(input.width(), input.height(), input.channels());

    const auto source_view = static_cast<const ImageBuffer<float>&>(result.source).view();
    apply_pipeline_denoise(source_view, result.denoised.view(), params.denoise);

    const auto denoised_view = static_cast<const ImageBuffer<float>&>(result.denoised).view();
    apply_pipeline_tone(denoised_view, result.tone_mapped.view(), params);

    const auto tone_view = static_cast<const ImageBuffer<float>&>(result.tone_mapped).view();
    apply_pipeline_gamma(tone_view, result.output.view(), params.gamma);
    return result;
}

PipelineIntermediates run_pipeline_hdr(const ImageView<const float>& short_image,
                                       const ImageView<const float>& long_image,
                                       const HdrMergeParams& hdr_params,
                                       const PipelineParams& params) {
    ImageBuffer<float> merged(short_image.width(), short_image.height(), short_image.channels());
    // HDR 合成后的 merged 是线性域图像，可以直接走普通单帧 ISP 教学管线。
    hdr_merge_aligned(short_image, long_image, merged.view(), hdr_params);
    const auto merged_view = static_cast<const ImageBuffer<float>&>(merged).view();
    return run_pipeline_single(merged_view, params);
}

}  // namespace cpp_isp
