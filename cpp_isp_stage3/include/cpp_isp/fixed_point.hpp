#pragma once

#include <cstdint>

namespace cpp_isp {

std::int32_t float_to_fixed(float value, std::uint32_t fractional_bits);
float fixed_to_float(std::int32_t value, std::uint32_t fractional_bits);
std::int64_t round_shift(std::int64_t value, std::uint32_t shift);
std::uint32_t max_value_for_bits(std::uint32_t bits);
std::uint32_t saturate_to_bits(std::int64_t value, std::uint32_t bits);

}  // namespace cpp_isp
