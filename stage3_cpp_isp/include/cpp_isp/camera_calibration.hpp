#pragma once

#include "cpp_isp/image.hpp"

#include <array>
#include <cstddef>
#include <vector>

namespace cpp_isp {

struct Point2d {
    double x = 0.0;
    double y = 0.0;
};

struct Homography {
    std::array<double, 9> values{{1.0, 0.0, 0.0,
                                  0.0, 1.0, 0.0,
                                  0.0, 0.0, 1.0}};

    Point2d project(const Point2d& point) const;
};

struct ReprojectionMetrics {
    double mean_error_px = 0.0;
    double rms_error_px = 0.0;
    double max_error_px = 0.0;
    std::size_t valid_points = 0;
};

// Least-squares planar homography with h22 fixed to 1. At least four
// non-degenerate correspondences are required.
Homography solve_planar_homography(
    const std::vector<Point2d>& source,
    const std::vector<Point2d>& destination);

ReprojectionMetrics evaluate_reprojection(
    const Homography& source_to_destination,
    const std::vector<Point2d>& source,
    const std::vector<Point2d>& destination);

// Inverse-map destination pixels and bilinearly sample the source. The caller
// owns the output buffer so repeated frames do not allocate inside the warp.
void warp_perspective_bilinear(
    const ImageView<const float>& input,
    ImageView<float> output,
    const Homography& source_to_destination,
    float fill_value = 0.0F);

}  // namespace cpp_isp
