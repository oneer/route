#include "cpp_isp/tone_lut.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(float a, float b, float eps) {
    return std::abs(a - b) <= eps;
}

void test_lut_reinhard_known_values() {
    cpp_isp::ToneLutParams params;
    params.curve = cpp_isp::ToneCurve::Reinhard;
    params.input_bits = 12;
    params.output_bits = 12;
    params.input_max = 4.0F;
    cpp_isp::ToneCurveLut lut(params);

    require(lut.values().size() == 4096, "12-bit LUT should have 4096 entries");
    require(near(lut.apply(0.0F), 0.0F, 1.0F / 4095.0F), "Reinhard LUT zero failed");
    require(near(lut.apply(1.0F), 0.5F, 2.0F / 4095.0F), "Reinhard LUT one failed");
    require(near(lut.apply(3.0F), 0.75F, 2.0F / 4095.0F), "Reinhard LUT three failed");
}

void test_lut_saturates_domain() {
    cpp_isp::ToneLutParams params;
    params.curve = cpp_isp::ToneCurve::Reinhard;
    params.input_bits = 10;
    params.output_bits = 8;
    params.input_max = 1.0F;
    cpp_isp::ToneCurveLut lut(params);

    require(lut.apply_code(-1.0F) == lut.apply_code(0.0F), "LUT should clamp negative input");
    require(lut.apply_code(5.0F) == lut.apply_code(1.0F), "LUT should clamp above input_max");
}

void test_lut_tone_map_matches_float_reasonably() {
    cpp_isp::ImageBuffer<float> input(17, 9, 3);
    cpp_isp::ImageBuffer<float> float_output(17, 9, 3);
    cpp_isp::ImageBuffer<float> lut_output(17, 9, 3);

    for (std::uint32_t y = 0; y < input.height(); ++y) {
        for (std::uint32_t x = 0; x < input.width(); ++x) {
            input(y, x, 0) = 0.05F + static_cast<float>(x) / 4.0F;
            input(y, x, 1) = 0.04F + static_cast<float>(y) / 5.0F;
            input(y, x, 2) = 0.02F + static_cast<float>(x + y) / 12.0F;
        }
    }

    cpp_isp::ToneMappingParams float_params;
    float_params.curve = cpp_isp::ToneCurve::Filmic;
    float_params.exposure = 0.45F;
    float_params.preserve_luminance = true;
    const auto input_view = static_cast<const cpp_isp::ImageBuffer<float>&>(input).view();
    cpp_isp::tone_map(input_view, float_output.view(), float_params);

    cpp_isp::ToneLutParams lut_params;
    lut_params.curve = cpp_isp::ToneCurve::Filmic;
    lut_params.input_bits = 12;
    lut_params.output_bits = 12;
    lut_params.input_max = 4.0F;
    lut_params.exposure = 0.45F;
    lut_params.preserve_luminance = true;
    cpp_isp::ToneCurveLut lut(lut_params);
    cpp_isp::tone_map_lut(input_view, lut_output.view(), lut);

    float max_error = 0.0F;
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                max_error = std::max(max_error, std::abs(float_output(y, x, c) - lut_output(y, x, c)));
            }
        }
    }
    require(max_error < 0.004F, "12-bit LUT should stay close to float TM");
}

void test_invalid_lut_params() {
    cpp_isp::ToneLutParams params;
    params.input_bits = 1;
    bool threw = false;
    try {
        cpp_isp::ToneCurveLut lut(params);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    require(threw, "invalid input_bits should throw");
}

}  // namespace

int main() {
    try {
        test_lut_reinhard_known_values();
        test_lut_saturates_domain();
        test_lut_tone_map_matches_float_reasonably();
        test_invalid_lut_params();
        std::cout << "test_tone_lut passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_tone_lut failed: " << error.what() << '\n';
        return 1;
    }
}
