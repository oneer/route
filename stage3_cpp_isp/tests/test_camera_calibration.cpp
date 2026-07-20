#include "cpp_isp/camera_calibration.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        cpp_isp::Homography expected;
        expected.values = {{1.02, 0.03, 12.0, -0.02, 0.98, 7.0, 0.0002, -0.0001, 1.0}};
        const std::vector<cpp_isp::Point2d> source{{0.0, 0.0}, {100.0, 0.0}, {0.0, 80.0},
                                                   {100.0, 80.0}, {50.0, 20.0}, {30.0, 60.0}};
        std::vector<cpp_isp::Point2d> destination;
        for (const auto& point : source) {
            destination.push_back(expected.project(point));
        }
        const auto fitted = cpp_isp::solve_planar_homography(source, destination);
        const auto metrics = cpp_isp::evaluate_reprojection(fitted, source, destination);
        require(metrics.valid_points == source.size(), "valid point count mismatch");
        require(metrics.max_error_px < 1.0e-7, "synthetic homography did not align");

        cpp_isp::ImageBuffer<float> input(4, 3, 1);
        cpp_isp::ImageBuffer<float> output(4, 3, 1);
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                input(y, x) = static_cast<float>(10U * y + x);
            }
        }
        cpp_isp::warp_perspective_bilinear(
            static_cast<const cpp_isp::ImageBuffer<float>&>(input).view(), output.view(), cpp_isp::Homography{});
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                require(std::abs(input(y, x) - output(y, x)) < 1.0e-6F, "identity warp mismatch");
            }
        }

        bool rejected = false;
        try {
            const std::vector<cpp_isp::Point2d> collinear{{0.0, 0.0}, {1.0, 0.0}, {2.0, 0.0}, {3.0, 0.0}};
            (void)cpp_isp::solve_planar_homography(collinear, collinear);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "degenerate correspondences must be rejected");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
