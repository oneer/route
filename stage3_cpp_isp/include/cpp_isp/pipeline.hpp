#pragma once

#include "cpp_isp/hdr_merge.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/tone_mapping.hpp"

#include <string>

namespace cpp_isp {

enum class PipelineDenoiseMode {
    None,
    Box,
    Gaussian,
};

enum class PipelineToneMode {
    Global,
    Local,
    Lut,
};

struct PipelineParams {
    PipelineDenoiseMode denoise = PipelineDenoiseMode::Gaussian;
    PipelineToneMode tone = PipelineToneMode::Global;
    ToneCurve curve = ToneCurve::Reinhard;
    float exposure = 1.0F;
    float gamma = 1.0F;
};

struct PipelineIntermediates {
    ImageBuffer<float> source;
    ImageBuffer<float> denoised;
    ImageBuffer<float> tone_mapped;
    ImageBuffer<float> output;
};

PipelineDenoiseMode parse_pipeline_denoise_mode(const std::string& value);
PipelineToneMode parse_pipeline_tone_mode(const std::string& value);
ToneCurve parse_pipeline_tone_curve(const std::string& value);

const char* to_string(PipelineDenoiseMode mode);
const char* to_string(PipelineToneMode mode);
const char* to_string(ToneCurve curve);

PipelineIntermediates run_pipeline_single(const ImageView<const float>& input,
                                          const PipelineParams& params);

PipelineIntermediates run_pipeline_hdr(const ImageView<const float>& short_image,
                                       const ImageView<const float>& long_image,
                                       const HdrMergeParams& hdr_params,
                                       const PipelineParams& params);

}  // namespace cpp_isp
