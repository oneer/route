#pragma once

#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <vector>

namespace cpp_isp {

// ImageView 是“不拥有内存”的图像视图，只记录数据指针和布局信息。
// 本阶段统一使用 planar 布局：同一个通道的像素连续存放，通道之间用 channel_stride 跳转。
// 访问公式是 data[c * channel_stride + y * row_stride + x]，这让算法代码可以同时处理
// 1 通道 RAW/灰度图和 3/4 通道 RGB/RGBA 数据。
template <typename T>
class ImageView {
public:
    ImageView() = default;

    template <typename U, typename = std::enable_if_t<std::is_convertible<U*, T*>::value>>
    ImageView(const ImageView<U>& other)
        : ImageView(other.data(),
                    other.width(),
                    other.height(),
                    other.channels(),
                    other.row_stride(),
                    other.channel_stride()) {}

    ImageView(T* data,
              std::uint32_t width,
              std::uint32_t height,
              std::uint32_t channels,
              std::uint32_t row_stride,
              std::uint32_t channel_stride)
        : data_(data),
          width_(width),
          height_(height),
          channels_(channels),
          row_stride_(row_stride),
          channel_stride_(channel_stride) {
        if (data == nullptr || width == 0 || height == 0 || channels == 0) {
            throw std::invalid_argument("invalid ImageView shape or data");
        }
        if (row_stride < width) {
            throw std::invalid_argument("row_stride must be >= width");
        }
        const auto minimum_channel_stride =
            static_cast<std::uint64_t>(row_stride) * static_cast<std::uint64_t>(height);
        if (minimum_channel_stride > std::numeric_limits<std::uint32_t>::max() ||
            static_cast<std::uint64_t>(channel_stride) < minimum_channel_stride) {
            throw std::invalid_argument("channel_stride is too small");
        }
    }

    T& operator()(std::uint32_t y, std::uint32_t x, std::uint32_t c = 0) const {
        return data_[offset(y, x, c)];
    }

    // at() 做越界检查，适合测试和调试；operator() 不检查边界，适合内层像素循环。
    T& at(std::uint32_t y, std::uint32_t x, std::uint32_t c = 0) const {
        if (x >= width_ || y >= height_ || c >= channels_) {
            throw std::out_of_range("ImageView index out of range");
        }
        return (*this)(y, x, c);
    }

    std::uint32_t width() const { return width_; }
    std::uint32_t height() const { return height_; }
    std::uint32_t channels() const { return channels_; }
    std::uint32_t row_stride() const { return row_stride_; }
    std::uint32_t channel_stride() const { return channel_stride_; }
    T* data() const { return data_; }

private:
    // row_stride 允许每行尾部有 padding；channel_stride 允许每个平面之间有间隔。
    // 这样可以模拟真实 ISP/硬件缓冲区里常见的对齐布局，而不是假设完全紧密排列。
    std::size_t offset(std::uint32_t y, std::uint32_t x, std::uint32_t c) const {
        return static_cast<std::size_t>(c) * channel_stride_ +
               static_cast<std::size_t>(y) * row_stride_ + x;
    }

    T* data_ = nullptr;
    std::uint32_t width_ = 0;
    std::uint32_t height_ = 0;
    std::uint32_t channels_ = 0;
    std::uint32_t row_stride_ = 0;
    std::uint32_t channel_stride_ = 0;
};

// ImageBuffer 是拥有内存的容器；它负责分配 vector，然后用 view() 暴露成 ImageView。
// 这种分层让算法函数只依赖 ImageView，既能处理自己分配的缓冲，也能处理外部传入的数据。
template <typename T>
class ImageBuffer {
public:
    ImageBuffer() = default;

    ImageBuffer(std::uint32_t width,
                std::uint32_t height,
                std::uint32_t channels = 1,
                std::uint32_t row_stride = 0)
        : width_(width),
          height_(height),
          channels_(channels),
          row_stride_(row_stride == 0 ? width : row_stride) {
        if (width == 0 || height == 0 || channels == 0) {
            throw std::invalid_argument("invalid ImageBuffer shape");
        }
        if (row_stride_ < width) {
            throw std::invalid_argument("row_stride must be >= width");
        }
        const auto channel_stride =
            static_cast<std::uint64_t>(row_stride_) * static_cast<std::uint64_t>(height_);
        if (channel_stride > std::numeric_limits<std::uint32_t>::max()) {
            throw std::overflow_error("channel_stride exceeds uint32 range");
        }
        channel_stride_ = static_cast<std::uint32_t>(channel_stride);
        const auto element_count = channel_stride * static_cast<std::uint64_t>(channels_);
        if (element_count > static_cast<std::uint64_t>(data_.max_size())) {
            throw std::length_error("ImageBuffer storage exceeds vector max_size");
        }
        data_.resize(static_cast<std::size_t>(element_count));
    }

    ImageView<T> view() {
        return ImageView<T>(data_.data(), width_, height_, channels_, row_stride_, channel_stride_);
    }

    ImageView<const T> view() const {
        return ImageView<const T>(data_.data(), width_, height_, channels_, row_stride_, channel_stride_);
    }

    T& operator()(std::uint32_t y, std::uint32_t x, std::uint32_t c = 0) {
        return view()(y, x, c);
    }

    const T& operator()(std::uint32_t y, std::uint32_t x, std::uint32_t c = 0) const {
        return view()(y, x, c);
    }

    std::uint32_t width() const { return width_; }
    std::uint32_t height() const { return height_; }
    std::uint32_t channels() const { return channels_; }
    std::uint32_t row_stride() const { return row_stride_; }
    std::uint32_t channel_stride() const { return channel_stride_; }
    std::size_t storage_size() const { return data_.size(); }
    std::vector<T>& storage() { return data_; }
    const std::vector<T>& storage() const { return data_; }

private:
    std::uint32_t width_ = 0;
    std::uint32_t height_ = 0;
    std::uint32_t channels_ = 0;
    std::uint32_t row_stride_ = 0;
    std::uint32_t channel_stride_ = 0;
    std::vector<T> data_;
};

}  // namespace cpp_isp
