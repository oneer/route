#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace cpp_isp {

// CPF32 是本项目自定义的极简浮点张量格式：
// 文本头 "CPF32\nwidth height channels\n" + little-endian float32 原始 payload。
struct TensorF32 {
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    std::uint32_t channels = 0;
    std::vector<float> data;

    std::size_t size() const;
};

// 读取/写入 CPF32，用于 C++ 实现和 Python reference 之间传递完全可复现的测试向量。
TensorF32 read_cpf32(const std::string& path);
void write_cpf32(const std::string& path, const TensorF32& tensor);

}  // namespace cpp_isp
