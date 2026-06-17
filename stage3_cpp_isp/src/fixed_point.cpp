#include "cpp_isp/fixed_point.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

namespace cpp_isp {

std::int32_t float_to_fixed(float value, std::uint32_t fractional_bits) {
    if (fractional_bits >= 30) {
        throw std::invalid_argument("fractional_bits must be < 30");
    }
    const double scale = static_cast<double>(std::int64_t{1} << fractional_bits);
    const double rounded = std::round(static_cast<double>(value) * scale);
    if (rounded > static_cast<double>(std::numeric_limits<std::int32_t>::max()) ||
        rounded < static_cast<double>(std::numeric_limits<std::int32_t>::min())) {
        throw std::overflow_error("fixed-point value overflows int32");
    }
    return static_cast<std::int32_t>(rounded);
}

float fixed_to_float(std::int32_t value, std::uint32_t fractional_bits) {
    if (fractional_bits >= 30) {
        throw std::invalid_argument("fractional_bits must be < 30");
    }
    const float scale = static_cast<float>(std::int64_t{1} << fractional_bits);
    return static_cast<float>(value) / scale;
}

std::int64_t round_shift(std::int64_t value, std::uint32_t shift) {
    if (shift == 0) {
        return value;
    }
    if (shift >= 62) {
        throw std::invalid_argument("shift is too large");
    }
    const std::int64_t offset = std::int64_t{1} << (shift - 1U);
    if (value >= 0) {
        return (value + offset) >> shift;
    }
    return -(((-value) + offset) >> shift);
}

std::uint32_t max_value_for_bits(std::uint32_t bits) {
    if (bits == 0 || bits > 31) {
        throw std::invalid_argument("bits must be in [1, 31]");
    }
    return (std::uint32_t{1} << bits) - 1U;
}

std::uint32_t saturate_to_bits(std::int64_t value, std::uint32_t bits) {
    const std::uint32_t max_value = max_value_for_bits(bits);
    if (value <= 0) {
        return 0;
    }
    if (value >= static_cast<std::int64_t>(max_value)) {
        return max_value;
    }
    return static_cast<std::uint32_t>(value);
}

}  // namespace cpp_isp
