#pragma once

#include "cpp_isp/border.hpp"
#include "cpp_isp/image.hpp"

#include <cstdint>
#include <vector>

namespace cpp_isp {

// Box filter：固定窗口内简单平均。速度快、实现直观，但会明显模糊边缘。
void box_filter(const ImageView<const float>& input,
                ImageView<float> output,
                std::uint32_t radius,
                BorderPolicy border_policy);

// 生成一维高斯核；二维高斯滤波会拆成“横向一次 + 纵向一次”以降低复杂度。
std::vector<float> make_gaussian_kernel_1d(std::uint32_t radius, float sigma);

// Gaussian filter：按距离加权平均，比 box filter 更平滑自然，但仍不会保护边缘。
void gaussian_filter(const ImageView<const float>& input,
                     ImageView<float> output,
                     std::uint32_t radius,
                     float sigma,
                     BorderPolicy border_policy);

// Bilateral filter：同时考虑空间距离和像素值差异，尽量在降噪时保留边缘。
void bilateral_filter(const ImageView<const float>& input,
                      ImageView<float> output,
                      std::uint32_t radius,
                      float sigma_spatial,
                      float sigma_range,
                      BorderPolicy border_policy);

// 用查表近似 range weight，减少内层循环里的 exp() 调用，便于性能优化和硬件思维训练。
void bilateral_filter_range_lut(const ImageView<const float>& input,
                                ImageView<float> output,
                                std::uint32_t radius,
                                float sigma_spatial,
                                float sigma_range,
                                std::uint32_t range_lut_bins,
                                BorderPolicy border_policy);

// 分块版本用于观察 cache locality 和 tile 尺寸对性能的影响。
void bilateral_filter_range_lut_tiled(const ImageView<const float>& input,
                                      ImageView<float> output,
                                      std::uint32_t radius,
                                      float sigma_spatial,
                                      float sigma_range,
                                      std::uint32_t range_lut_bins,
                                      BorderPolicy border_policy,
                                      std::uint32_t tile_width,
                                      std::uint32_t tile_height);

// 按行分配多线程任务，适合快速验证并行加速，但负载均衡不如动态 tile。
void bilateral_filter_range_lut_threaded_rows(const ImageView<const float>& input,
                                              ImageView<float> output,
                                              std::uint32_t radius,
                                              float sigma_spatial,
                                              float sigma_range,
                                              std::uint32_t range_lut_bins,
                                              BorderPolicy border_policy,
                                              std::uint32_t thread_count);

// 多线程 tile 版本用原子计数器动态领取任务，适合图像块耗时不完全一致的情况。
void bilateral_filter_range_lut_threaded_tiles(const ImageView<const float>& input,
                                               ImageView<float> output,
                                               std::uint32_t radius,
                                               float sigma_spatial,
                                               float sigma_range,
                                               std::uint32_t range_lut_bins,
                                               BorderPolicy border_policy,
                                               std::uint32_t tile_width,
                                               std::uint32_t tile_height,
                                               std::uint32_t thread_count);

}  // namespace cpp_isp
