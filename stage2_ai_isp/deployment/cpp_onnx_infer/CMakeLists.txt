# 中文说明：构建 OpenCV DNN 版 ONNX 推理示例。
# 作用：用系统已安装的 OpenCV 读取图片、执行 ONNX 模型、保存输出图片。
cmake_minimum_required(VERSION 3.16)
project(stage2_onnx_infer LANGUAGES CXX)

# 中文说明：部署示例使用 filesystem 等 C++17 标准库能力。
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 中文说明：依赖 OpenCV 的 dnn/imgcodecs/imgproc 模块，具体库由 OpenCVConfig.cmake 提供。
find_package(OpenCV REQUIRED)

add_executable(stage2_onnx_infer main.cpp)
# 中文说明：链接 OpenCV 自动发现到的库集合。
target_link_libraries(stage2_onnx_infer PRIVATE ${OpenCV_LIBS})
