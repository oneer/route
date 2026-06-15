#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace cpp_isp {

struct TensorF32 {
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    std::uint32_t channels = 0;
    std::vector<float> data;

    std::size_t size() const;
};

TensorF32 read_cpf32(const std::string& path);
void write_cpf32(const std::string& path, const TensorF32& tensor);

}  // namespace cpp_isp
