#include "cpp_isp/denoise.hpp"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <functional>
#include <memory>
#include <stdexcept>
#include <vector>

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <process.h>
#include <windows.h>
#endif

namespace cpp_isp {

namespace {

void validate_bilateral_args(const ImageView<const float>& input,
                             const ImageView<float>& output,
                             float sigma_spatial,
                             float sigma_range) {
    if (input.width() != output.width() || input.height() != output.height() ||
        input.channels() != output.channels()) {
        throw std::invalid_argument("input and output shapes do not match");
    }
    if (sigma_spatial <= 0.0F || sigma_range <= 0.0F) {
        throw std::invalid_argument("bilateral sigmas must be positive");
    }
}

float spatial_weight(int dx, int dy, float sigma_spatial) {
    const float d2 = static_cast<float>(dx * dx + dy * dy);
    return std::exp(-0.5F * d2 / (sigma_spatial * sigma_spatial));
}

float range_weight(float diff, float sigma_range) {
    return std::exp(-0.5F * diff * diff / (sigma_range * sigma_range));
}

std::vector<float> make_range_lut(std::uint32_t bins, float sigma_range) {
    if (bins < 2) {
        throw std::invalid_argument("range_lut_bins must be >= 2");
    }

    std::vector<float> lut(bins);
    for (std::uint32_t i = 0; i < bins; ++i) {
        const float diff = static_cast<float>(i) / static_cast<float>(bins - 1);
        lut[i] = range_weight(diff, sigma_range);
    }
    return lut;
}

float lookup_range_weight(const std::vector<float>& lut, float diff) {
    const float clamped = std::min(std::abs(diff), 1.0F);
    const float pos = clamped * static_cast<float>(lut.size() - 1);
    const auto idx0 = static_cast<std::size_t>(pos);
    const auto idx1 = std::min(idx0 + 1, lut.size() - 1);
    const float t = pos - static_cast<float>(idx0);
    return lut[idx0] * (1.0F - t) + lut[idx1] * t;
}

void validate_tile_args(std::uint32_t tile_width, std::uint32_t tile_height) {
    if (tile_width == 0 || tile_height == 0) {
        throw std::invalid_argument("tile dimensions must be positive");
    }
}

std::uint32_t normalize_thread_count(std::uint32_t thread_count) {
    if (thread_count == 0) {
        return 1;
    }
    return thread_count;
}

void bilateral_lut_rect(const ImageView<const float>& input,
                        ImageView<float> output,
                        std::uint32_t radius,
                        float sigma_spatial,
                        const std::vector<float>& lut,
                        BorderPolicy border_policy,
                        std::uint32_t y_begin,
                        std::uint32_t y_end,
                        std::uint32_t x_begin,
                        std::uint32_t x_end) {
    const int r = static_cast<int>(radius);
    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = y_begin; y < y_end; ++y) {
            for (std::uint32_t x = x_begin; x < x_end; ++x) {
                const float center = input(y, x, c);
                float weighted_sum = 0.0F;
                float weight_sum = 0.0F;
                for (int dy = -r; dy <= r; ++dy) {
                    for (int dx = -r; dx <= r; ++dx) {
                        const float value = sample_with_border(input,
                                                               static_cast<int>(y) + dy,
                                                               static_cast<int>(x) + dx,
                                                               c,
                                                               border_policy,
                                                               center);
                        const float weight =
                            spatial_weight(dx, dy, sigma_spatial) * lookup_range_weight(lut, value - center);
                        weighted_sum += weight * value;
                        weight_sum += weight;
                    }
                }
                output(y, x, c) = weight_sum > 0.0F ? weighted_sum / weight_sum : center;
            }
        }
    }
}

struct TileRect {
    std::uint32_t y_begin;
    std::uint32_t y_end;
    std::uint32_t x_begin;
    std::uint32_t x_end;
};

std::vector<TileRect> make_tiles(std::uint32_t width,
                                 std::uint32_t height,
                                 std::uint32_t tile_width,
                                 std::uint32_t tile_height) {
    validate_tile_args(tile_width, tile_height);
    std::vector<TileRect> tiles;
    for (std::uint32_t y = 0; y < height; y += tile_height) {
        for (std::uint32_t x = 0; x < width; x += tile_width) {
            tiles.push_back(TileRect{y,
                                     std::min(y + tile_height, height),
                                     x,
                                     std::min(x + tile_width, width)});
        }
    }
    return tiles;
}

#if defined(_WIN32)
struct ThreadTask {
    std::function<void()> fn;
};

unsigned __stdcall run_thread_task(void* data) {
    static_cast<ThreadTask*>(data)->fn();
    return 0;
}

void run_parallel_tasks(std::vector<std::function<void()>> task_functions) {
    std::vector<std::unique_ptr<ThreadTask>> tasks;
    std::vector<HANDLE> handles;
    tasks.reserve(task_functions.size());
    handles.reserve(task_functions.size());

    for (auto& fn : task_functions) {
        auto task = std::make_unique<ThreadTask>();
        task->fn = std::move(fn);
        const auto handle = reinterpret_cast<HANDLE>(
            _beginthreadex(nullptr, 0, run_thread_task, task.get(), 0, nullptr));
        if (handle == nullptr) {
            throw std::runtime_error("failed to create worker thread");
        }
        handles.push_back(handle);
        tasks.push_back(std::move(task));
    }

    if (!handles.empty()) {
        WaitForMultipleObjects(static_cast<DWORD>(handles.size()), handles.data(), TRUE, INFINITE);
    }
    for (const auto handle : handles) {
        CloseHandle(handle);
    }
}
#else
void run_parallel_tasks(std::vector<std::function<void()>> task_functions) {
    for (auto& fn : task_functions) {
        fn();
    }
}
#endif

}  // namespace

