#include "image_io.hpp"

#include <algorithm>
#include <fstream>
#include <stdexcept>

namespace stage4 {

namespace {

std::string read_token(std::istream& in) {
    // PPM 头部可能包含注释；这里逐 token 读取并跳过注释行。
    std::string token;
    in >> token;
    while (!token.empty() && token[0] == '#') {
        std::string ignored;
        std::getline(in, ignored);
        in >> token;
    }
    return token;
}

}  // namespace

ImageTensor load_ppm_rgb_as_nchw(const std::string& path) {
    // 只实现部署样例需要的 P6 RGB 8-bit，保持 C++ runner 轻量可读。
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("Failed to open input image: " + path);
    }

    const std::string magic = read_token(in);
    if (magic != "P6") {
        throw std::runtime_error("Only binary PPM P6 is supported for the minimal Stage 4 runner.");
    }

    ImageTensor image;
    image.width = std::stoi(read_token(in));
    image.height = std::stoi(read_token(in));
    const int max_value = std::stoi(read_token(in));
    if (max_value != 255) {
        throw std::runtime_error("Only 8-bit PPM is supported.");
    }
    in.get();  // consume one whitespace byte after the header

    std::vector<unsigned char> hwc(static_cast<size_t>(image.width) * image.height * image.channels);
    in.read(reinterpret_cast<char*>(hwc.data()), static_cast<std::streamsize>(hwc.size()));
    if (!in) {
        throw std::runtime_error("Failed to read full PPM payload: " + path);
    }

    image.nchw.assign(hwc.size(), 0.0f);
    const int hw = image.width * image.height;
    // PPM 存储为 HWC/RGB/RGB...，ONNX 输入要求 NCHW/CCC...，这里完成布局转换。
    for (int y = 0; y < image.height; ++y) {
        for (int x = 0; x < image.width; ++x) {
            const int hwc_base = (y * image.width + x) * image.channels;
            const int spatial = y * image.width + x;
            for (int c = 0; c < image.channels; ++c) {
                image.nchw[c * hw + spatial] = static_cast<float>(hwc[hwc_base + c]) / 255.0f;
            }
        }
    }
    return image;
}

void save_ppm_rgb_from_nchw(const std::string& path, const float* data, int width, int height, int channels) {
    // 输出只支持 RGB，因为 Stage 4 导出的降噪模型也是三通道 RGB。
    if (channels != 3) {
        throw std::runtime_error("Only RGB output is supported.");
    }
    std::ofstream out(path, std::ios::binary);
    if (!out) {
        throw std::runtime_error("Failed to open output image: " + path);
    }
    out << "P6\n" << width << " " << height << "\n255\n";

    std::vector<unsigned char> hwc(static_cast<size_t>(width) * height * channels);
    const int hw = width * height;
    // 保存图片时从 NCHW 转回 HWC，并执行 clamp + round 到 uint8。
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const int hwc_base = (y * width + x) * channels;
            const int spatial = y * width + x;
            for (int c = 0; c < channels; ++c) {
                const float value = std::clamp(data[c * hw + spatial], 0.0f, 1.0f);
                hwc[hwc_base + c] = static_cast<unsigned char>(value * 255.0f + 0.5f);
            }
        }
    }
    out.write(reinterpret_cast<const char*>(hwc.data()), static_cast<std::streamsize>(hwc.size()));
}

void save_float32_tensor(const std::string& path, const float* data, size_t count) {
    // 直接写二进制 float32，没有头信息；比较脚本按同样 dtype 读取。
    std::ofstream out(path, std::ios::binary);
    if (!out) {
        throw std::runtime_error("Failed to open tensor output: " + path);
    }
    out.write(
        reinterpret_cast<const char*>(data),
        static_cast<std::streamsize>(count * sizeof(float)));
}

}  // namespace stage4
