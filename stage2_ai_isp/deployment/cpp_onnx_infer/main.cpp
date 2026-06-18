#include <algorithm>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>
#include <opencv2/dnn.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

int main(int argc, char** argv) {
    if (argc < 4 || argc > 6) {
        std::cerr << "usage: stage2_onnx_infer model.onnx input.png output.png "
                     "[warmup=5] [repeats=30]\n";
        return 1;
    }

    const std::string model_path = argv[1];
    const std::string input_path = argv[2];
    const std::string output_path = argv[3];
    const int warmup = argc >= 5 ? std::stoi(argv[4]) : 5;
    const int repeats = argc >= 6 ? std::stoi(argv[5]) : 30;
    if (warmup < 0 || repeats < 1) {
        std::cerr << "warmup must be >= 0 and repeats must be >= 1\n";
        return 1;
    }

    cv::Mat bgr = cv::imread(input_path, cv::IMREAD_COLOR);
    if (bgr.empty()) {
        std::cerr << "failed to read input: " << input_path << "\n";
        return 1;
    }

    cv::Mat rgb;
    cv::cvtColor(bgr, rgb, cv::COLOR_BGR2RGB);
    rgb.convertTo(rgb, CV_32F, 1.0 / 255.0);

    cv::Mat blob = cv::dnn::blobFromImage(rgb);
    cv::dnn::Net net;
    try {
        net = cv::dnn::readNetFromONNX(model_path);
    } catch (const cv::Exception& error) {
        std::cerr << "failed to load ONNX: " << error.what() << "\n";
        return 1;
    }
    net.setInput(blob);

    for (int i = 0; i < warmup; ++i) {
        net.forward();
    }
    std::vector<double> latencies;
    cv::Mat output;
    for (int i = 0; i < repeats; ++i) {
        const auto start = std::chrono::high_resolution_clock::now();
        output = net.forward();
        const auto end = std::chrono::high_resolution_clock::now();
        latencies.push_back(
            std::chrono::duration<double, std::milli>(end - start).count());
    }
    if (output.dims != 4 || output.size[0] != 1 || output.size[1] != 3) {
        std::cerr << "expected output shape [1,3,H,W]\n";
        return 1;
    }

    const int height = output.size[2];
    const int width = output.size[3];
    cv::Mat chw(3, height * width, CV_32F, output.ptr<float>());
    std::vector<cv::Mat> channels;
    for (int c = 0; c < 3; ++c) {
        channels.emplace_back(height, width, CV_32F, chw.ptr<float>(c));
    }

    cv::Mat restored_rgb;
    cv::merge(channels, restored_rgb);
    cv::Mat clipped;
    cv::max(restored_rgb, 0.0, clipped);
    cv::min(clipped, 1.0, clipped);
    restored_rgb = clipped;
    restored_rgb.convertTo(restored_rgb, CV_8U, 255.0);

    cv::Mat restored_bgr;
    cv::cvtColor(restored_rgb, restored_bgr, cv::COLOR_RGB2BGR);
    const std::filesystem::path output_file(output_path);
    if (output_file.has_parent_path()) {
        std::filesystem::create_directories(output_file.parent_path());
    }
    if (!cv::imwrite(output_path, restored_bgr)) {
        std::cerr << "failed to write output: " << output_path << "\n";
        return 1;
    }

    std::sort(latencies.begin(), latencies.end());
    const double mean_ms =
        std::accumulate(latencies.begin(), latencies.end(), 0.0) / latencies.size();
    const double p50_ms = latencies[latencies.size() / 2];
    const double p95_ms =
        latencies[static_cast<size_t>(0.95 * (latencies.size() - 1))];
    std::cout << "saved: " << output_path << "\n";
    std::cout << "warmup: " << warmup << "\n";
    std::cout << "repeats: " << repeats << "\n";
    std::cout << "latency_mean_ms: " << mean_ms << "\n";
    std::cout << "latency_p50_ms: " << p50_ms << "\n";
    std::cout << "latency_p95_ms: " << p95_ms << "\n";
    return 0;
}
