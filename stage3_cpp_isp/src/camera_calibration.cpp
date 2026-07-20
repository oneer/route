#include "cpp_isp/camera_calibration.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace cpp_isp {
namespace {

using AugmentedSystem = std::array<std::array<double, 9>, 8>;

bool finite_point(const Point2d& point) {
    return std::isfinite(point.x) && std::isfinite(point.y);
}

std::array<double, 8> solve_linear_system(AugmentedSystem system) {
    for (std::size_t column = 0; column < 8; ++column) {
        std::size_t pivot = column;
        for (std::size_t row = column + 1; row < 8; ++row) {
            if (std::abs(system[row][column]) > std::abs(system[pivot][column])) {
                pivot = row;
            }
        }
        if (std::abs(system[pivot][column]) < 1.0e-10) {
            throw std::invalid_argument("degenerate homography correspondences");
        }
        std::swap(system[column], system[pivot]);
        const double divisor = system[column][column];
        for (std::size_t item = column; item < 9; ++item) {
            system[column][item] /= divisor;
        }
        for (std::size_t row = 0; row < 8; ++row) {
            if (row == column) {
                continue;
            }
            const double factor = system[row][column];
            for (std::size_t item = column; item < 9; ++item) {
                system[row][item] -= factor * system[column][item];
            }
        }
    }
    std::array<double, 8> solution{};
    for (std::size_t row = 0; row < 8; ++row) {
        solution[row] = system[row][8];
    }
    return solution;
}

Homography inverse(const Homography& input) {
    const auto& h = input.values;
    const double a = h[0], b = h[1], c = h[2];
    const double d = h[3], e = h[4], f = h[5];
    const double g = h[6], i = h[7], j = h[8];
    const double determinant = a * (e * j - f * i) - b * (d * j - f * g) + c * (d * i - e * g);
    if (std::abs(determinant) < 1.0e-12) {
        throw std::invalid_argument("homography is not invertible");
    }
    Homography result;
    result.values = {{
        (e * j - f * i) / determinant,
        (c * i - b * j) / determinant,
        (b * f - c * e) / determinant,
        (f * g - d * j) / determinant,
        (a * j - c * g) / determinant,
        (c * d - a * f) / determinant,
        (d * i - e * g) / determinant,
        (b * g - a * i) / determinant,
        (a * e - b * d) / determinant,
    }};
    return result;
}

}  // namespace

Point2d Homography::project(const Point2d& point) const {
    const double denominator = values[6] * point.x + values[7] * point.y + values[8];
    if (std::abs(denominator) < 1.0e-12) {
        throw std::domain_error("homography projects point to infinity");
    }
    return {
        (values[0] * point.x + values[1] * point.y + values[2]) / denominator,
        (values[3] * point.x + values[4] * point.y + values[5]) / denominator,
    };
}

Homography solve_planar_homography(
    const std::vector<Point2d>& source,
    const std::vector<Point2d>& destination) {
    if (source.size() != destination.size() || source.size() < 4) {
        throw std::invalid_argument("homography needs at least four paired points");
    }
    AugmentedSystem normal{};
    for (std::size_t point_index = 0; point_index < source.size(); ++point_index) {
        const auto& src = source[point_index];
        const auto& dst = destination[point_index];
        if (!finite_point(src) || !finite_point(dst)) {
            throw std::invalid_argument("homography points must be finite");
        }
        const std::array<std::array<double, 8>, 2> rows{{
            {{src.x, src.y, 1.0, 0.0, 0.0, 0.0, -dst.x * src.x, -dst.x * src.y}},
            {{0.0, 0.0, 0.0, src.x, src.y, 1.0, -dst.y * src.x, -dst.y * src.y}},
        }};
        const std::array<double, 2> targets{{dst.x, dst.y}};
        for (std::size_t equation = 0; equation < 2; ++equation) {
            for (std::size_t row = 0; row < 8; ++row) {
                for (std::size_t column = 0; column < 8; ++column) {
                    normal[row][column] += rows[equation][row] * rows[equation][column];
                }
                normal[row][8] += rows[equation][row] * targets[equation];
            }
        }
    }
    const auto solution = solve_linear_system(normal);
    Homography homography;
    homography.values = {{
        solution[0], solution[1], solution[2],
        solution[3], solution[4], solution[5],
        solution[6], solution[7], 1.0,
    }};
    return homography;
}

ReprojectionMetrics evaluate_reprojection(
    const Homography& source_to_destination,
    const std::vector<Point2d>& source,
    const std::vector<Point2d>& destination) {
    if (source.size() != destination.size() || source.empty()) {
        throw std::invalid_argument("reprojection needs paired points");
    }
    ReprojectionMetrics metrics;
    double sum = 0.0;
    double squared_sum = 0.0;
    for (std::size_t index = 0; index < source.size(); ++index) {
        const auto projected = source_to_destination.project(source[index]);
        const double dx = projected.x - destination[index].x;
        const double dy = projected.y - destination[index].y;
        const double error = std::hypot(dx, dy);
        sum += error;
        squared_sum += error * error;
        metrics.max_error_px = std::max(metrics.max_error_px, error);
        ++metrics.valid_points;
    }
    metrics.mean_error_px = sum / static_cast<double>(metrics.valid_points);
    metrics.rms_error_px = std::sqrt(squared_sum / static_cast<double>(metrics.valid_points));
    return metrics;
}

void warp_perspective_bilinear(
    const ImageView<const float>& input,
    ImageView<float> output,
    const Homography& source_to_destination,
    float fill_value) {
    if (input.channels() != output.channels()) {
        throw std::invalid_argument("warp input/output channel count mismatch");
    }
    const Homography destination_to_source = inverse(source_to_destination);
    for (std::uint32_t y = 0; y < output.height(); ++y) {
        for (std::uint32_t x = 0; x < output.width(); ++x) {
            const Point2d source_point = destination_to_source.project(
                {static_cast<double>(x), static_cast<double>(y)});
            const bool inside = source_point.x >= 0.0 && source_point.y >= 0.0 &&
                                source_point.x <= static_cast<double>(input.width() - 1U) &&
                                source_point.y <= static_cast<double>(input.height() - 1U);
            for (std::uint32_t channel = 0; channel < output.channels(); ++channel) {
                if (!inside) {
                    output(y, x, channel) = fill_value;
                    continue;
                }
                const auto x0 = static_cast<std::uint32_t>(std::floor(source_point.x));
                const auto y0 = static_cast<std::uint32_t>(std::floor(source_point.y));
                const auto x1 = std::min(x0 + 1U, input.width() - 1U);
                const auto y1 = std::min(y0 + 1U, input.height() - 1U);
                const float wx = static_cast<float>(source_point.x - static_cast<double>(x0));
                const float wy = static_cast<float>(source_point.y - static_cast<double>(y0));
                const float top = (1.0F - wx) * input(y0, x0, channel) + wx * input(y0, x1, channel);
                const float bottom = (1.0F - wx) * input(y1, x0, channel) + wx * input(y1, x1, channel);
                output(y, x, channel) = (1.0F - wy) * top + wy * bottom;
            }
        }
    }
}

}  // namespace cpp_isp
