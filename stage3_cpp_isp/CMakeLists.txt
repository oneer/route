cmake_minimum_required(VERSION 3.20)

project(stage3_cpp_isp LANGUAGES CXX)

# ASAN 用于排查越界/Use-after-free；FetchContent 只在需要下载 GTest/Benchmark 时开启。
option(CPP_ISP_ENABLE_ASAN "Enable AddressSanitizer when supported" OFF)
option(CPP_ISP_USE_FETCHCONTENT "Download GoogleTest and Google Benchmark with FetchContent" OFF)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(CompilerOptions)
include(Sanitizers)

# 核心库只包含算法、格式和指标逻辑；tools/tests/benchmarks 都链接这个库，避免重复实现。
add_library(cpp_isp_core
    src/cpf32.cpp
    src/image.cpp
    src/border.cpp
    src/fixed_point.cpp
    src/denoise_basic.cpp
    src/bilateral_denoise.cpp
    src/tone_mapping.cpp
    src/tone_lut.cpp
    src/local_tone_mapping.cpp
    src/hdr_merge.cpp
    src/pipeline.cpp
    src/metrics.cpp
)
target_include_directories(cpp_isp_core PUBLIC include)
cpp_isp_apply_compiler_options(cpp_isp_core)
cpp_isp_enable_sanitizers(cpp_isp_core)

