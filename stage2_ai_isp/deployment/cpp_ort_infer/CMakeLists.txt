# 中文说明：构建 ONNX Runtime C++ 推理示例。
# 使用方式：配置时传入 -DONNXRUNTIME_ROOT=<ONNX Runtime C++ SDK 根目录>。
cmake_minimum_required(VERSION 3.16)
project(stage2_ort_infer LANGUAGES CXX)

# 中文说明：部署示例使用 filesystem、array 等 C++17 标准库能力。
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 中文说明：ONNX Runtime SDK 不随项目提交，通过 CMake cache 变量显式指定。
set(ONNXRUNTIME_ROOT "" CACHE PATH "ONNX Runtime C++ SDK root")
if(NOT ONNXRUNTIME_ROOT)
    message(FATAL_ERROR "Set -DONNXRUNTIME_ROOT=<onnxruntime SDK root>")
endif()

add_executable(stage2_ort_infer main.cpp)
# 中文说明：头文件来自 SDK include，库文件来自 SDK lib。
target_include_directories(
    stage2_ort_infer PRIVATE "${ONNXRUNTIME_ROOT}/include"
)
target_link_libraries(
    stage2_ort_infer PRIVATE "${ONNXRUNTIME_ROOT}/lib/onnxruntime.lib"
)

add_custom_command(
    TARGET stage2_ort_infer POST_BUILD
    # 中文说明：构建后复制 onnxruntime.dll，避免运行 exe 时找不到动态库。
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${ONNXRUNTIME_ROOT}/lib/onnxruntime.dll"
            "$<TARGET_FILE_DIR:stage2_ort_infer>"
)
