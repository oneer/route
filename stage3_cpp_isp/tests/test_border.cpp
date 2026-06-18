#include "cpp_isp/border.hpp"

#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void test_index_mapping() {
    require(cpp_isp::map_border_index(-1, 4, cpp_isp::BorderPolicy::Constant) == -1,
            "constant left border failed");
    require(cpp_isp::map_border_index(4, 4, cpp_isp::BorderPolicy::Constant) == -1,
            "constant right border failed");
    require(cpp_isp::map_border_index(-1, 4, cpp_isp::BorderPolicy::Replicate) == 0,
            "replicate left border failed");
    require(cpp_isp::map_border_index(4, 4, cpp_isp::BorderPolicy::Replicate) == 3,
            "replicate right border failed");
    require(cpp_isp::map_border_index(-1, 4, cpp_isp::BorderPolicy::Reflect) == 1,
            "reflect left border failed");
    require(cpp_isp::map_border_index(4, 4, cpp_isp::BorderPolicy::Reflect) == 2,
            "reflect right border failed");
    require(cpp_isp::map_border_index(-7, 1, cpp_isp::BorderPolicy::Reflect) == 0,
            "1x1 reflect left border failed");
    require(cpp_isp::map_border_index(7, 1, cpp_isp::BorderPolicy::Reflect) == 0,
            "1x1 reflect right border failed");
}

void test_sample_with_border() {
    cpp_isp::ImageBuffer<int> image(3, 2, 1);
    image(0, 0) = 1;
    image(0, 1) = 2;
    image(0, 2) = 3;
    image(1, 0) = 4;
    image(1, 1) = 5;
    image(1, 2) = 6;

    const auto view = image.view();
    require(cpp_isp::sample_with_border(view, 0, 1, 0, cpp_isp::BorderPolicy::Constant, -9) == 2,
            "inside sample failed");
    require(cpp_isp::sample_with_border(view, -1, 1, 0, cpp_isp::BorderPolicy::Constant, -9) == -9,
            "constant sample failed");
    require(cpp_isp::sample_with_border(view, -1, 1, 0, cpp_isp::BorderPolicy::Replicate, -9) == 2,
            "replicate sample failed");
    require(cpp_isp::sample_with_border(view, 2, 1, 0, cpp_isp::BorderPolicy::Reflect, -9) == 2,
            "reflect sample failed");
}

}  // namespace

int main() {
    try {
        test_index_mapping();
        test_sample_with_border();
        std::cout << "test_border passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_border failed: " << error.what() << '\n';
        return 1;
    }
}
