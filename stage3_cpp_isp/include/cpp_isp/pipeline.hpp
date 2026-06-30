#pragma once

#include "cpp_isp/hdr_merge.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/tone_mapping.hpp"

#include <string>

namespace cpp_isp {

// Stage 3 教学管线的降噪阶段：None 用于对照，Box/Gaussian 用于展示基础滤波差异。
enum class PipelineDenoiseMode {
    None,
    Box,
    Gaussian,
};

// Tone 阶段可以切换全局浮点、局部 tone mapping、以及 LUT 近似路径。
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
    // 保留中间结果是为了调试和写报告：能分别比较 source/denoised/tone_mapped/output。
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

// 单帧路径：输入 -> 降噪 -> tone mapping -> gamma。
PipelineIntermediates run_pipeline_single(const ImageView<const float>& input,
                                          const PipelineParams& params);

// HDR 路径：先把短/长曝光融合成线性 HDR，再复用单帧路径。
PipelineIntermediates run_pipeline_hdr(const ImageView<const float>& short_image,
                                       const ImageView<const float>& long_image,
                                       const HdrMergeParams& hdr_params,
                                       const PipelineParams& params);

}  // namespace cpp_isp
