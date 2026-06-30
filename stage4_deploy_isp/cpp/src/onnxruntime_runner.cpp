#include "onnxruntime_runner.hpp"

#include <array>
#include <filesystem>
#include <stdexcept>

namespace stage4 {

OnnxRuntimeRunner::OnnxRuntimeRunner(
    const std::string& model_path,
    const std::string& input_name,
    const std::string& output_name)
    : env_(ORT_LOGGING_LEVEL_WARNING, "stage4_ort_runner"),
      session_options_(),
      session_(nullptr),
      memory_info_(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault)),
      input_name_(input_name),
      output_name_(output_name) {
    // 单线程设置让 CPU benchmark 更稳定；图优化打开以贴近实际部署。
    session_options_.SetIntraOpNumThreads(1);
    session_options_.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    const std::filesystem::path model_file(model_path);
    session_ = Ort::Session(env_, model_file.c_str(), session_options_);
}

std::vector<float> OnnxRuntimeRunner::run(
    const std::vector<float>& input,
    int batch,
    int channels,
    int height,
    int width) {
    const std::array<int64_t, 4> input_shape{
        // ONNX Runtime 需要 int64 形状；顺序必须是 batch, channel, height, width。
        static_cast<int64_t>(batch),
        static_cast<int64_t>(channels),
        static_cast<int64_t>(height),
        static_cast<int64_t>(width),
    };
    const size_t expected = static_cast<size_t>(batch) * channels * height * width;
    if (input.size() != expected) {
        // 输入长度和形状不一致时立即失败，避免 ORT 读越界或输出难解释的错误。
        throw std::runtime_error("Input tensor size does not match NCHW shape.");
    }

    // CreateTensor 不拷贝 input 数据，因此 input vector 在 Run 返回前必须保持有效。
    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        memory_info_,
        const_cast<float*>(input.data()),
        input.size(),
        input_shape.data(),
        input_shape.size());

    const char* input_names[] = {input_name_.c_str()};
    const char* output_names[] = {output_name_.c_str()};
    auto outputs = session_.Run(
        // RunOptions 为空表示使用 session 默认配置。
        Ort::RunOptions{nullptr},
        input_names,
        &input_tensor,
        1,
        output_names,
        1);

    float* output_data = outputs.front().GetTensorMutableData<float>();
    auto output_info = outputs.front().GetTensorTypeAndShapeInfo();
    const size_t output_count = output_info.GetElementCount();
    // 返回 vector 拷贝，让调用方不依赖 ORT 输出对象的生命周期。
    return std::vector<float>(output_data, output_data + output_count);
}

}  // namespace stage4
