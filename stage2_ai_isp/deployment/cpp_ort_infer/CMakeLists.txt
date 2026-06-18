cmake_minimum_required(VERSION 3.16)
project(stage2_ort_infer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ONNXRUNTIME_ROOT "" CACHE PATH "ONNX Runtime C++ SDK root")
if(NOT ONNXRUNTIME_ROOT)
    message(FATAL_ERROR "Set -DONNXRUNTIME_ROOT=<onnxruntime SDK root>")
endif()

add_executable(stage2_ort_infer main.cpp)
target_include_directories(
    stage2_ort_infer PRIVATE "${ONNXRUNTIME_ROOT}/include"
)
target_link_libraries(
    stage2_ort_infer PRIVATE "${ONNXRUNTIME_ROOT}/lib/onnxruntime.lib"
)

add_custom_command(
    TARGET stage2_ort_infer POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${ONNXRUNTIME_ROOT}/lib/onnxruntime.dll"
            "$<TARGET_FILE_DIR:stage2_ort_infer>"
)
