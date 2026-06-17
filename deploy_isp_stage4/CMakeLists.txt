cmake_minimum_required(VERSION 3.20)
project(deploy_isp_stage4 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(STAGE4_BUILD_ORT "Build ONNX Runtime C++ runner" ON)

if(NOT DEFINED ONNXRUNTIME_ROOT)
  message(FATAL_ERROR "Please pass -DONNXRUNTIME_ROOT=/path/to/onnxruntime-win-x64-*")
endif()

add_executable(stage4_ort_runner
  cpp/src/main.cpp
  cpp/src/image_io.cpp
  cpp/src/onnxruntime_runner.cpp
)

target_include_directories(stage4_ort_runner PRIVATE
  cpp/include
  ${ONNXRUNTIME_ROOT}/include
)

if(WIN32)
  target_link_libraries(stage4_ort_runner PRIVATE
    ${ONNXRUNTIME_ROOT}/lib/onnxruntime.lib
  )
else()
  target_link_libraries(stage4_ort_runner PRIVATE
    ${ONNXRUNTIME_ROOT}/lib/libonnxruntime.so
  )
endif()

