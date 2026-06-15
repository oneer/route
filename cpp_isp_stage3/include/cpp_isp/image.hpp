#pragma once

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <type_traits>
#include <vector>

namespace cpp_isp {

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
        if (channel_stride < static_cast<std::uint32_t>(row_stride * height)) {
            throw std::invalid_argument("channel_stride is too small");
        }
    }

    T& operator()(std::uint32_t y, std::uint32_t x, std::uint32_t c = 0) const {
        return data_[offset(y, x, c)];
    }

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
          row_stride_(row_stride == 0 ? width : row_stride),
          channel_stride_(row_stride_ * height) {
        if (width == 0 || height == 0 || channels == 0) {
            throw std::invalid_argument("invalid ImageBuffer shape");
        }
        if (row_stride_ < width) {
            throw std::invalid_argument("row_stride must be >= width");
        }
        data_.resize(static_cast<std::size_t>(channel_stride_) * channels_);
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
