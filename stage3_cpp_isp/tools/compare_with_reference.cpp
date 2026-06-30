#include "cpp_isp/cpf32.hpp"
#include "cpp_isp/metrics.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>

// 命令行对齐检查工具：读取 reference/output 两个 CPF32 文件，输出误差指标。
// 返回码也表达测试结果：0 表示所有值都在 threshold 内，1 表示存在超差或读取失败。
int main(int argc, char** argv) {
    if (argc < 3 || argc > 4) {
        std::cerr << "usage: compare_with_reference <reference.cpf32> <output.cpf32> [threshold]\n";
        return 2;
    }

    const double threshold = argc == 4 ? std::atof(argv[3]) : 1e-6;

    try {
        // CPF32 是 C++ 与 Python reference 之间的公共中间格式。
        const auto reference = cpp_isp::read_cpf32(argv[1]);
        const auto output = cpp_isp::read_cpf32(argv[2]);
        const auto metrics = cpp_isp::compare_tensors(reference, output, threshold);

        std::cout << std::fixed << std::setprecision(10);
        std::cout << "shape: " << reference.width << "x" << reference.height
                  << "x" << reference.channels << '\n';
        std::cout << "threshold: " << threshold << '\n';
        std::cout << "max_abs_error: " << metrics.max_abs_error << '\n';
        std::cout << "mean_abs_error: " << metrics.mean_abs_error << '\n';
        std::cout << "rmse: " << metrics.rmse << '\n';
        std::cout << "psnr: " << metrics.psnr << '\n';
        std::cout << "failed_values: " << metrics.failed_pixels << " / "
                  << metrics.total_values << '\n';

        // 让脚本/CI 可以直接根据进程退出码判断是否对齐成功。
        return metrics.failed_pixels == 0 ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "compare failed: " << error.what() << '\n';
        return 1;
    }
}
