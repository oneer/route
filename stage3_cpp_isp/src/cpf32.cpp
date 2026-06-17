#include "cpp_isp/cpf32.hpp"

#include <fstream>
#include <stdexcept>

namespace cpp_isp {

std::size_t TensorF32::size() const {
    return static_cast<std::size_t>(width) * height * channels;
}

TensorF32 read_cpf32(const std::string& path) {
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

    return tensor;
}

void write_cpf32(const std::string& path, const TensorF32& tensor) {
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
