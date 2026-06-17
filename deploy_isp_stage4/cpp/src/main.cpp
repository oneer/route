#include "image_io.hpp"
#include "onnxruntime_runner.hpp"

#include <chrono>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void print_usage() {
    std::cerr
        << "Usage: stage4_ort_runner <model.onnx> <input.ppm> <output.ppm>\n"
        << "Input and output use RGB PPM P6 so the minimal runner has no image-library dependency.\n";
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        print_usage();
        return 2;
    }

    try {
        const std::string model_path = argv[1];
        const std::string input_path = argv[2];
        const std::string output_path = argv[3];

        const auto image = stage4::load_ppm_rgb_as_nchw(input_path);
        stage4::OnnxRuntimeRunner runner(model_path, "input", "output");

        const auto t0 = std::chrono::high_resolution_clock::now();
        const auto output = runner.run(image.nchw, 1, image.channels, image.height, image.width);
        const auto t1 = std::chrono::high_resolution_clock::now();
        const double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

        stage4::save_ppm_rgb_from_nchw(output_path, output.data(), image.width, image.height, image.channels);
        std::cout << "ORT C++ inference_ms=" << ms << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "stage4_ort_runner failed: " << e.what() << "\n";
        return 1;
    }
}

