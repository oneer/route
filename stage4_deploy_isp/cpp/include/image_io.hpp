#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace stage4 {

// C++ runner 内部统一使用 NCHW float32/[0,1]，与导出的 ONNX 输入合同一致。
struct ImageTensor {
    int width = 0;
    int height = 0;
    int channels = 3;
    std::vector<float> nchw;
};

// 读取最简单的二进制 PPM P6 RGB 图片，并完成 HWC uint8 -> NCHW float32 转换。
ImageTensor load_ppm_rgb_as_nchw(const std::string& path);

// 将模型输出的 NCHW float32 裁剪到 [0,1]，再写回 PPM P6 RGB 图片。
void save_ppm_rgb_from_nchw(const std::string& path, const float* data, int width, int height, int channels);

// 保存裸 float32 张量，供 Python 脚本逐元素比较 C++ 与 Python ORT 输出。
void save_float32_tensor(const std::string& path, const float* data, size_t count);

}  // namespace stage4
