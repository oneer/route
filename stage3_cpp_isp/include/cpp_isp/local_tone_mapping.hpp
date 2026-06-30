#pragma once

#include "cpp_isp/border.hpp"
#include "cpp_isp/image.hpp"
#include "cpp_isp/tone_mapping.hpp"

#include <cstdint>

namespace cpp_isp {

// 局部 tone mapping 先估计低频 base，再保留/增强 detail。
// Box 速度快但容易产生 halo；Bilateral 更慢但更能保护边缘。
enum class LocalBaseFilter {
    Box,
    Bilateral,
};

struct LocalToneMappingParams {
    ToneCurve curve = ToneCurve::Reinhard;
    float exposure = 1.0F;
    std::uint32_t base_radius = 5;
    // base_sigma_spatial/range 只在 Bilateral base 下使用，控制空间平滑和边缘保护强度。
    float base_sigma_spatial = 3.0F;
    float base_sigma_range = 0.25F;
    // detail_strength 控制 detail = luminance / base 的保留程度；0 表示只看压缩后的 base。
    float detail_strength = 1.0F;
    LocalBaseFilter base_filter = LocalBaseFilter::Box;
    BorderPolicy border_policy = BorderPolicy::Reflect;
};

void estimate_luminance_base(const ImageView<const float>& input,
                             ImageView<float> base,
                             const LocalToneMappingParams& params);

// 对 HDR/线性图做局部动态范围压缩，输出仍是 [0,1] 显示域。
void local_tone_map(const ImageView<const float>& input,
                    ImageView<float> output,
                    const LocalToneMappingParams& params);

}  // namespace cpp_isp
