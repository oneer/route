#include "cuda_preprocess.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct PpmImage {
    int width = 0;
    int height = 0;
    int channels = 3;
    std::vector<unsigned char> hwc;
};

std::string read_token(std::istream& in) {
    std::string token;
    in >> token;
    while (!token.empty() && token[0] == '#') {
        std::string ignored;
        std::getline(in, ignored);
        in >> token;
    }
    return token;
}

PpmImage load_ppm_hwc(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("Failed to open input image: " + path);
    }
    if (read_token(in) != "P6") {
        throw std::runtime_error("Only binary PPM P6 is supported.");
    }
    PpmImage image;
    image.width = std::stoi(read_token(in));
    image.height = std::stoi(read_token(in));
    const int max_value = std::stoi(read_token(in));
    if (max_value != 255) {
        throw std::runtime_error("Only 8-bit PPM is supported.");
    }
    in.get();
    image.hwc.resize(static_cast<size_t>(image.width) * image.height * image.channels);
    in.read(reinterpret_cast<char*>(image.hwc.data()), static_cast<std::streamsize>(image.hwc.size()));
    if (!in) {
        throw std::runtime_error("Failed to read full PPM payload: " + path);
    }
    return image;
}

double cpu_normalize(const PpmImage& image, std::vector<float>& output, int runs) {
    const int hw = image.width * image.height;
    output.assign(image.hwc.size(), 0.0f);
    const auto start = std::chrono::steady_clock::now();
    for (int run = 0; run < runs; ++run) {
        for (int pixel = 0; pixel < hw; ++pixel) {
            const int hwc_base = pixel * image.channels;
            for (int c = 0; c < image.channels; ++c) {
                output[c * hw + pixel] = static_cast<float>(image.hwc[hwc_base + c]) / 255.0f;
            }
        }
    }
    const auto end = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(end - start).count() / runs;
}

std::pair<float, float> compare_outputs(const std::vector<float>& a, const std::vector<float>& b) {
    float max_abs = 0.0f;
    double sum_abs = 0.0;
    for (size_t i = 0; i < a.size(); ++i) {
        const float err = std::fabs(a[i] - b[i]);
        max_abs = std::max(max_abs, err);
        sum_abs += err;
    }
    return {max_abs, static_cast<float>(sum_abs / a.size())};
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: stage4_cuda_preprocess_benchmark input.ppm output.csv [runs]\n";
        return 2;
    }
    const std::string input_path = argv[1];
    const std::string output_path = argv[2];
    const int runs = argc >= 4 ? std::stoi(argv[3]) : 200;

    try {
        const PpmImage image = load_ppm_hwc(input_path);
        std::vector<float> cpu_output;
        std::vector<float> gpu_output(image.hwc.size(), 0.0f);
        const double cpu_ms = cpu_normalize(image, cpu_output, runs);
        const float gpu_kernel_ms = stage4::cuda_normalize_u8_to_float_nchw(
            image.hwc.data(),
            gpu_output.data(),
            image.width,
            image.height,
            image.channels,
            runs);
        const auto [max_abs, mean_abs] = compare_outputs(cpu_output, gpu_output);

        std::ofstream out(output_path);
        if (!out) {
            throw std::runtime_error("Failed to open output csv: " + output_path);
        }
        out << "input,width,height,channels,runs,cpu_preprocess_mean_ms,cuda_kernel_mean_ms,"
               "max_abs_error,mean_abs_error\n";
        out << input_path << "," << image.width << "," << image.height << "," << image.channels << "," << runs
            << "," << cpu_ms << "," << gpu_kernel_ms << "," << max_abs << "," << mean_abs << "\n";

        std::cout << "cpu_preprocess_mean_ms=" << cpu_ms << "\n";
        std::cout << "cuda_kernel_mean_ms=" << gpu_kernel_ms << "\n";
        std::cout << "max_abs_error=" << max_abs << "\n";
        std::cout << "mean_abs_error=" << mean_abs << "\n";
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << "\n";
        return 1;
    }
    return 0;
}