void bilateral_filter(const ImageView<const float>& input,
                      ImageView<float> output,
                      std::uint32_t radius,
                      float sigma_spatial,
                      float sigma_range,
                      BorderPolicy border_policy) {
    validate_bilateral_args(input, output, sigma_spatial, sigma_range);
    const int r = static_cast<int>(radius);

    for (std::uint32_t c = 0; c < input.channels(); ++c) {
        for (std::uint32_t y = 0; y < input.height(); ++y) {
            for (std::uint32_t x = 0; x < input.width(); ++x) {
                const float center = input(y, x, c);
                float weighted_sum = 0.0F;
                float weight_sum = 0.0F;
                for (int dy = -r; dy <= r; ++dy) {
                    for (int dx = -r; dx <= r; ++dx) {
                        const float value = sample_with_border(input,
                                                               static_cast<int>(y) + dy,
                                                               static_cast<int>(x) + dx,
                                                               c,
                                                               border_policy,
                                                               center);
                        const float weight = spatial_weight(dx, dy, sigma_spatial) *
                                             range_weight(value - center, sigma_range);
                        weighted_sum += weight * value;
                        weight_sum += weight;
                    }
                }
                output(y, x, c) = weight_sum > 0.0F ? weighted_sum / weight_sum : center;
            }
        }
    }
}

void bilateral_filter_range_lut(const ImageView<const float>& input,
                                ImageView<float> output,
                                std::uint32_t radius,
                                float sigma_spatial,
                                float sigma_range,
                                std::uint32_t range_lut_bins,
                                BorderPolicy border_policy) {
    validate_bilateral_args(input, output, sigma_spatial, sigma_range);
    const auto lut = make_range_lut(range_lut_bins, sigma_range);
    bilateral_lut_rect(input, output, radius, sigma_spatial, lut, border_policy, 0, input.height(), 0, input.width());
}

void bilateral_filter_range_lut_tiled(const ImageView<const float>& input,
                                      ImageView<float> output,
                                      std::uint32_t radius,
                                      float sigma_spatial,
                                      float sigma_range,
                                      std::uint32_t range_lut_bins,
                                      BorderPolicy border_policy,
                                      std::uint32_t tile_width,
                                      std::uint32_t tile_height) {
    validate_bilateral_args(input, output, sigma_spatial, sigma_range);
    const auto lut = make_range_lut(range_lut_bins, sigma_range);
    for (const auto& tile : make_tiles(input.width(), input.height(), tile_width, tile_height)) {
        bilateral_lut_rect(input,
                           output,
                           radius,
                           sigma_spatial,
                           lut,
                           border_policy,
                           tile.y_begin,
                           tile.y_end,
                           tile.x_begin,
                           tile.x_end);
    }
}

void bilateral_filter_range_lut_threaded_rows(const ImageView<const float>& input,
                                              ImageView<float> output,
                                              std::uint32_t radius,
                                              float sigma_spatial,
                                              float sigma_range,
                                              std::uint32_t range_lut_bins,
                                              BorderPolicy border_policy,
                                              std::uint32_t thread_count) {
    validate_bilateral_args(input, output, sigma_spatial, sigma_range);
    thread_count = std::min(normalize_thread_count(thread_count), input.height());
    const auto lut = make_range_lut(range_lut_bins, sigma_range);
    std::vector<std::function<void()>> tasks;
    tasks.reserve(thread_count);

    for (std::uint32_t i = 0; i < thread_count; ++i) {
        const std::uint32_t y_begin = (input.height() * i) / thread_count;
        const std::uint32_t y_end = (input.height() * (i + 1)) / thread_count;
        tasks.emplace_back([&, y_begin, y_end] {
            bilateral_lut_rect(input,
                               output,
                               radius,
                               sigma_spatial,
                               lut,
                               border_policy,
                               y_begin,
                               y_end,
                               0,
                               input.width());
        });
    }

    run_parallel_tasks(std::move(tasks));
}

void bilateral_filter_range_lut_threaded_tiles(const ImageView<const float>& input,
                                               ImageView<float> output,
                                               std::uint32_t radius,
                                               float sigma_spatial,
                                               float sigma_range,
                                               std::uint32_t range_lut_bins,
                                               BorderPolicy border_policy,
                                               std::uint32_t tile_width,
                                               std::uint32_t tile_height,
                                               std::uint32_t thread_count) {
    validate_bilateral_args(input, output, sigma_spatial, sigma_range);
    const auto tiles = make_tiles(input.width(), input.height(), tile_width, tile_height);
    thread_count = std::min(normalize_thread_count(thread_count), static_cast<std::uint32_t>(tiles.size()));
    const auto lut = make_range_lut(range_lut_bins, sigma_range);
    std::atomic<std::uint32_t> next_tile{0};
    std::vector<std::function<void()>> tasks;
    tasks.reserve(thread_count);

    for (std::uint32_t i = 0; i < thread_count; ++i) {
        tasks.emplace_back([&] {
            while (true) {
                const std::uint32_t tile_index = next_tile.fetch_add(1);
                if (tile_index >= tiles.size()) {
                    break;
                }
                const auto& tile = tiles[tile_index];
                bilateral_lut_rect(input,
                                   output,
                                   radius,
                                   sigma_spatial,
                                   lut,
                                   border_policy,
                                   tile.y_begin,
                                   tile.y_end,
                                   tile.x_begin,
                                   tile.x_end);
            }
        });
    }

    run_parallel_tasks(std::move(tasks));
}

}  // namespace cpp_isp
