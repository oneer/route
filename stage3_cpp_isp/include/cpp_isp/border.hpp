#pragma once

#include "cpp_isp/image.hpp"

#include <cstdint>
#include <type_traits>

namespace cpp_isp {

// 卷积/滤波访问边界外像素时的策略：
// Constant 返回常数，Replicate 复制最近边缘像素，Reflect 镜像回图像内部。
enum class BorderPolicy {
    Constant,
    Replicate,
    Reflect,
};

// 把可能越界的一维坐标映射回合法坐标；Constant 策略用 -1 表示“使用常数值”。
int map_border_index(int index, int size, BorderPolicy policy);

template <typename T>
std::remove_const_t<T> sample_with_border(const ImageView<T>& image,
                                          int y,
                                          int x,
                                          std::uint32_t c,
                                          BorderPolicy policy,
                                          std::remove_const_t<T> constant_value = {}) {
    // 先分别处理 y/x 轴，再统一采样；这样二维边界逻辑不会散落在每个滤波器里。
    const int mapped_y = map_border_index(y, static_cast<int>(image.height()), policy);
    const int mapped_x = map_border_index(x, static_cast<int>(image.width()), policy);
    if (mapped_y < 0 || mapped_x < 0) {
        return constant_value;
    }
    return image(static_cast<std::uint32_t>(mapped_y), static_cast<std::uint32_t>(mapped_x), c);
}

}  // namespace cpp_isp
