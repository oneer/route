#include "cpp_isp/fixed_point.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

// 定点工具测试关注三个硬件常见行为：Q 格式转换、带四舍五入右移、码值饱和裁剪。
namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(float a, float b, float eps = 1e-6F) {
    return std::abs(a - b) <= eps;
}

void test_float_fixed_round_trip() {
    const auto fixed = cpp_isp::float_to_fixed(0.625F, 8);
    require(fixed == 160, "0.625 with 8 frac bits should be 160");
    require(near(cpp_isp::fixed_to_float(fixed, 8), 0.625F), "fixed round trip failed");
}

void test_round_shift() {
    require(cpp_isp::round_shift(7, 2) == 2, "positive round_shift failed");
    require(cpp_isp::round_shift(6, 2) == 2, "positive round_shift tie failed");
    require(cpp_isp::round_shift(-7, 2) == -2, "negative round_shift failed");
}

void test_saturate_to_bits() {
    require(cpp_isp::max_value_for_bits(10) == 1023, "10-bit max failed");
    require(cpp_isp::saturate_to_bits(-4, 8) == 0, "negative saturation failed");
    require(cpp_isp::saturate_to_bits(128, 8) == 128, "in-range saturation failed");
    require(cpp_isp::saturate_to_bits(999, 8) == 255, "high saturation failed");
}

void test_invalid_parameters() {
    bool threw = false;
    try {
        (void)cpp_isp::float_to_fixed(1.0F, 31);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    require(threw, "invalid fractional_bits should throw");
}

}  // namespace

int main() {
    try {
        test_float_fixed_round_trip();
        test_round_shift();
        test_saturate_to_bits();
        test_invalid_parameters();
        std::cout << "test_fixed_point passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_fixed_point failed: " << error.what() << '\n';
        return 1;
    }
}
