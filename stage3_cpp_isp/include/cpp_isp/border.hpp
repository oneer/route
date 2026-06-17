#pragma once

#include "cpp_isp/image.hpp"

#include <cstdint>
#include <type_traits>

namespace cpp_isp {

enum class BorderPolicy {
    Constant,
    Replicate,
    Reflect,
};

int map_border_index(int index, int size, BorderPolicy policy);

template <typename T>
std::remove_const_t<T> sample_with_border(const ImageView<T>& image,
                                          int y,
                                          int x,
                                          std::uint32_t c,
                                          BorderPolicy policy,
                                          std::remove_const_t<T> constant_value = {}) {
    const int mapped_y = map_border_index(y, static_cast<int>(image.height()), policy);
    const int mapped_x = map_border_index(x, static_cast<int>(image.width()), policy);
    if (mapped_y < 0 || mapped_x < 0) {
        return constant_value;
    }
    return image(static_cast<std::uint32_t>(mapped_y), static_cast<std::uint32_t>(mapped_x), c);
}

}  // namespace cpp_isp
