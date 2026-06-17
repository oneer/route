cmake_minimum_required(VERSION 3.20)
project(stage4_deploy_isp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(STAGE4_BUILD_ORT "Build ONNX Runtime C++ runner" ON)
option(STAGE4_BUILD_CUDA_PREPROCESS "Build CUDA preprocess benchmark" OFF)

if(STAGE4_BUILD_ORT AND NOT DEFINED ONNXRUNTIME_ROOT)
  message(FATAL_ERROR "Please pass -DONNXRUNTIME_ROOT=/path/to/onnxruntime-win-x64-*")
endif()

if(STAGE4_BUILD_ORT)
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
endif()

if(STAGE4_BUILD_CUDA_PREPROCESS)
  enable_language(CUDA)
  add_executable(stage4_cuda_preprocess_benchmark
    cpp/src/cuda_preprocess_benchmark.cpp
    cuda_kernels/normalize.cu
  )
  target_include_directories(stage4_cuda_preprocess_benchmark PRIVATE cpp/include)
  set_target_properties(stage4_cuda_preprocess_benchmark PROPERTIES
    CUDA_STANDARD 17
    CUDA_STANDARD_REQUIRED ON
    CUDA_SEPARABLE_COMPILATION OFF
  )
endif()
