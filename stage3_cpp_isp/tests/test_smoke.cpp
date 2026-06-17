#ifdef CPP_ISP_HAS_GTEST
#include <gtest/gtest.h>
#endif

#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/metrics.hpp"

#include <iostream>
#include <stdexcept>

#ifdef CPP_ISP_HAS_GTEST
TEST(SmokeTest, IdenticalTensorsHaveZeroError) {
    cpp_isp::TensorF32 a;
    a.width = 2;
    a.height = 2;
    a.channels = 1;
    a.data = {0.0F, 0.25F, 0.5F, 1.0F};

    const auto metrics = cpp_isp::compare_tensors(a, a, 1e-6);
    EXPECT_EQ(metrics.failed_pixels, 0U);
    EXPECT_DOUBLE_EQ(metrics.max_abs_error, 0.0);
}
#else
int main() {
    cpp_isp::TensorF32 a;
    a.width = 2;
    a.height = 2;
    a.channels = 1;
    a.data = {0.0F, 0.25F, 0.5F, 1.0F};

    const auto metrics = cpp_isp::compare_tensors(a, a, 1e-6);
    if (metrics.failed_pixels != 0 || metrics.max_abs_error != 0.0) {
        std::cerr << "smoke test failed\n";
        return 1;
    }

    std::cout << "smoke test passed\n";
    return 0;
}
#endif