# 命令行工具用于生成报告数据、对齐 Python reference、导出中间结果。
add_executable(compare_with_reference tools/compare_with_reference.cpp)
target_link_libraries(compare_with_reference PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(compare_with_reference)
cpp_isp_enable_sanitizers(compare_with_reference)

add_executable(run_bilateral_lut tools/run_bilateral_lut.cpp)
target_link_libraries(run_bilateral_lut PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(run_bilateral_lut)
cpp_isp_enable_sanitizers(run_bilateral_lut)

add_executable(run_tone_mapping tools/run_tone_mapping.cpp)
target_link_libraries(run_tone_mapping PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(run_tone_mapping)
cpp_isp_enable_sanitizers(run_tone_mapping)

add_executable(run_tone_lut tools/run_tone_lut.cpp)
target_link_libraries(run_tone_lut PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(run_tone_lut)
cpp_isp_enable_sanitizers(run_tone_lut)

add_executable(run_local_tone_mapping tools/run_local_tone_mapping.cpp)
target_link_libraries(run_local_tone_mapping PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(run_local_tone_mapping)
cpp_isp_enable_sanitizers(run_local_tone_mapping)

add_executable(run_hdr_merge tools/run_hdr_merge.cpp)
target_link_libraries(run_hdr_merge PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(run_hdr_merge)
cpp_isp_enable_sanitizers(run_hdr_merge)

add_executable(run_pipeline tools/run_pipeline.cpp)
target_link_libraries(run_pipeline PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(run_pipeline)
cpp_isp_enable_sanitizers(run_pipeline)

add_executable(dump_intermediate tools/dump_intermediate.cpp)
target_link_libraries(dump_intermediate PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(dump_intermediate)
cpp_isp_enable_sanitizers(dump_intermediate)

enable_testing()

if(CPP_ISP_USE_FETCHCONTENT)
    # 可选路径：联网下载 GTest/Google Benchmark，适合想接入第三方测试框架时使用。
    include(FetchContent)

    FetchContent_Declare(
        googletest
        URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    FetchContent_Declare(
        benchmark
        URL https://github.com/google/benchmark/archive/refs/tags/v1.8.3.zip
    )
    set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(benchmark)

    add_executable(test_smoke tests/test_smoke.cpp)
    target_compile_definitions(test_smoke PRIVATE CPP_ISP_HAS_GTEST=1)
    target_link_libraries(test_smoke PRIVATE cpp_isp_core GTest::gtest_main)
    add_test(NAME test_smoke COMMAND test_smoke)

    add_executable(bench_smoke benchmarks/bench_smoke.cpp)
    target_compile_definitions(bench_smoke PRIVATE CPP_ISP_HAS_BENCHMARK=1)
    target_link_libraries(bench_smoke PRIVATE cpp_isp_core benchmark::benchmark_main)
else()
    # 默认路径：不依赖网络，使用项目里的轻量 main()/chrono fallback。
    add_executable(test_smoke tests/test_smoke.cpp)
    target_link_libraries(test_smoke PRIVATE cpp_isp_core)
    add_test(NAME test_smoke COMMAND test_smoke)

    add_executable(bench_smoke benchmarks/bench_smoke.cpp)
    target_link_libraries(bench_smoke PRIVATE cpp_isp_core)
endif()

cpp_isp_apply_compiler_options(test_smoke)
cpp_isp_enable_sanitizers(test_smoke)
cpp_isp_apply_compiler_options(bench_smoke)
cpp_isp_enable_sanitizers(bench_smoke)

foreach(test_name IN ITEMS test_cpf32 test_image test_border test_denoise_basic test_tone_mapping test_fixed_point test_tone_lut test_local_tone_mapping test_hdr_merge)
    # 大多数单元测试结构一致，用循环注册，减少 CMake 重复样板。
    add_executable(${test_name} tests/${test_name}.cpp)
    target_link_libraries(${test_name} PRIVATE cpp_isp_core)
    cpp_isp_apply_compiler_options(${test_name})
    cpp_isp_enable_sanitizers(${test_name})
    add_test(NAME ${test_name} COMMAND ${test_name})
endforeach()

add_executable(test_pipeline_golden tests/test_pipeline_golden.cpp)
target_link_libraries(test_pipeline_golden PRIVATE cpp_isp_core)
# golden 测试需要知道源码目录，才能读取 data/pipeline_golden 下的固定参考文件。
target_compile_definitions(test_pipeline_golden PRIVATE CPP_ISP_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
cpp_isp_apply_compiler_options(test_pipeline_golden)
cpp_isp_enable_sanitizers(test_pipeline_golden)
add_test(NAME test_pipeline_golden COMMAND test_pipeline_golden)

add_executable(test_bilateral_denoise tests/test_bilateral_denoise.cpp)
target_link_libraries(test_bilateral_denoise PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(test_bilateral_denoise)
cpp_isp_enable_sanitizers(test_bilateral_denoise)
add_test(NAME test_bilateral_denoise COMMAND test_bilateral_denoise)

add_executable(bench_bilateral benchmarks/bench_bilateral.cpp)
target_link_libraries(bench_bilateral PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(bench_bilateral)
cpp_isp_enable_sanitizers(bench_bilateral)

add_executable(bench_denoise benchmarks/bench_denoise.cpp)
target_link_libraries(bench_denoise PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(bench_denoise)
cpp_isp_enable_sanitizers(bench_denoise)

add_executable(bench_tone_mapping benchmarks/bench_tone_mapping.cpp)
target_link_libraries(bench_tone_mapping PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(bench_tone_mapping)
cpp_isp_enable_sanitizers(bench_tone_mapping)

add_executable(bench_tone_lut benchmarks/bench_tone_lut.cpp)
target_link_libraries(bench_tone_lut PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(bench_tone_lut)
cpp_isp_enable_sanitizers(bench_tone_lut)

add_executable(bench_local_tone_mapping benchmarks/bench_local_tone_mapping.cpp)
target_link_libraries(bench_local_tone_mapping PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(bench_local_tone_mapping)
cpp_isp_enable_sanitizers(bench_local_tone_mapping)

add_executable(bench_pipeline benchmarks/bench_pipeline.cpp)
target_link_libraries(bench_pipeline PRIVATE cpp_isp_core)
cpp_isp_apply_compiler_options(bench_pipeline)
cpp_isp_enable_sanitizers(bench_pipeline)
