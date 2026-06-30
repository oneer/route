// 中文说明：Stage2 部署侧 OpenCV DNN ONNX 推理示例。
// 作用：读取普通图片，按 Python 训练时的 RGB/[0,1]/NCHW 约定送入 ONNX 模型，
// 保存复原图片并输出 warmup/repeats 延迟统计。
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
    // 中文说明：命令行参数依次为模型、输入图片、输出图片，以及可选延迟统计参数。
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

    // 中文说明：OpenCV 读图默认是 BGR；训练管线使用 RGB float，因此这里显式转换。
    cv::Mat rgb;
    cv::cvtColor(bgr, rgb, cv::COLOR_BGR2RGB);
    rgb.convertTo(rgb, CV_32F, 1.0 / 255.0);

    // 中文说明：blobFromImage 会把 HWC 图像整理为 NCHW batch，匹配 PyTorch 导出的 ONNX。
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
        // 中文说明：warmup 不计入最终延迟，避免首次推理初始化开销污染统计。
        net.forward();
    }
    std::vector<double> latencies;
    cv::Mat output;
    for (int i = 0; i < repeats; ++i) {
        // 中文说明：正式计时只覆盖 forward，用来衡量 OpenCV DNN 后端推理耗时。
        const auto start = std::chrono::high_resolution_clock::now();
        output = net.forward();
        const auto end = std::chrono::high_resolution_clock::now();
        latencies.push_back(
            std::chrono::duration<double, std::milli>(end - start).count());
    }
    if (output.dims != 4 || output.size[0] != 1 || output.size[1] != 3) {
        // 中文说明：本阶段图像模型约定输出 [1,3,H,W]，否则后处理无法按 RGB 三通道还原。
        std::cerr << "expected output shape [1,3,H,W]\n";
        return 1;
    }

    const int height = output.size[2];
    const int width = output.size[3];
    cv::Mat chw(3, height * width, CV_32F, output.ptr<float>());
    std::vector<cv::Mat> channels;
    for (int c = 0; c < 3; ++c) {
        // 中文说明：把 CHW 内存视图拆成三个二维通道，后面 merge 回 RGB 图像。
        channels.emplace_back(height, width, CV_32F, chw.ptr<float>(c));
    }

    cv::Mat restored_rgb;
    cv::merge(channels, restored_rgb);
    cv::Mat clipped;
    // 中文说明：模型输出可能略超出 [0,1]，保存 uint8 图片前需要裁剪。
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
    // 中文说明：均值、p50、p95 一起输出，便于报告平均速度和尾部波动。
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
