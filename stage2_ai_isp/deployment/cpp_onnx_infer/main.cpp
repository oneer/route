#include <chrono>
#include <iostream>
#include <opencv2/dnn.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: stage2_onnx_infer model.onnx input.png output.png\n";
        return 1;
    }

    const std::string model_path = argv[1];
    const std::string input_path = argv[2];
    const std::string output_path = argv[3];

    cv::Mat bgr = cv::imread(input_path, cv::IMREAD_COLOR);
    if (bgr.empty()) {
        std::cerr << "failed to read input: " << input_path << "\n";
        return 1;
    }

    cv::Mat rgb;
    cv::cvtColor(bgr, rgb, cv::COLOR_BGR2RGB);
    rgb.convertTo(rgb, CV_32F, 1.0 / 255.0);

    cv::Mat blob = cv::dnn::blobFromImage(rgb);
    cv::dnn::Net net = cv::dnn::readNetFromONNX(model_path);
    net.setInput(blob);

    const auto start = std::chrono::high_resolution_clock::now();
    cv::Mat output = net.forward();
    const auto end = std::chrono::high_resolution_clock::now();
    const double ms = std::chrono::duration<double, std::milli>(end - start).count();

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
    cv::imwrite(output_path, restored_bgr);

    std::cout << "saved: " << output_path << "\n";
    std::cout << "latency_ms: " << ms << "\n";
    return 0;
}
