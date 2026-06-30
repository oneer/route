#pragma once

#include <memory>
#include <string>
#include <vector>

#include <onnxruntime_cxx_api.h>

namespace stage4 {

// 对 ONNX Runtime C++ API 做一层极薄封装：构造时加载模型，run() 时喂入 NCHW 张量。
class OnnxRuntimeRunner {
public:
    // input_name/output_name 必须和导出 ONNX 时使用的名字保持一致。
    OnnxRuntimeRunner(const std::string& model_path, const std::string& input_name, const std::string& output_name);

    // 输入 vector 按 NCHW 连续存储，返回值也是 ORT 输出张量的连续 float 拷贝。
    std::vector<float> run(const std::vector<float>& input, int batch, int channels, int height, int width);

private:
    // Env 和 Session 生命周期必须覆盖整个推理过程，因此作为成员保存。
    Ort::Env env_;
    Ort::SessionOptions session_options_;
    Ort::Session session_;
    Ort::MemoryInfo memory_info_;
    std::string input_name_;
    std::string output_name_;
};

}  // namespace stage4
