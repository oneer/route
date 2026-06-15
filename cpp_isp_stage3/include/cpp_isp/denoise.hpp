#pragma once

#include "cpp_isp/border.hpp"
#include "cpp_isp/image.hpp"

#include <cstdint>
#include <vector>

namespace cpp_isp {

void box_filter(const ImageView<const float>& input,
                ImageView<float> output,
                std::uint32_t radius,
                BorderPolicy border_policy);

std::vector<float> make_gaussian_kernel_1d(std::uint32_t radius, float sigma);

void gaussian_filter(const ImageView<const float>& input,
                     ImageView<float> output,
                     std::uint32_t radius,
                     float sigma,
                     BorderPolicy border_policy);

void bilateral_filter(const ImageView<const float>& input,
                      ImageView<float> output,
                      std::uint32_t radius,
                      float sigma_spatial,
                      float sigma_range,
                      BorderPolicy border_policy);

void bilateral_filter_range_lut(const ImageView<const float>& input,
                                ImageView<float> output,
                                std::uint32_t radius,
                                float sigma_spatial,
                                float sigma_range,
                                std::uint32_t range_lut_bins,
                                BorderPolicy border_policy);

void bilateral_filter_range_lut_tiled(const ImageView<const float>& input,
                                      ImageView<float> output,
                                      std::uint32_t radius,
                                      float sigma_spatial,
                                      float sigma_range,
                                      std::uint32_t range_lut_bins,
                                      BorderPolicy border_policy,
                                      std::uint32_t tile_width,
                                      std::uint32_t tile_height);

void bilateral_filter_range_lut_threaded_rows(const ImageView<const float>& input,
                                              ImageView<float> output,
                                              std::uint32_t radius,
                                              float sigma_spatial,
                                              float sigma_range,
                                              std::uint32_t range_lut_bins,
                                              BorderPolicy border_policy,
                                              std::uint32_t thread_count);

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
