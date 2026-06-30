#pragma once

#include <algorithm>
#include <chrono>
#include <stdexcept>
#include <vector>

namespace cpp_isp_bench {

// 简单基准计时工具：先 warmup，再记录多次耗时，最后取中位数降低偶发抖动影响。
template <typename Fn>
double median_ms(Fn&& fn, int warmup_runs, int measured_runs) {
    if (warmup_runs < 0 || measured_runs <= 0) {
        throw std::invalid_argument("invalid benchmark run count");
    }
    for (int i = 0; i < warmup_runs; ++i) {
        // warmup 不计入结果，用来触发缓存、分配器和分支预测进入稳定状态。
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
    // 中位数比平均值更不容易被单次系统调度尖峰拖偏。
    const std::size_t middle = samples.size() / 2;
    if (samples.size() % 2 == 1) {
        return samples[middle];
    }
    return 0.5 * (samples[middle - 1] + samples[middle]);
}

}  // namespace cpp_isp_bench
