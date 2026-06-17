#pragma once

#include <memory>
#include <string>
#include <vector>

#include <onnxruntime_cxx_api.h>

namespace stage4 {

class OnnxRuntimeRunner {
public:
    OnnxRuntimeRunner(const std::string& model_path, const std::string& input_name, const std::string& output_name);

    std::vector<float> run(const std::vector<float>& input, int batch, int channels, int height, int width);

private:
    Ort::Env env_;
    Ort::SessionOptions session_options_;
    Ort::Session session_;
    Ort::MemoryInfo memory_info_;
    std::string input_name_;
    std::string output_name_;
};

}  // namespace stage4

