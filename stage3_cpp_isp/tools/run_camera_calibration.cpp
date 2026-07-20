#include "cpp_isp/camera_calibration.hpp"

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void read_correspondences(const std::string& path,
                          std::vector<cpp_isp::Point2d>& source,
                          std::vector<cpp_isp::Point2d>& destination) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open correspondence CSV");
    }
    std::string line;
    std::getline(input, line);
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        std::replace(line.begin(), line.end(), ',', ' ');
        std::istringstream row(line);
        cpp_isp::Point2d src;
        cpp_isp::Point2d dst;
        if (!(row >> src.x >> src.y >> dst.x >> dst.y)) {
            throw std::runtime_error("invalid correspondence CSV row");
        }
        source.push_back(src);
        destination.push_back(dst);
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: run_camera_calibration <correspondences.csv> <metrics.csv> <max_mean_error_px>\n";
        return 2;
    }
    try {
        std::vector<cpp_isp::Point2d> source;
        std::vector<cpp_isp::Point2d> destination;
        read_correspondences(argv[1], source, destination);
        const auto homography = cpp_isp::solve_planar_homography(source, destination);
        const auto metrics = cpp_isp::evaluate_reprojection(homography, source, destination);
        const double threshold = std::stod(argv[3]);
        std::ofstream output(argv[2]);
        if (!output) {
            throw std::runtime_error("cannot create metrics CSV");
        }
        output << std::setprecision(17) << "key,value\n";
        for (std::size_t index = 0; index < homography.values.size(); ++index) {
            output << 'h' << index / 3 << index % 3 << ',' << homography.values[index] << '\n';
        }
        output << "valid_points," << metrics.valid_points << '\n';
        output << "mean_reprojection_error_px," << metrics.mean_error_px << '\n';
        output << "rms_reprojection_error_px," << metrics.rms_error_px << '\n';
        output << "max_reprojection_error_px," << metrics.max_error_px << '\n';
        output << "threshold_px," << threshold << '\n';
        output << "passed," << (metrics.mean_error_px <= threshold ? 1 : 0) << '\n';
        std::cout << "valid_points=" << metrics.valid_points
                  << " mean_reprojection_error_px=" << metrics.mean_error_px
                  << " max_reprojection_error_px=" << metrics.max_error_px << '\n';
        return metrics.mean_error_px <= threshold ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "run_camera_calibration failed: " << error.what() << '\n';
        return 1;
    }
}
