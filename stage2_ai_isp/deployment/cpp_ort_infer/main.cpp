#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

#include <onnxruntime_cxx_api.h>

struct TensorFile {
    std::array<int64_t, 4> shape{};
    std::vector<float> values;
};

TensorFile read_tensor(const std::string& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("failed to open input tensor: " + path);
    }
    std::array<int32_t, 4> shape32{};
    stream.read(reinterpret_cast<char*>(shape32.data()), sizeof(shape32));
    TensorFile tensor;
    int64_t count = 1;
    for (size_t i = 0; i < shape32.size(); ++i) {
        if (shape32[i] <= 0) {
            throw std::runtime_error("invalid tensor dimension");
        }
        tensor.shape[i] = shape32[i];
        count *= tensor.shape[i];
    }
    tensor.values.resize(static_cast<size_t>(count));
    stream.read(
        reinterpret_cast<char*>(tensor.values.data()),
        static_cast<std::streamsize>(tensor.values.size() * sizeof(float)));
    if (!stream) {
        throw std::runtime_error("input tensor payload is incomplete");
    }
    return tensor;
}

void write_tensor(
    const std::string& path,
    const std::array<int64_t, 4>& shape,
    const float* values,
    size_t count) {
    std::ofstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("failed to open output tensor: " + path);
    }
    std::array<int32_t, 4> shape32{};
    for (size_t i = 0; i < shape.size(); ++i) {
        shape32[i] = static_cast<int32_t>(shape[i]);
    }
    stream.write(reinterpret_cast<const char*>(shape32.data()), sizeof(shape32));
    stream.write(
        reinterpret_cast<const char*>(values),
        static_cast<std::streamsize>(count * sizeof(float)));
}

int main(int argc, char** argv) {
    if (argc < 4 || argc > 7) {
        std::cerr << "usage: stage2_ort_infer model.onnx input.f32 output.f32 "
                     "[warmup=5] [repeats=30] [metrics.json]\n";
        return 1;
    }
    try {
        const int warmup = argc >= 5 ? std::stoi(argv[4]) : 5;
        const int repeats = argc >= 6 ? std::stoi(argv[5]) : 30;
        if (warmup < 0 || repeats < 1) {
            throw std::runtime_error("warmup must be >=0 and repeats must be >=1");
        }

        TensorFile input = read_tensor(argv[2]);
        Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "stage2");
        Ort::SessionOptions options;
        options.SetGraphOptimizationLevel(
            GraphOptimizationLevel::ORT_ENABLE_ALL);
        const std::filesystem::path model_path(argv[1]);
        Ort::Session session(env, model_path.c_str(), options);
        Ort::AllocatorWithDefaultOptions allocator;
        auto input_name = session.GetInputNameAllocated(0, allocator);
        auto output_name = session.GetOutputNameAllocated(0, allocator);
        const char* input_names[] = {input_name.get()};
        const char* output_names[] = {output_name.get()};

        Ort::MemoryInfo memory = Ort::MemoryInfo::CreateCpu(
            OrtArenaAllocator, OrtMemTypeDefault);
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            memory,
            input.values.data(),
            input.values.size(),
            input.shape.data(),
            input.shape.size());

        auto run_once = [&]() {
            return session.Run(
                Ort::RunOptions{nullptr},
                input_names,
                &input_tensor,
                1,
                output_names,
                1);
        };
        for (int i = 0; i < warmup; ++i) {
            run_once();
        }

        std::vector<double> latencies;
        std::vector<Ort::Value> outputs;
        for (int i = 0; i < repeats; ++i) {
            const auto start = std::chrono::high_resolution_clock::now();
            outputs = run_once();
            const auto end = std::chrono::high_resolution_clock::now();
            latencies.push_back(
                std::chrono::duration<double, std::milli>(end - start).count());
        }

        auto output_shape_vector =
            outputs[0].GetTensorTypeAndShapeInfo().GetShape();
        if (output_shape_vector.size() != 4) {
            throw std::runtime_error("expected a four-dimensional output");
        }
        std::array<int64_t, 4> output_shape{};
        std::copy(
            output_shape_vector.begin(), output_shape_vector.end(),
            output_shape.begin());
        const size_t output_count =
            outputs[0].GetTensorTypeAndShapeInfo().GetElementCount();
        write_tensor(
            argv[3],
            output_shape,
            outputs[0].GetTensorData<float>(),
            output_count);

        std::sort(latencies.begin(), latencies.end());
        const double mean =
            std::accumulate(latencies.begin(), latencies.end(), 0.0) /
            latencies.size();
        std::cout << "saved: " << argv[3] << "\n";
        std::cout << "warmup: " << warmup << "\n";
        std::cout << "repeats: " << repeats << "\n";
        std::cout << "latency_mean_ms: " << mean << "\n";
        std::cout << "latency_p50_ms: "
                  << latencies[latencies.size() / 2] << "\n";
        std::cout << "latency_p95_ms: "
                  << latencies[static_cast<size_t>(
                         0.95 * (latencies.size() - 1))]
                  << "\n";
        if (argc >= 7) {
            std::ofstream metrics(argv[6]);
            if (!metrics) {
                throw std::runtime_error("failed to open metrics JSON");
            }
            metrics << "{\n"
                    << "  \"backend\": \"onnxruntime_cpp_cpu\",\n"
                    << "  \"warmup\": " << warmup << ",\n"
                    << "  \"repeats\": " << repeats << ",\n"
                    << "  \"latency_mean_ms\": " << mean << ",\n"
                    << "  \"latency_p50_ms\": "
                    << latencies[latencies.size() / 2] << ",\n"
                    << "  \"latency_p95_ms\": "
                    << latencies[static_cast<size_t>(
                           0.95 * (latencies.size() - 1))]
                    << "\n}\n";
        }
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
