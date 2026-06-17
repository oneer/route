#include "cpp_isp/image.hpp"

#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void test_stride_greater_than_width() {
    cpp_isp::ImageBuffer<float> image(3, 2, 1, 5);
    image(0, 0) = 1.0F;
    image(0, 2) = 2.0F;
    image(1, 0) = 3.0F;

    require(image.row_stride() == 5, "row stride mismatch");
    require(image.channel_stride() == 10, "channel stride mismatch");
    require(image.storage_size() == 10, "storage size mismatch");
    require(image(0, 0) == 1.0F, "value mismatch at 0,0");
    require(image(0, 2) == 2.0F, "value mismatch at 0,2");
    require(image(1, 0) == 3.0F, "value mismatch at 1,0");
}

void test_planar4_indexing() {
    cpp_isp::ImageBuffer<int> image(4, 3, 4);
    for (std::uint32_t c = 0; c < image.channels(); ++c) {
        for (std::uint32_t y = 0; y < image.height(); ++y) {
            for (std::uint32_t x = 0; x < image.width(); ++x) {
                image(y, x, c) = static_cast<int>(c * 100 + y * 10 + x);
            }
        }
    }

    require(image(2, 3, 0) == 23, "channel 0 indexing failed");
    require(image(2, 3, 1) == 123, "channel 1 indexing failed");
    require(image(2, 3, 2) == 223, "channel 2 indexing failed");
    require(image(2, 3, 3) == 323, "channel 3 indexing failed");
}

void test_bounds_checked_access() {
    cpp_isp::ImageBuffer<float> image(2, 2, 1);
    bool threw = false;
    try {
        image.view().at(2, 0);
    } catch (const std::out_of_range&) {
        threw = true;
    }
    require(threw, "at() should throw for out-of-range access");
}

}  // namespace

int main() {
    try {
        test_stride_greater_than_width();
        test_planar4_indexing();
        test_bounds_checked_access();
        std::cout << "test_image passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_image failed: " << error.what() << '\n';
        return 1;
    }
}
