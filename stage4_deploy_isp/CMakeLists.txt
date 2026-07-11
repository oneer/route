cmake_minimum_required(VERSION 3.20)
project(stage4_deploy_isp LANGUAGES CXX)

# Stage 4 的 C++ runner 使用现代 C++17，同时保持依赖最少，便于在部署机器上编译。
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# STAGE4_BUILD_ORT：构建最小 ONNX Runtime C++ 推理程序。
# STAGE4_BUILD_CUDA_PREPROCESS：可选构建 CUDA 预处理 benchmark，需要 CUDA Toolkit。
option(STAGE4_BUILD_ORT "Build ONNX Runtime C++ runner" ON)
option(STAGE4_BUILD_CUDA_PREPROCESS "Build CUDA preprocess benchmark" OFF)

if(STAGE4_BUILD_ORT AND NOT DEFINED ONNXRUNTIME_ROOT)
  # ONNX Runtime 不从系统路径猜测，显式传入根目录可以避免链接到错误版本。
  message(FATAL_ERROR "Please pass -DONNXRUNTIME_ROOT=/path/to/onnxruntime-win-x64-*")
endif()

if(STAGE4_BUILD_ORT)
  # C++ runner 只包含 PPM I/O、ORT 包装和 main 入口。
  add_executable(stage4_ort_runner
    cpp/src/main.cpp
    cpp/src/image_io.cpp
    cpp/src/onnxruntime_runner.cpp
  )

  target_include_directories(stage4_ort_runner PRIVATE
    cpp/include
    ${ONNXRUNTIME_ROOT}/include
  )

  if(MSVC)
    target_compile_options(stage4_ort_runner PRIVATE /W4 /permissive- /utf-8)
  else()
    target_compile_options(stage4_ort_runner PRIVATE -Wall -Wextra -Wpedantic)
  endif()

  if(WIN32)
    # Windows 使用 onnxruntime.lib 导入库，运行时还需要 onnxruntime.dll 在 PATH 或 exe 旁边。
    target_link_libraries(stage4_ort_runner PRIVATE
      ${ONNXRUNTIME_ROOT}/lib/onnxruntime.lib
    )
  else()
    # Linux/macOS 类环境按共享库名称链接。
    target_link_libraries(stage4_ort_runner PRIVATE
      ${ONNXRUNTIME_ROOT}/lib/libonnxruntime.so
    )
  endif()
endif()

if(STAGE4_BUILD_CUDA_PREPROCESS)
  # CUDA preprocess benchmark 只编译 normalize kernel，用于对比 CPU 与 GPU 的布局转换成本。
  enable_language(CUDA)
  add_executable(stage4_cuda_preprocess_benchmark
    cpp/src/cuda_preprocess_benchmark.cpp
    cuda_kernels/normalize.cu
  )
  target_include_directories(stage4_cuda_preprocess_benchmark PRIVATE cpp/include)
  set_target_properties(stage4_cuda_preprocess_benchmark PROPERTIES
    # CUDA 源码也按 C++17 编译，和主 C++ 代码保持一致。
    CUDA_STANDARD 17
    CUDA_STANDARD_REQUIRED ON
    CUDA_SEPARABLE_COMPILATION OFF
  )
endif()
