#include "cpp_isp/metrics.hpp"

#ifdef CPP_ISP_HAS_BENCHMARK
#include <benchmark/benchmark.h>
#else
#include <chrono>
#include <iostream>
#endif

#include <vector>

static cpp_isp::TensorF32 make_tensor(std::uint32_t width, std::uint32_t height) {
    cpp_isp::TensorF32 tensor;
    tensor.width = width;
    tensor.height = height;
    tensor.channels = 1;
    tensor.data.resize(tensor.size());
    for (std::size_t i = 0; i < tensor.data.size(); ++i) {
        tensor.data[i] = static_cast<float>((i % 1024) / 1023.0);
    }
    return tensor;
}

#ifdef CPP_ISP_HAS_BENCHMARK
static void BM_CompareIdentical(benchmark::State& state) {
    const auto tensor = make_tensor(static_cast<std::uint32_t>(state.range(0)),
                                    static_cast<std::uint32_t>(state.range(1)));
    for (auto _ : state) {
        benchmark::DoNotOptimize(cpp_isp::compare_tensors(tensor, tensor, 1e-6));
    }
}

BENCHMARK(BM_CompareIdentical)->Args({1920, 1080})->Args({3840, 2160});
BENCHMARK_MAIN();
#else
int main() {
    const auto tensor = make_tensor(1920, 1080);
    const auto begin = std::chrono::steady_clock::now();
    auto metrics = cpp_isp::compare_tensors(tensor, tensor, 1e-6);
    const auto end = std::chrono::steady_clock::now();
    const auto ms = std::chrono::duration<double, std::milli>(end - begin).count();

    std::cout << "fallback smoke benchmark\n";
    std::cout << "values: " << metrics.total_values << '\n';
    std::cout << "elapsed_ms: " << ms << '\n';
    return metrics.failed_pixels == 0 ? 0 : 1;
}
#endif
