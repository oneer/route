#include "cpp_isp/metrics.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace cpp_isp {

AlignmentMetrics compare_tensors(const TensorF32& reference,
                                 const TensorF32& output,
                                 double threshold,
                                 double peak_value) {
    if (reference.width != output.width || reference.height != output.height ||
        reference.channels != output.channels || reference.data.size() != output.data.size()) {
        throw std::runtime_error("tensor shapes do not match");
    }

    AlignmentMetrics metrics;
    metrics.total_values = reference.data.size();
    if (metrics.total_values == 0) {
        return metrics;
    }

    double abs_sum = 0.0;
    double sq_sum = 0.0;
    for (std::size_t i = 0; i < reference.data.size(); ++i) {
        // 对齐检查拒绝 NaN/Inf，否则误差统计会失真且很难定位问题。
        if (!std::isfinite(reference.data[i]) || !std::isfinite(output.data[i])) {
            throw std::runtime_error("alignment input contains NaN or Inf at value index " +
                                     std::to_string(i));
        }
        const double error = static_cast<double>(output.data[i]) - reference.data[i];
        const double abs_error = std::abs(error);
        // 同时累计最大误差、平均绝对误差、均方误差，覆盖“最坏点”和“整体偏差”。
        metrics.max_abs_error = std::max(metrics.max_abs_error, abs_error);
        abs_sum += abs_error;
        sq_sum += error * error;
        if (abs_error > threshold) {
            ++metrics.failed_pixels;
        }
    }

    metrics.mean_abs_error = abs_sum / static_cast<double>(metrics.total_values);
    metrics.rmse = std::sqrt(sq_sum / static_cast<double>(metrics.total_values));
    if (metrics.rmse == 0.0) {
        metrics.psnr = INFINITY;
    } else {
        // PSNR 越高表示整体误差越小；完全一致时定义为无穷大。
        metrics.psnr = 20.0 * std::log10(peak_value / metrics.rmse);
    }

    return metrics;
}

}  // namespace cpp_isp
