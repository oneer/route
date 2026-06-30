#include "cpp_isp/image.hpp"

namespace cpp_isp {
namespace {
// ImageBuffer/ImageView 的实现都在头文件模板里；这个 cpp 文件保留为库目标的稳定编译单元。
constexpr int keep_translation_unit_non_empty = 0;
}
}  // namespace cpp_isp
