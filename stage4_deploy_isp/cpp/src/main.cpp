#include "image_io.hpp"
#include "onnxruntime_runner.hpp"

#include <chrono>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void print_usage() {
    // 使用 PPM 而不是 PNG/JPEG，目的是让最小 runner 不依赖额外图像库。
    std::cerr
        << "Usage: stage4_ort_runner <model.onnx> <input.ppm> <output.ppm>"
        << " [output.f32] [warmup=3] [runs=10]\n"
        << "Input and output use RGB PPM P6 so the minimal runner has no image-library dependency.\n";
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 4 || argc > 7) {
        print_usage();
        return 2;
    }

    try {
        const std::string model_path = argv[1];
        const std::string input_path = argv[2];
        const std::string output_path = argv[3];
        const std::string tensor_path = argc >= 5 ? argv[4] : "";
        const int warmup = argc >= 6 ? std::stoi(argv[5]) : 3;
        const int runs = argc >= 7 ? std::stoi(argv[6]) : 10;
        if (warmup < 0 || runs <= 0) {
            throw std::runtime_error("warmup must be >= 0 and runs must be > 0.");
        }

        // load_ppm_rgb_as_nchw 已完成 /255.0 和 HWC -> NCHW，runner 可直接推理。
        const auto image = stage4::load_ppm_rgb_as_nchw(input_path);
        stage4::OnnxRuntimeRunner runner(model_path, "input", "output");

        std::vector<float> output;
        // warmup 不计时，用于消除首次图优化、内存分配等一次性开销。
        for (int i = 0; i < warmup; ++i) {
            output = runner.run(image.nchw, 1, image.channels, image.height, image.width);
        }
        std::vector<double> timings;
        timings.reserve(static_cast<size_t>(runs));
        for (int i = 0; i < runs; ++i) {
            // 这里只统计 ORT run 的时间，不包含读图和写图。
            const auto t0 = std::chrono::high_resolution_clock::now();
            output = runner.run(image.nchw, 1, image.channels, image.height, image.width);
            const auto t1 = std::chrono::high_resolution_clock::now();
            timings.push_back(std::chrono::duration<double, std::milli>(t1 - t0).count());
        }
        double total_ms = 0.0;
        for (double value : timings) {
            total_ms += value;
        }

        // 同时保存可视化 PPM 和可选裸张量，分别服务肉眼检查与严格对齐检查。
        stage4::save_ppm_rgb_from_nchw(output_path, output.data(), image.width, image.height, image.channels);
        if (!tensor_path.empty() && tensor_path != "-") {
            stage4::save_float32_tensor(tensor_path, output.data(), output.size());
        }
        std::cout << "ORT C++ warmup=" << warmup
                  << " runs=" << runs
                  << " inference_mean_ms=" << total_ms / runs
                  << " tensor_output=" << (tensor_path.empty() ? "disabled" : tensor_path)
                  << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "stage4_ort_runner failed: " << e.what() << "\n";
        return 1;
    }
}
