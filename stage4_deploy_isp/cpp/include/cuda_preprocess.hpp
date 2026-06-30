#pragma once

#include <cstddef>

namespace stage4 {

// 将解码后的 RGB uint8 HWC 缓冲区归一化为模型输入需要的 float32 NCHW。
// 返回值是多次 kernel launch 的平均耗时，单位毫秒；H2D/D2H 拷贝不计入该返回值。
float cuda_normalize_u8_to_float_nchw(
    const unsigned char* input_hwc,
    float* output_nchw,
    int width,
    int height,
    int channels,
    int runs);

}  // namespace stage4
