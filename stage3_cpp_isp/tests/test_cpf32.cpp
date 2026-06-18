#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/metrics.hpp"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

struct TempFile {
    explicit TempFile(std::string path) : path(std::move(path)) {}
    ~TempFile() { std::remove(path.c_str()); }
    std::string path;
};

void test_hwc_round_trip() {
    TempFile file("test_cpf32_hwc_round_trip.tmp");
    cpp_isp::TensorF32 tensor;
    tensor.width = 2;
    tensor.height = 1;
    tensor.channels = 3;
    tensor.data = {1.0F, 2.0F, 3.0F, 4.0F, 5.0F, 6.0F};

    cpp_isp::write_cpf32(file.path, tensor);
    const auto loaded = cpp_isp::read_cpf32(file.path);

    require(loaded.width == 2 && loaded.height == 1 && loaded.channels == 3,
            "CPF32 shape round trip failed");
    require(loaded.data == tensor.data, "CPF32 HWC payload order changed");
}

void test_rejects_payload_size_mismatch() {
    TempFile file("test_cpf32_trailing_payload.tmp");
    {
        std::ofstream out(file.path, std::ios::binary);
        out << "CPF32\n1 1 1\n";
        const float value = 0.5F;
        out.write(reinterpret_cast<const char*>(&value), sizeof(value));
        out.put('\0');
    }

    bool threw = false;
    try {
        (void)cpp_isp::read_cpf32(file.path);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    require(threw, "CPF32 reader should reject trailing payload bytes");
}

void test_alignment_rejects_non_finite_values() {
    cpp_isp::TensorF32 reference;
    reference.width = 1;
    reference.height = 1;
    reference.channels = 1;
    reference.data = {0.0F};

    auto output = reference;
    output.data[0] = std::numeric_limits<float>::quiet_NaN();

    bool threw = false;
    try {
        (void)cpp_isp::compare_tensors(reference, output, 1.0e-6);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    require(threw, "alignment must not report NaN as a passing value");
}

}  // namespace

int main() {
    try {
        test_hwc_round_trip();
        test_rejects_payload_size_mismatch();
        test_alignment_rejects_non_finite_values();
        std::cout << "test_cpf32 passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test_cpf32 failed: " << error.what() << '\n';
        return 1;
    }
}
