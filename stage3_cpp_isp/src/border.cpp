#include "cpp_isp/border.hpp"

#include <stdexcept>

namespace cpp_isp {

int map_border_index(int index, int size, BorderPolicy policy) {
    if (size <= 0) {
        throw std::invalid_argument("border size must be positive");
    }

    if (index >= 0 && index < size) {
        return index;
    }

    switch (policy) {
        case BorderPolicy::Constant:
            return -1;
        case BorderPolicy::Replicate:
            // 复制边界：左侧全部取 0，右侧全部取 size - 1。
            return index < 0 ? 0 : size - 1;
        case BorderPolicy::Reflect:
            // 镜像边界：-1 -> 1，size -> size - 2。while 支持半径远大于图像尺寸的情况。
            if (size == 1) {
                return 0;
            }
            while (index < 0 || index >= size) {
                if (index < 0) {
                    index = -index;
                }
                if (index >= size) {
                    index = 2 * size - 2 - index;
                }
            }
            return index;
    }

    return -1;
}

}  // namespace cpp_isp
