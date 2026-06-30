#pragma once

#include <cstdint>

namespace cpp_isp {

// 把浮点数转换成 Q 格式定点整数：实际值 * 2^fractional_bits 后四舍五入。
std::int32_t float_to_fixed(float value, std::uint32_t fractional_bits);
// 把 Q 格式定点整数还原成浮点值。
float fixed_to_float(std::int32_t value, std::uint32_t fractional_bits);
// 带四舍五入的右移，常用于定点乘法后把多出来的小数位移回目标格式。
std::int64_t round_shift(std::int64_t value, std::uint32_t shift);
// n bit 无符号码值的最大值，例如 12 bit -> 4095。
std::uint32_t max_value_for_bits(std::uint32_t bits);
// 把整数饱和到 [0, 2^bits - 1]，模拟硬件输出裁剪。
std::uint32_t saturate_to_bits(std::int64_t value, std::uint32_t bits);

}  // namespace cpp_isp
