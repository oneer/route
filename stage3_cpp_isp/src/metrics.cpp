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
        if (!std::isfinite(reference.data[i]) || !std::isfinite(output.data[i])) {
            throw std::runtime_error("alignment input contains NaN or Inf at value index " +
                                     std::to_string(i));
        }
        const double error = static_cast<double>(output.data[i]) - reference.data[i];
        const double abs_error = std::abs(error);
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
        metrics.psnr = 20.0 * std::log10(peak_value / metrics.rmse);
    }

    return metrics;
}

}  // namespace cpp_isp
