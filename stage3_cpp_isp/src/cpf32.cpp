#include "cpp_isp/cpf32.hpp"

#include <cstdint>
#include <fstream>
#include <stdexcept>

namespace cpp_isp {
namespace {

bool host_is_little_endian() {
    const std::uint16_t value = 1;
    return *reinterpret_cast<const unsigned char*>(&value) == 1;
}

void require_little_endian_host() {
    if (!host_is_little_endian()) {
        throw std::runtime_error("CPF32 requires a little-endian host");
    }
}

}  // namespace

std::size_t TensorF32::size() const {
    return static_cast<std::size_t>(width) * height * channels;
}

TensorF32 read_cpf32(const std::string& path) {
    require_little_endian_host();
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("failed to open CPF32 file: " + path);
    }

    std::string magic;
    in >> magic;
    if (magic != "CPF32") {
        throw std::runtime_error("invalid CPF32 magic in: " + path);
    }

    TensorF32 tensor;
    in >> tensor.width >> tensor.height >> tensor.channels;
    if (!in || tensor.width == 0 || tensor.height == 0 || tensor.channels == 0) {
        throw std::runtime_error("invalid CPF32 shape in: " + path);
    }

    in.get();
    tensor.data.resize(tensor.size());
    in.read(reinterpret_cast<char*>(tensor.data.data()),
            static_cast<std::streamsize>(tensor.data.size() * sizeof(float)));
    if (!in) {
        throw std::runtime_error("truncated CPF32 payload in: " + path);
    }
    if (in.peek() != std::char_traits<char>::eof()) {
        throw std::runtime_error("CPF32 payload size does not match shape in: " + path);
    }

    return tensor;
}

void write_cpf32(const std::string& path, const TensorF32& tensor) {
    require_little_endian_host();
    if (tensor.width == 0 || tensor.height == 0 || tensor.channels == 0) {
        throw std::runtime_error("CPF32 tensor dimensions must be positive");
    }
    if (tensor.size() != tensor.data.size()) {
        throw std::runtime_error("CPF32 tensor shape does not match data size");
    }

    std::ofstream out(path, std::ios::binary);
    if (!out) {
        throw std::runtime_error("failed to write CPF32 file: " + path);
    }

    out << "CPF32\n";
    out << tensor.width << ' ' << tensor.height << ' ' << tensor.channels << '\n';
    out.write(reinterpret_cast<const char*>(tensor.data.data()),
              static_cast<std::streamsize>(tensor.data.size() * sizeof(float)));
}

}  // namespace cpp_isp
