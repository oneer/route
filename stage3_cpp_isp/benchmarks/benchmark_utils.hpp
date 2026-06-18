#pragma once

#include <algorithm>
#include <chrono>
#include <stdexcept>
#include <vector>

namespace cpp_isp_bench {

template <typename Fn>
double median_ms(Fn&& fn, int warmup_runs, int measured_runs) {
    if (warmup_runs < 0 || measured_runs <= 0) {
        throw std::invalid_argument("invalid benchmark run count");
    }
    for (int i = 0; i < warmup_runs; ++i) {
        fn();
    }

    std::vector<double> samples;
    samples.reserve(static_cast<std::size_t>(measured_runs));
    for (int i = 0; i < measured_runs; ++i) {
        const auto begin = std::chrono::steady_clock::now();
        fn();
        const auto end = std::chrono::steady_clock::now();
        samples.push_back(std::chrono::duration<double, std::milli>(end - begin).count());
    }
    std::sort(samples.begin(), samples.end());
    const std::size_t middle = samples.size() / 2;
    if (samples.size() % 2 == 1) {
        return samples[middle];
    }
    return 0.5 * (samples[middle - 1] + samples[middle]);
}

}  // namespace cpp_isp_bench
