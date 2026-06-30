#pragma once

#include "cpp_isp/cpf32.hpp"

namespace cpp_isp {

struct AlignmentMetrics {
    // 这些指标用于判断 C++ 输出是否和 Python/golden reference 对齐。
    double max_abs_error = 0.0;
    double mean_abs_error = 0.0;
    double rmse = 0.0;
    double psnr = 0.0;
    std::size_t failed_pixels = 0;
    std::size_t total_values = 0;
};

// threshold 统计超过容忍误差的值数量；peak_value 用于 PSNR 计算，默认按 [0,1] 图像。
AlignmentMetrics compare_tensors(const TensorF32& reference,
                                 const TensorF32& output,
                                 double threshold,
                                 double peak_value = 1.0);

}  // namespace cpp_isp
